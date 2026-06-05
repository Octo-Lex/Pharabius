"""Tests for v3.4.0 External Evidence Review and Reporting.

Covers:
- No external evidence case
- External evidence summary computation
- Combined evidence manifest rendering
- Deterministic ordering
- Malformed external artifact warning
- Existing report contents unchanged
- Status reader external/combined evidence display
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo_with_no_external(tmp_path: Path) -> Path:
    """Repository with .ai-debt but no external evidence."""
    repo = tmp_path / "repo"
    repo.mkdir()
    ai_debt = repo / ".ai-debt"
    ai_debt.mkdir()
    return repo


@pytest.fixture()
def repo_with_external(tmp_path: Path) -> Path:
    """Repository with external evidence from one connector."""
    repo = tmp_path / "repo"
    repo.mkdir()
    ai_debt = repo / ".ai-debt"
    ai_debt.mkdir()
    ext_dir = ai_debt / "external-evidence"
    ext_dir.mkdir()

    # SARIF evidence
    sarif_store = {
        "repository": "",
        "evidence": [
            _make_evidence(
                eid="EXT-SARIF-000001",
                connector="sarif",
                rule_id="python/sql-injection",
                confidence="High",
                summary="SQL injection in query",
            ),
            _make_evidence(
                eid="EXT-SARIF-000002",
                connector="sarif",
                rule_id="python/xss",
                confidence="Medium",
                summary="Reflected XSS",
            ),
        ],
    }
    (ext_dir / "sarif-20240101-120000.json").write_text(json.dumps(sarif_store))

    return repo


@pytest.fixture()
def repo_with_multiple_connectors(tmp_path: Path) -> Path:
    """Repository with external evidence from multiple connectors."""
    repo = tmp_path / "repo"
    repo.mkdir()
    ai_debt = repo / ".ai-debt"
    ai_debt.mkdir()
    ext_dir = ai_debt / "external-evidence"
    ext_dir.mkdir()

    # Trivy evidence with severity
    trivy_store = {
        "repository": "",
        "evidence": [
            _make_evidence(
                eid="EXT-TRIVY-000001",
                connector="trivy",
                rule_id="CVE-2024-1234",
                confidence="High",
                summary="Vulnerability in requests",
                severity="Critical",
                pkg_name="requests",
            ),
            _make_evidence(
                eid="EXT-TRIVY-000002",
                connector="trivy",
                rule_id="CVE-2024-5678",
                confidence="Medium",
                summary="Vulnerability in urllib3",
                severity="High",
                pkg_name="urllib3",
            ),
            _make_evidence(
                eid="EXT-TRIVY-000003",
                connector="trivy",
                rule_id="CVE-2024-1234",
                confidence="High",
                summary="Same CVE different location",
                severity="Critical",
                pkg_name="requests",
            ),
        ],
    }
    (ext_dir / "trivy-20240101-120000.json").write_text(json.dumps(trivy_store))

    # Syft evidence (SBOM, no severity)
    syft_store = {
        "repository": "",
        "evidence": [
            _make_evidence(
                eid="EXT-SYFT-000001",
                connector="syft",
                confidence="High",
                summary="Package: flask",
                pkg_name="flask",
                sbom=True,
            ),
            _make_evidence(
                eid="EXT-SYFT-000002",
                connector="syft",
                confidence="Medium",
                summary="Package: werkzeug",
                pkg_name="werkzeug",
                sbom=True,
            ),
        ],
    }
    (ext_dir / "syft-20240101-120000.json").write_text(json.dumps(syft_store))

    return repo


@pytest.fixture()
def repo_with_malformed(tmp_path: Path) -> Path:
    """Repository with one good and one malformed external evidence file."""
    repo = tmp_path / "repo"
    repo.mkdir()
    ai_debt = repo / ".ai-debt"
    ai_debt.mkdir()
    ext_dir = ai_debt / "external-evidence"
    ext_dir.mkdir()

    good_store = {
        "repository": "",
        "evidence": [
            _make_evidence(eid="EXT-001", connector="semgrep", confidence="High"),
        ],
    }
    (ext_dir / "semgrep-good.json").write_text(json.dumps(good_store))
    (ext_dir / "bad-corrupted.json").write_text("NOT JSON {{{")

    return repo


@pytest.fixture()
def repo_with_combined(tmp_path: Path) -> Path:
    """Repository with combined evidence and manifest."""
    repo = tmp_path / "repo"
    repo.mkdir()
    ai_debt = repo / ".ai-debt"
    ai_debt.mkdir()

    # Native evidence
    native = {
        "repository": "test",
        "evidence": [
            {
                "evidence_id": "NAT-001",
                "source": "scan",
                "type": "test_file_detected",
                "category": "TD-TEST",
                "location": {"file": "tests/test_app.py", "line_start": 1},
                "subject": "test",
                "object": "file",
                "summary": "Test file",
                "raw_observation": "test",
                "confidence": "High",
                "collected_at": "2024-01-01T00:00:00Z",
            },
        ],
    }
    (ai_debt / "evidence.json").write_text(json.dumps(native))

    # External evidence
    ext_dir = ai_debt / "external-evidence"
    ext_dir.mkdir()
    ext_store = {
        "repository": "",
        "evidence": [
            _make_evidence(
                eid="EXT-001",
                connector="sarif",
                rule_id="python/sql-injection",
                confidence="High",
            ),
        ],
    }
    (ext_dir / "sarif-20240101.json").write_text(json.dumps(ext_store))

    # Combined evidence
    combined = {
        "repository": "test",
        "evidence": [
            native["evidence"][0],
            {
                "evidence_id": "EXT-SARIF-ABC123-000001",
                "source": "external_connector",
                "type": "vulnerability_detected",
                "category": "TD-SEC",
                "location": {"file": "src/app.py", "line_start": 42},
                "subject": "app",
                "object": "sql injection",
                "summary": "SQL injection",
                "raw_observation": "test",
                "confidence": "High",
                "collected_at": "2024-01-01T00:00:00Z",
            },
        ],
    }
    (ai_debt / "combined-evidence.json").write_text(json.dumps(combined))

    # Manifest
    manifest = {
        "schema_version": "1.0",
        "native": {
            "source_type": "native",
            "source_file": ".ai-debt/evidence.json",
            "evidence_count": 1,
            "imported_count": 1,
        },
        "external_sources": [
            {
                "source_type": "external",
                "source_file": ".ai-debt/external-evidence/sarif-20240101.json",
                "evidence_count": 1,
                "imported_count": 1,
                "duplicate_count": 0,
            },
        ],
        "total_native": 1,
        "total_external": 1,
        "total_combined": 2,
        "deduplicated": 0,
    }
    (ai_debt / "combined-evidence-manifest.json").write_text(json.dumps(manifest))

    return repo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_evidence(
    eid: str = "EXT-001",
    connector: str = "sarif",
    rule_id: str = "",
    confidence: str = "High",
    summary: str = "Test finding",
    severity: str = "",
    pkg_name: str = "",
    sbom: bool = False,
) -> dict:
    """Create a mock evidence item dict."""
    metadata: dict = {
        "connector_provenance": {
            "connector_name": connector,
            "connector_version": "1.0.0",
            "source_format": connector,
            "source_file": f"test.{connector}",
        },
    }
    if rule_id:
        metadata["connector_provenance"]["source_rule_id"] = rule_id
    if severity:
        metadata.setdefault("depsec_coordinates", {})["severity"] = severity
    if pkg_name:
        key = "sbom_coordinates" if sbom else "depsec_coordinates"
        metadata.setdefault(key, {})["pkg_name"] = pkg_name

    return {
        "evidence_id": eid,
        "source": "external_connector",
        "type": "vulnerability_detected",
        "category": "TD-SEC",
        "location": {"file": "src/app.py", "line_start": 10},
        "subject": "app",
        "object": "finding",
        "summary": summary,
        "raw_observation": "test",
        "confidence": confidence,
        "collected_at": "2024-01-01T00:00:00Z",
        "metadata": metadata,
    }


# ---------------------------------------------------------------------------
# S01 — No External Evidence
# ---------------------------------------------------------------------------


class TestNoExternalEvidence:
    """Report handles absence of external evidence gracefully."""

    def test_no_external_dir(self, repo_with_no_external: Path) -> None:
        from pharabius.core.connectors.review import build_external_evidence_summary

        s = build_external_evidence_summary(repo_with_no_external)
        assert s.external_files_total == 0
        assert not s.has_external_evidence
        assert not s.has_combined_evidence

    def test_no_external_report_content(self, repo_with_no_external: Path) -> None:
        from pharabius.core.connectors.review import (
            build_external_evidence_summary,
            render_external_evidence_report,
        )

        s = build_external_evidence_summary(repo_with_no_external)
        report = render_external_evidence_report(s)
        assert "No external evidence files found" in report
        assert "confirmed findings" in report
        assert "No combined evidence store found" in report

    def test_no_external_write_reports(self, repo_with_no_external: Path) -> None:
        from pharabius.core.reporter import write_reports

        # Need minimal artifacts for reporter
        ai_debt = repo_with_no_external / ".ai-debt"
        (ai_debt / "project-profile.json").write_text(
            json.dumps(
                {
                    "project_name": "test",
                    "repository_root": str(repo_with_no_external),
                }
            )
        )
        (ai_debt / "evidence.json").write_text(
            json.dumps(
                {
                    "repository": "test",
                    "evidence": [],
                }
            )
        )
        (ai_debt / "debt-register.json").write_text(
            json.dumps(
                {
                    "project_name": "test",
                    "summary": {
                        "total_findings": 0,
                        "critical": 0,
                        "high": 0,
                        "medium": 0,
                        "low": 0,
                    },
                }
            )
        )

        result = write_reports(repo_with_no_external)
        # Should include external-evidence-report.md
        report_names = [p.name for p in result.files_written]
        assert "external-evidence-report.md" in report_names

        # Read the report content
        report_path = next(
            p for p in result.files_written if p.name == "external-evidence-report.md"
        )
        content = report_path.read_text(encoding="utf-8")
        assert "No external evidence files found" in content


# ---------------------------------------------------------------------------
# S02 — External Evidence Summary
# ---------------------------------------------------------------------------


class TestExternalEvidenceSummary:
    """Summary computation from external evidence artifacts."""

    def test_single_connector_summary(self, repo_with_external: Path) -> None:
        from pharabius.core.connectors.review import build_external_evidence_summary

        s = build_external_evidence_summary(repo_with_external)
        assert s.external_files_total == 1
        assert s.external_files_readable == 1
        assert s.external_items_total == 2
        assert s.connector_counts == {"sarif": 2}
        assert s.confidence_distribution == {"High": 1, "Medium": 1}
        assert s.top_rules == [("python/sql-injection", 1), ("python/xss", 1)]

    def test_multiple_connectors_summary(self, repo_with_multiple_connectors: Path) -> None:
        from pharabius.core.connectors.review import build_external_evidence_summary

        s = build_external_evidence_summary(repo_with_multiple_connectors)
        assert s.external_files_total == 2
        assert s.external_items_total == 5
        assert "syft" in s.connector_counts
        assert "trivy" in s.connector_counts
        assert s.top_packages[0] == ("requests", 2)  # Most common package

    def test_severity_distribution(self, repo_with_multiple_connectors: Path) -> None:
        from pharabius.core.connectors.review import build_external_evidence_summary

        s = build_external_evidence_summary(repo_with_multiple_connectors)
        assert s.severity_distribution == {"Critical": 2, "High": 1}

    def test_deterministic_ordering(self, repo_with_multiple_connectors: Path) -> None:
        from pharabius.core.connectors.review import build_external_evidence_summary

        s1 = build_external_evidence_summary(repo_with_multiple_connectors)
        s2 = build_external_evidence_summary(repo_with_multiple_connectors)
        assert list(s1.connector_counts.keys()) == list(s2.connector_counts.keys())
        assert s1.top_rules == s2.top_rules
        assert s1.top_packages == s2.top_packages


# ---------------------------------------------------------------------------
# S03 — Malformed Artifacts
# ---------------------------------------------------------------------------


class TestMalformedArtifacts:
    """Malformed files produce warnings, not failures."""

    def test_malformed_file_warning(self, repo_with_malformed: Path) -> None:
        from pharabius.core.connectors.review import build_external_evidence_summary

        s = build_external_evidence_summary(repo_with_malformed)
        assert s.external_files_total == 2
        assert s.external_files_readable == 1
        assert s.external_files_malformed == 1
        assert len(s.warnings) == 1
        assert "Malformed" in s.warnings[0]
        assert "bad-corrupted.json" in s.warnings[0]

    def test_malformed_report_includes_warning(self, repo_with_malformed: Path) -> None:
        from pharabius.core.connectors.review import (
            build_external_evidence_summary,
            render_external_evidence_report,
        )

        s = build_external_evidence_summary(repo_with_malformed)
        report = render_external_evidence_report(s)
        assert "Warnings" in report
        assert "bad-corrupted.json" in report


# ---------------------------------------------------------------------------
# S04 — Combined Evidence and Manifest
# ---------------------------------------------------------------------------


class TestCombinedEvidenceRendering:
    """Combined evidence and manifest rendering."""

    def test_combined_evidence_summary(self, repo_with_combined: Path) -> None:
        from pharabius.core.connectors.review import build_external_evidence_summary

        s = build_external_evidence_summary(repo_with_combined)
        assert s.combined_present
        assert s.combined_readable
        assert s.combined_total_count == 2
        assert s.combined_native_count == 1
        assert s.combined_external_count == 1
        assert s.manifest_present
        assert s.manifest_imported == 1

    def test_combined_report_content(self, repo_with_combined: Path) -> None:
        from pharabius.core.connectors.review import (
            build_external_evidence_summary,
            render_external_evidence_report,
        )

        s = build_external_evidence_summary(repo_with_combined)
        report = render_external_evidence_report(s)
        assert "Combined store: **present**" in report
        assert "Total items: 2" in report
        assert "Native items: 1" in report
        assert "External items: 1" in report
        assert "Combination Manifest" in report
        assert "Imported: 1" in report


# ---------------------------------------------------------------------------
# S05 — Status Reader
# ---------------------------------------------------------------------------


class TestStatusReaderExternal:
    """Status reader shows external and combined evidence."""

    def test_no_external_status(self, repo_with_no_external: Path) -> None:
        from pharabius.core.status_reader import read_status

        # Need minimal artifacts
        ai_debt = repo_with_no_external / ".ai-debt"
        (ai_debt / "project-profile.json").write_text(
            json.dumps(
                {
                    "project_name": "test",
                    "repository_root": str(repo_with_no_external),
                }
            )
        )
        (ai_debt / "evidence.json").write_text(
            json.dumps(
                {
                    "repository": "test",
                    "evidence": [],
                }
            )
        )
        (ai_debt / "debt-register.json").write_text(
            json.dumps(
                {
                    "project_name": "test",
                    "summary": {
                        "total_findings": 0,
                        "critical": 0,
                        "high": 0,
                        "medium": 0,
                        "low": 0,
                    },
                }
            )
        )

        status = read_status(repo_with_no_external)
        assert "Ext. evidence: absent" in status
        assert "Combined:     absent" in status

    def test_with_external_status(self, repo_with_combined: Path) -> None:
        from pharabius.core.status_reader import read_status

        # Need minimal artifacts
        ai_debt = repo_with_combined / ".ai-debt"
        (ai_debt / "project-profile.json").write_text(
            json.dumps(
                {
                    "project_name": "test",
                    "repository_root": str(repo_with_combined),
                }
            )
        )
        (ai_debt / "debt-register.json").write_text(
            json.dumps(
                {
                    "project_name": "test",
                    "summary": {
                        "total_findings": 0,
                        "critical": 0,
                        "high": 0,
                        "medium": 0,
                        "low": 0,
                    },
                }
            )
        )

        status = read_status(repo_with_combined)
        assert "Ext. evidence:" in status
        assert "Combined:" in status

    def test_malformed_status(self, repo_with_malformed: Path) -> None:
        from pharabius.core.status_reader import read_status

        ai_debt = repo_with_malformed / ".ai-debt"
        (ai_debt / "project-profile.json").write_text(
            json.dumps(
                {
                    "project_name": "test",
                    "repository_root": str(repo_with_malformed),
                }
            )
        )
        (ai_debt / "evidence.json").write_text(
            json.dumps(
                {
                    "repository": "test",
                    "evidence": [],
                }
            )
        )
        (ai_debt / "debt-register.json").write_text(
            json.dumps(
                {
                    "project_name": "test",
                    "summary": {
                        "total_findings": 0,
                        "critical": 0,
                        "high": 0,
                        "medium": 0,
                        "low": 0,
                    },
                }
            )
        )

        status = read_status(repo_with_malformed)
        assert "Ext. evidence:" in status
        assert "1 malformed" in status


# ---------------------------------------------------------------------------
# S06 — Existing Reports Unchanged
# ---------------------------------------------------------------------------


class TestExistingReportsUnchanged:
    """Existing reports are not modified by the new external evidence report."""

    def test_existing_reports_still_written(self, repo_with_no_external: Path) -> None:
        from pharabius.core.reporter import write_reports

        ai_debt = repo_with_no_external / ".ai-debt"
        (ai_debt / "project-profile.json").write_text(
            json.dumps(
                {
                    "project_name": "test",
                    "repository_root": str(repo_with_no_external),
                }
            )
        )
        (ai_debt / "evidence.json").write_text(
            json.dumps(
                {
                    "repository": "test",
                    "evidence": [],
                }
            )
        )
        (ai_debt / "debt-register.json").write_text(
            json.dumps(
                {
                    "project_name": "test",
                    "summary": {
                        "total_findings": 0,
                        "critical": 0,
                        "high": 0,
                        "medium": 0,
                        "low": 0,
                    },
                }
            )
        )

        result = write_reports(repo_with_no_external)
        report_names = [p.name for p in result.files_written]

        expected = [
            "architecture-map.md",
            "dependency-health.md",
            "test-health.md",
            "security-exposure.md",
            "business-risk-proxy.md",
            "foundation-audit-report.md",
            "external-evidence-report.md",
        ]
        for name in expected:
            assert name in report_names, f"Missing report: {name}"

    def test_foundation_report_content_unchanged(self, repo_with_no_external: Path) -> None:
        from pharabius.core.reporter import write_reports

        ai_debt = repo_with_no_external / ".ai-debt"
        (ai_debt / "project-profile.json").write_text(
            json.dumps(
                {
                    "project_name": "test",
                    "repository_root": str(repo_with_no_external),
                }
            )
        )
        (ai_debt / "evidence.json").write_text(
            json.dumps(
                {
                    "repository": "test",
                    "evidence": [],
                }
            )
        )
        (ai_debt / "debt-register.json").write_text(
            json.dumps(
                {
                    "project_name": "test",
                    "summary": {
                        "total_findings": 0,
                        "critical": 0,
                        "high": 0,
                        "medium": 0,
                        "low": 0,
                    },
                }
            )
        )

        result = write_reports(repo_with_no_external)
        foundation_path = next(
            p for p in result.files_written if p.name == "foundation-audit-report.md"
        )
        content = foundation_path.read_text(encoding="utf-8")
        assert "Foundation Technical Debt Audit Report" in content
        # No external evidence section in foundation
        pre_evidence = content.lower().split("evidence")[0]
        assert "external" not in pre_evidence.split()[:3]


# ---------------------------------------------------------------------------
# S07 — Review Warnings and Safety
# ---------------------------------------------------------------------------


class TestReviewWarningsAndSafety:
    """Report surfaces warnings without failing."""

    def test_report_always_generated(self, repo_with_no_external: Path) -> None:
        from pharabius.core.connectors.review import (
            ExternalEvidenceSummary,
            render_external_evidence_report,
        )

        # Even with completely empty summary
        s = ExternalEvidenceSummary()
        report = render_external_evidence_report(s)
        assert "# External Evidence Review" in report
        assert "No external evidence files found" in report

    def test_report_explicitly_states_not_findings(self, repo_with_external: Path) -> None:
        from pharabius.core.connectors.review import (
            build_external_evidence_summary,
            render_external_evidence_report,
        )

        s = build_external_evidence_summary(repo_with_external)
        report = render_external_evidence_report(s)
        assert "confirmed findings" in report

    def test_no_scanner_execution(self, repo_with_external: Path) -> None:
        from pharabius.core.connectors.review import build_external_evidence_summary

        # Summary should be computed purely from existing files
        s = build_external_evidence_summary(repo_with_external)
        assert s.external_items_total == 2  # Only from the files we created
        # No network, no subprocess, no scanner


# ---------------------------------------------------------------------------
# S08 — Platform Assessment (Edge Cases)
# ---------------------------------------------------------------------------


class TestPlatformAssessment:
    """Edge cases and platform safety."""

    def test_empty_external_dir(self, tmp_path: Path) -> None:
        from pharabius.core.connectors.review import build_external_evidence_summary

        repo = tmp_path / "repo"
        repo.mkdir()
        ai_debt = repo / ".ai-debt"
        ai_debt.mkdir()
        ext_dir = ai_debt / "external-evidence"
        ext_dir.mkdir()
        # Empty dir — no files

        s = build_external_evidence_summary(repo)
        assert s.external_files_total == 0
        assert s.external_items_total == 0

    def test_combined_unreadable(self, tmp_path: Path) -> None:
        from pharabius.core.connectors.review import build_external_evidence_summary

        repo = tmp_path / "repo"
        repo.mkdir()
        ai_debt = repo / ".ai-debt"
        ai_debt.mkdir()
        (ai_debt / "combined-evidence.json").write_text("BROKEN{")

        s = build_external_evidence_summary(repo)
        assert s.combined_present
        assert not s.combined_readable

    def test_manifest_unreadable(self, tmp_path: Path) -> None:
        from pharabius.core.connectors.review import build_external_evidence_summary

        repo = tmp_path / "repo"
        repo.mkdir()
        ai_debt = repo / ".ai-debt"
        ai_debt.mkdir()
        (ai_debt / "combined-evidence-manifest.json").write_text("BROKEN{")

        s = build_external_evidence_summary(repo)
        assert s.manifest_present
        assert not s.manifest_readable

    def test_non_dict_evidence_file(self, tmp_path: Path) -> None:
        from pharabius.core.connectors.review import build_external_evidence_summary

        repo = tmp_path / "repo"
        repo.mkdir()
        ai_debt = repo / ".ai-debt"
        ai_debt.mkdir()
        ext_dir = ai_debt / "external-evidence"
        ext_dir.mkdir()
        (ext_dir / "list.json").write_text("[1, 2, 3]")

        s = build_external_evidence_summary(repo)
        assert s.external_files_total == 1
        assert s.external_files_malformed == 1
        assert s.external_items_total == 0
