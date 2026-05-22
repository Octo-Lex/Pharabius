"""Tests for validate_v151_scoring_calibration script (W40-S04)."""

from __future__ import annotations

from pathlib import Path

from scripts.validate_v151_scoring_calibration import (
    compare_default_to_enhanced,
    extract_finding_snapshot,
    hash_file,
    render_evidence_pack_markdown,
)


class TestHashFile:
    def test_hash_file_is_stable(self, tmp_path: Path) -> None:
        p = tmp_path / "test.json"
        p.write_text('{"a": 1}', encoding="utf-8")
        h1 = hash_file(p)
        h2 = hash_file(p)
        assert h1 == h2
        assert len(h1) == 64

    def test_hash_file_changes_with_content(self, tmp_path: Path) -> None:
        p = tmp_path / "test.json"
        p.write_text('{"a": 1}', encoding="utf-8")
        h1 = hash_file(p)
        p.write_text('{"a": 2}', encoding="utf-8")
        h2 = hash_file(p)
        assert h1 != h2


class TestExtractFindingSnapshot:
    def test_reads_scores_priorities_and_ids(self) -> None:
        register = {
            "findings": [
                {
                    "id": "TD-DEP-001",
                    "risk_score": 15,
                    "priority": "Medium",
                    "evidence_ids": ["EV-002", "EV-001"],
                },
                {
                    "id": "TD-PROCESS-001",
                    "risk_score": 3,
                    "priority": "Low",
                    "evidence_ids": [],
                },
            ]
        }
        snap = extract_finding_snapshot(register)
        assert snap["TD-DEP-001"]["score"] == 15
        assert snap["TD-DEP-001"]["priority"] == "Medium"
        assert snap["TD-DEP-001"]["evidence_ids"] == ["EV-001", "EV-002"]  # sorted
        assert snap["TD-PROCESS-001"]["score"] == 3

    def test_empty_findings(self) -> None:
        snap = extract_finding_snapshot({"findings": []})
        assert snap == {}


class TestCompareDefaultToEnhanced:
    def test_detects_score_changes(self) -> None:
        default_snap = {"TD-001": {"score": 10, "priority": "Low", "evidence_ids": []}}
        enhanced_snap = {"TD-001": {"score": 15, "priority": "Medium", "evidence_ids": []}}
        default_reg = {
            "findings": [
                {"id": "TD-001", "title": "test", "category": "TD-DEP", "risk_breakdown": {}}
            ]
        }
        enhanced_reg = {
            "findings": [
                {
                    "id": "TD-001",
                    "title": "test",
                    "category": "TD-DEP",
                    "risk_breakdown": {
                        "architecture_centrality": {
                            "level": "High",
                            "value": 5,
                            "source": "graph",
                            "reason": "fan_in=8",
                        }
                    },
                }
            ]
        }
        changes = compare_default_to_enhanced(
            default_snap, enhanced_snap, default_reg, enhanced_reg
        )
        assert len(changes) == 1
        assert changes[0]["before_score"] == 10
        assert changes[0]["after_score"] == 15
        assert changes[0]["before_priority"] == "Low"
        assert changes[0]["after_priority"] == "Medium"

    def test_no_changes(self) -> None:
        snap = {"TD-001": {"score": 10, "priority": "Low", "evidence_ids": []}}
        reg = {
            "findings": [
                {"id": "TD-001", "title": "test", "category": "TD-DEP", "risk_breakdown": {}}
            ]
        }
        changes = compare_default_to_enhanced(snap, snap, reg, reg)
        assert changes == []

    def test_detects_priority_changes_only(self) -> None:
        default_snap = {"TD-001": {"score": 10, "priority": "Low", "evidence_ids": []}}
        enhanced_snap = {"TD-001": {"score": 10, "priority": "Medium", "evidence_ids": []}}
        reg = {
            "findings": [
                {"id": "TD-001", "title": "test", "category": "TD-DEP", "risk_breakdown": {}}
            ]
        }
        changes = compare_default_to_enhanced(default_snap, enhanced_snap, reg, reg)
        assert len(changes) == 1
        assert changes[0]["before_priority"] == "Low"
        assert changes[0]["after_priority"] == "Medium"


class TestRenderEvidencePackMarkdown:
    def test_contains_summary_tables(self) -> None:
        pack = {
            "summary": {
                "repositories_checked": 2,
                "repositories_passed": 2,
                "score_changes_total": 3,
                "priority_changes_total": 1,
                "preview_mutation_failures": 0,
                "id_stability_failures": 0,
            },
            "repositories": [
                {
                    "name": "test-repo",
                    "finding_ids_stable": True,
                    "evidence_ids_stable": True,
                    "canonical_mutation_in_preview": False,
                    "default_findings": 4,
                    "enhanced_findings": 4,
                    "score_changes": [
                        {
                            "finding_id": "TD-001",
                            "category": "TD-DEP",
                            "before_score": 15,
                            "after_score": 8,
                            "before_priority": "Medium",
                            "after_priority": "Medium",
                            "changed_factors": [{"factor": "change_frequency"}],
                        }
                    ],
                    "warnings": [],
                }
            ],
        }
        md = render_evidence_pack_markdown(pack)
        assert "# Scoring Evidence Pack" in md
        assert "| Repositories checked | 2 |" in md
        assert "| Repositories passed | 2 |" in md
        assert "## Repository: test-repo" in md
        assert "| Finding IDs stable | PASS |" in md
        assert "### Score Changes" in md
        assert "| TD-001 | TD-DEP" in md

    def test_handles_empty_repos(self) -> None:
        pack = {
            "summary": {
                "repositories_checked": 0,
                "repositories_passed": 0,
                "score_changes_total": 0,
                "priority_changes_total": 0,
                "preview_mutation_failures": 0,
                "id_stability_failures": 0,
            },
            "repositories": [],
        }
        md = render_evidence_pack_markdown(pack)
        assert "# Scoring Evidence Pack" in md
        assert "| Repositories checked | 0 |" in md

    def test_handles_warnings(self) -> None:
        pack = {
            "summary": {
                "repositories_checked": 1,
                "repositories_passed": 1,
                "score_changes_total": 0,
                "priority_changes_total": 0,
                "preview_mutation_failures": 0,
                "id_stability_failures": 0,
            },
            "repositories": [
                {
                    "name": "warn-repo",
                    "finding_ids_stable": True,
                    "evidence_ids_stable": True,
                    "canonical_mutation_in_preview": False,
                    "default_findings": 1,
                    "enhanced_findings": 1,
                    "score_changes": [],
                    "warnings": ["fallback: no graph available"],
                }
            ],
        }
        md = render_evidence_pack_markdown(pack)
        assert "### Warnings" in md
        assert "- fallback: no graph available" in md
