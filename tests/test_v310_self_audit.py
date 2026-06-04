"""v3.1.0 Self-Audit Regression Tests.

These tests verify that the specific defects identified in the v3.1.0
self-audit have been repaired and cannot silently return.
"""

from __future__ import annotations

import json
from pathlib import Path

from pharabius.ai.mock_provider import MockAIAdapter
from pharabius.core.analyzer import _deduplicate_findings
from pharabius.core.claims import generate_claims_from_findings
from pharabius.core.planner import _group_findings, _should_group
from pharabius.core.run_metadata import execute_run
from pharabius.core.scanner import _debt_markers_in_text, scan_repository
from pharabius.schemas.finding import DebtFinding

# ---------------------------------------------------------------------------
# S01: Config/governance preservation
# ---------------------------------------------------------------------------


class TestS01ConfigPreservation:
    """S01: ai-debt run must not destroy user customizations."""

    def _make_repo(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")

    def test_config_survives_second_run(self, tmp_path: Path) -> None:
        self._make_repo(tmp_path)
        execute_run(tmp_path)

        config = tmp_path / ".ai-debt" / "config.yaml"
        config.write_text(config.read_text().replace('name: ""', 'name: "SURVIVAL_TEST"'))

        execute_run(tmp_path)
        assert "SURVIVAL_TEST" in config.read_text()

    def test_governance_survives_second_run(self, tmp_path: Path) -> None:
        self._make_repo(tmp_path)
        execute_run(tmp_path)

        gov = tmp_path / ".ai-debt" / "governance.yaml"
        gov.write_text(gov.read_text() + "# SURVIVAL_MARKER\n")

        execute_run(tmp_path)
        assert "SURVIVAL_MARKER" in gov.read_text()


# ---------------------------------------------------------------------------
# S02: TD-CODE signal generation
# ---------------------------------------------------------------------------


class TestS02TDCodeGeneration:
    """S02: TD-CODE findings must be generatable from real fixtures."""

    def _make_repo_with_file(self, tmp_path: Path, filename: str, content: str) -> None:
        (tmp_path / filename).write_text(content, encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")

    def test_large_file_produces_td_code(self, tmp_path: Path) -> None:
        big = tmp_path / "big.py"
        big.write_text("\n".join([f"# line {i}" for i in range(1200)]), encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")
        execute_run(tmp_path)
        register = json.loads((tmp_path / ".ai-debt" / "debt-register.json").read_text())
        td_code = [f for f in register["findings"] if f["category"] == "TD-CODE"]
        assert any(
            "large" in f["title"].lower() or "file" in f["title"].lower() for f in td_code
        ), "Large file should produce TD-CODE finding"

    def test_debt_markers_produce_td_code(self, tmp_path: Path) -> None:
        src = tmp_path / "markers.py"
        lines = [f"# TODO: fix thing {i}" for i in range(10)]
        lines.extend([f"# FIXME: broken {i}" for i in range(5)])
        src.write_text("\n".join(lines), encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")
        execute_run(tmp_path)
        register = json.loads((tmp_path / ".ai-debt" / "debt-register.json").read_text())
        td_code = [f for f in register["findings"] if f["category"] == "TD-CODE"]
        assert any(
            "marker" in f["title"].lower() or "debt" in f["title"].lower() for f in td_code
        ), "Debt markers should produce TD-CODE finding"

    def test_repeated_todo_counted_as_multiple(self) -> None:
        """5 TODOs must count as 5 occurrences, not 1 unique marker."""
        counts = _debt_markers_in_text("# TODO: a\n# TODO: b\n# TODO: c\n# TODO: d\n# TODO: e\n")
        assert counts.get("todo") == 5
        assert sum(counts.values()) == 5

    def test_scanner_emits_metadata_total_count(self, tmp_path: Path) -> None:
        """Evidence must carry total_count in metadata."""
        src = tmp_path / "markers.py"
        src.write_text("\n".join([f"# TODO: fix {i}" for i in range(10)]), encoding="utf-8")
        store = scan_repository(tmp_path)
        markers = [e for e in store.evidence if e.type == "debt_marker_detected"]
        assert len(markers) >= 1
        assert markers[0].metadata["total_count"] >= 5


# ---------------------------------------------------------------------------
# S03: Deduplication
# ---------------------------------------------------------------------------


class TestS03Deduplication:
    """S03: Duplicate findings should collapse deterministically."""

    def test_duplicate_findings_merge(self) -> None:
        """Two findings with same category+title+locations collapse to one."""
        f1 = DebtFinding(
            id="F-001",
            category="TD-DEP",
            title="No lockfile",
            description="No lockfile detected",
            severity="Medium",
            risk_score=15,
            evidence_ids=["E-001"],
            locations=["pkg/"],
            technical_impact="Reproducibility risk",
            business_impact="Inferred",
            priority="Medium",
            recommended_action="Add lockfile",
        )
        f2 = DebtFinding(
            id="F-002",
            category="TD-DEP",
            title="No lockfile",
            description="No lockfile detected",
            severity="Medium",
            risk_score=15,
            evidence_ids=["E-002"],
            locations=["pkg/"],
            technical_impact="Reproducibility risk",
            business_impact="Inferred",
            priority="Medium",
            recommended_action="Add lockfile",
        )
        result = _deduplicate_findings([f1, f2])
        assert len(result) == 1
        assert set(result[0].evidence_ids) == {"E-001", "E-002"}

    def test_higher_severity_higher_score_not_downgraded(self) -> None:
        """Higher severity + higher risk_score: base should be the higher one."""
        f_low = DebtFinding(
            id="F-001",
            category="TD-DEP",
            title="No lockfile",
            description="No lockfile detected",
            severity="Low",
            risk_score=5,
            evidence_ids=["E-001"],
            locations=["pkg/"],
            technical_impact="Low risk",
            business_impact="Low",
            priority="Low",
            recommended_action="Add lockfile",
        )
        f_high = DebtFinding(
            id="F-002",
            category="TD-DEP",
            title="No lockfile",
            description="No lockfile detected",
            severity="High",
            risk_score=25,
            evidence_ids=["E-002"],
            locations=["pkg/"],
            technical_impact="High risk",
            business_impact="High",
            priority="High",
            recommended_action="Add lockfile",
        )
        result = _deduplicate_findings([f_low, f_high])
        assert len(result) == 1
        assert result[0].severity == "High"
        assert result[0].risk_score == 25

    def test_higher_severity_lower_score_not_downgraded(self) -> None:
        """Critical severity + risk_score=10 must NOT be downgraded
        when merged with Medium severity + risk_score=30."""
        f_critical = DebtFinding(
            id="F-001",
            category="TD-DEP",
            title="No lockfile",
            description="No lockfile detected",
            severity="Critical",
            risk_score=10,
            evidence_ids=["E-001"],
            locations=["pkg/"],
            technical_impact="Critical risk",
            business_impact="Critical",
            priority="Critical",
            recommended_action="Add lockfile",
        )
        f_medium = DebtFinding(
            id="F-002",
            category="TD-DEP",
            title="No lockfile",
            description="No lockfile detected",
            severity="Medium",
            risk_score=30,
            evidence_ids=["E-002"],
            locations=["pkg/"],
            technical_impact="Medium risk",
            business_impact="Medium",
            priority="Medium",
            recommended_action="Add lockfile",
        )
        result = _deduplicate_findings([f_critical, f_medium])
        assert len(result) == 1
        assert result[0].severity == "Critical", "Severity must not be downgraded"
        assert result[0].risk_score == 30, "Risk score must be max across group"

    def test_different_locations_not_over_merged(self) -> None:
        """Different locations = different findings."""
        f1 = DebtFinding(
            id="F-001",
            category="TD-DEP",
            title="No lockfile",
            description="No lockfile detected",
            severity="Medium",
            risk_score=15,
            evidence_ids=["E-001"],
            locations=["pkg-a/"],
            technical_impact="Risk",
            business_impact="Inferred",
            priority="Medium",
            recommended_action="Add lockfile",
        )
        f2 = DebtFinding(
            id="F-002",
            category="TD-DEP",
            title="No lockfile",
            description="No lockfile detected",
            severity="Medium",
            risk_score=15,
            evidence_ids=["E-002"],
            locations=["pkg-b/"],
            technical_impact="Risk",
            business_impact="Inferred",
            priority="Medium",
            recommended_action="Add lockfile",
        )
        result = _deduplicate_findings([f1, f2])
        assert len(result) == 2, "Different locations should not merge"


# ---------------------------------------------------------------------------
# S04: Work-package grouping
# ---------------------------------------------------------------------------


class TestS04WorkPackageGrouping:
    """S04: Related findings should produce grouped work packages."""

    def test_same_category_owner_and_location_overlap_grouped(self) -> None:
        """Same category, same owner, overlapping locations → one group."""
        a = DebtFinding(
            id="F-001",
            category="TD-DEP",
            title="Dependency manifest risk",
            description="Risk in manifest",
            severity="High",
            risk_score=30,
            evidence_ids=["E-001"],
            locations=["package.json"],
            suggested_owner_area="Platform",
            technical_impact="Dependency risk",
            business_impact="Inferred",
            priority="High",
            recommended_action="Review dependencies",
        )
        b = DebtFinding(
            id="F-002",
            category="TD-DEP",
            title="Dependency lockfile risk",
            description="Risk in lockfile",
            severity="Medium",
            risk_score=20,
            evidence_ids=["E-002"],
            locations=["package.json"],
            suggested_owner_area="Platform",
            technical_impact="Dependency risk",
            business_impact="Inferred",
            priority="Medium",
            recommended_action="Add lockfile",
        )
        groups = _group_findings([a, b])
        assert len(groups) == 1
        assert sorted(f.id for f in groups[0]) == ["F-001", "F-002"]

    def test_same_category_owner_no_overlap_no_relation_not_grouped(self) -> None:
        """Same category + owner but no overlap and no related_findings → separate."""
        a = DebtFinding(
            id="F-001",
            category="TD-DEP",
            title="No lockfile",
            description="No lockfile",
            severity="Medium",
            risk_score=15,
            evidence_ids=["E-001"],
            locations=["frontend/package.json"],
            suggested_owner_area="Platform",
            technical_impact="Risk",
            business_impact="Inferred",
            priority="Medium",
            recommended_action="Add lockfile",
        )
        b = DebtFinding(
            id="F-002",
            category="TD-DEP",
            title="No lockfile",
            description="No lockfile",
            severity="Medium",
            risk_score=15,
            evidence_ids=["E-002"],
            locations=["backend/pyproject.toml"],
            suggested_owner_area="Platform",
            technical_impact="Risk",
            business_impact="Inferred",
            priority="Medium",
            recommended_action="Add lockfile",
        )
        groups = _group_findings([a, b])
        assert len(groups) == 2, "No overlap and no explicit relation → separate"

    def test_explicit_related_findings_triggers_grouping(self) -> None:
        """No location overlap, but A lists B in related_findings → grouped."""
        a = DebtFinding(
            id="F-001",
            category="TD-DEP",
            title="No lockfile",
            description="No lockfile",
            severity="High",
            risk_score=25,
            evidence_ids=["E-001"],
            locations=["frontend/package.json"],
            suggested_owner_area="Platform",
            related_findings=["F-002"],
            technical_impact="Risk",
            business_impact="Inferred",
            priority="High",
            recommended_action="Add lockfile",
        )
        b = DebtFinding(
            id="F-002",
            category="TD-DEP",
            title="No lockfile",
            description="No lockfile",
            severity="Medium",
            risk_score=15,
            evidence_ids=["E-002"],
            locations=["backend/pyproject.toml"],
            suggested_owner_area="Platform",
            technical_impact="Risk",
            business_impact="Inferred",
            priority="Medium",
            recommended_action="Add lockfile",
        )
        groups = _group_findings([a, b])
        assert len(groups) == 1, "Explicit related_findings link must trigger grouping"

    def test_highest_risk_is_grouped_wp_primary(self) -> None:
        """Pre-sort ensures highest-risk finding becomes group[0] (the primary)."""
        a = DebtFinding(
            id="F-001",
            category="TD-DEP",
            title="Low risk item",
            description="Low risk",
            severity="Low",
            risk_score=5,
            evidence_ids=["E-001"],
            locations=["shared/"],
            suggested_owner_area="Platform",
            technical_impact="Low",
            business_impact="Low",
            priority="Low",
            recommended_action="Review",
        )
        b = DebtFinding(
            id="F-002",
            category="TD-DEP",
            title="High risk item",
            description="High risk",
            severity="High",
            risk_score=35,
            evidence_ids=["E-002"],
            locations=["shared/"],
            suggested_owner_area="Platform",
            technical_impact="High",
            business_impact="High",
            priority="High",
            recommended_action="Review",
        )
        groups = _group_findings([a, b])
        assert len(groups) == 1
        assert groups[0][0].id == "F-002", "Highest risk must be primary"

    def test_unrelated_categories_not_grouped(self) -> None:
        """TD-DEP and TD-TEST findings never group together."""
        a = DebtFinding(
            id="F-001",
            category="TD-DEP",
            title="No lockfile",
            description="No lockfile",
            severity="High",
            risk_score=25,
            evidence_ids=["E-001"],
            locations=["shared/"],
            suggested_owner_area="Platform",
            technical_impact="Risk",
            business_impact="Inferred",
            priority="High",
            recommended_action="Add lockfile",
        )
        b = DebtFinding(
            id="F-002",
            category="TD-TEST",
            title="No tests",
            description="No tests",
            severity="High",
            risk_score=25,
            evidence_ids=["E-002"],
            locations=["shared/"],
            suggested_owner_area="Platform",
            technical_impact="Risk",
            business_impact="Inferred",
            priority="High",
            recommended_action="Add tests",
        )
        groups = _group_findings([a, b])
        assert len(groups) == 2, "Different categories must never group"


# ---------------------------------------------------------------------------
# S05: Mock provider confidence
# ---------------------------------------------------------------------------


class TestS05MockProviderConfidence:
    """S05: Mock provider must emit valid confidence values."""

    def test_no_critical_confidence(self) -> None:
        adapter = MockAIAdapter()
        response = adapter.generate_json(
            "test",
            {
                "findings": [
                    {
                        "id": "F-001",
                        "title": "Test",
                        "category": "TD-DEP",
                        "severity": "Critical",
                        "evidence_ids": ["E-001"],
                    },
                    {
                        "id": "F-002",
                        "title": "Test",
                        "category": "TD-DEP",
                        "severity": "Low",
                        "evidence_ids": [],
                    },
                ]
            },
        )
        for e in response.parsed_json["enrichments"]:
            assert e["confidence"] in ("High", "Medium", "Low"), (
                f"Invalid confidence: {e['confidence']}"
            )

    def test_critical_severity_maps_to_high_confidence(self) -> None:
        adapter = MockAIAdapter()
        response = adapter.generate_json(
            "test",
            {
                "findings": [
                    {
                        "id": "F-001",
                        "title": "Test",
                        "category": "TD-DEP",
                        "severity": "Critical",
                        "evidence_ids": ["E-001"],
                    },
                ]
            },
        )
        assert response.parsed_json["enrichments"][0]["confidence"] == "High"


# ---------------------------------------------------------------------------
# S06: Claims → work package mapping
# ---------------------------------------------------------------------------


class TestS06ClaimsTraceability:
    """S06: Claims must link to actual work package IDs."""

    def test_claims_link_to_real_wp(self) -> None:
        claims = generate_claims_from_findings(
            [
                {
                    "id": "F-001",
                    "category": "TD-DEP",
                    "title": "Test",
                    "evidence_ids": ["E-001"],
                }
            ],
            finding_to_wp_map={"F-001": ["WP-001"]},
        )
        assert claims[0].linked_work_packages == ["WP-001"]

    def test_related_findings_not_copied_as_wps(self) -> None:
        """related_findings must never leak into linked_work_packages."""
        claims = generate_claims_from_findings(
            [
                {
                    "id": "F-001",
                    "category": "TD-DEP",
                    "title": "Test",
                    "evidence_ids": ["E-001"],
                    "related_findings": ["F-002"],
                }
            ],
        )
        assert claims[0].linked_work_packages == []

    def test_no_wp_map_empty_links(self) -> None:
        """Without planning artifacts, claims have empty linked_work_packages."""
        claims = generate_claims_from_findings(
            [
                {
                    "id": "F-001",
                    "category": "TD-DEP",
                    "title": "Test",
                    "evidence_ids": ["E-001"],
                }
            ],
        )
        assert claims[0].linked_work_packages == []

    def test_execute_run_generates_claims(self, tmp_path: Path) -> None:
        """Claims must be wired into execute_run."""
        (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")
        execute_run(tmp_path)
        assert (tmp_path / ".ai-debt" / "claims" / "operational-claims.json").exists()

    def test_execute_run_generates_traceability_matrices(self, tmp_path: Path) -> None:
        """Traceability matrices must be wired into execute_run."""
        (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")
        execute_run(tmp_path)
        trace_dir = tmp_path / ".ai-debt" / "traceability"
        assert (trace_dir / "evidence-finding-matrix.md").exists()
        assert (trace_dir / "finding-claim-matrix.md").exists()
        assert (trace_dir / "claim-workpackage-matrix.md").exists()

    def test_claims_artifact_uses_correct_wp_links(self, tmp_path: Path) -> None:
        """Claims JSON (the sole v3.1.0 traceability target) must use correct WP links."""
        (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")
        execute_run(tmp_path)
        claims_data = json.loads(
            (tmp_path / ".ai-debt" / "claims" / "operational-claims.json").read_text()
        )
        # No claim should have finding IDs in linked_work_packages
        for claim in claims_data.get("claims", []):
            for wp_id in claim.get("linked_work_packages", []):
                assert not wp_id.startswith("F-"), (
                    f"Finding ID {wp_id} leaked into linked_work_packages"
                )


# ---------------------------------------------------------------------------
# S07: End-to-end validity
# ---------------------------------------------------------------------------


class TestS07EndToEndValidity:
    """S07: Full pipeline must produce valid .ai-debt/ package."""

    def test_full_run_produces_valid_package(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")
        execute_run(tmp_path)

        workspace = tmp_path / ".ai-debt"
        for artifact in [
            "config.yaml",
            "evidence.json",
            "debt-register.json",
            "debt-register.md",
            "remediation-roadmap.md",
            "handoff-summary.md",
        ]:
            assert (workspace / artifact).exists(), f"Missing {artifact}"

        # New v3.1.0 artifacts
        assert (workspace / "claims" / "operational-claims.json").exists()
        assert (workspace / "traceability" / "evidence-finding-matrix.md").exists()

        # All JSON must parse
        for jf in [
            "evidence.json",
            "debt-register.json",
            "project-profile.json",
            "claims/operational-claims.json",
        ]:
            json.loads((workspace / jf).read_text(encoding="utf-8"))
