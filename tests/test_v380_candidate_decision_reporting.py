"""Tests for v3.8.0 — Candidate Decision Reporting and Audit Trail.

Covers:
- Candidate decision summary in reports
- Lifecycle audit trail in reports
- Orphaned decision warnings
- Governance export candidate decisions
- Status reader candidate decision summary
- No mutation of any artifact

Key invariant:
Candidate decisions are visible and auditable,
but no candidate becomes an accepted finding.
"""

from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.connectors.candidate import write_candidate_artifact
from pharabius.core.connectors.candidate_review import review_candidate
from pharabius.core.governance_export import (
    build_candidate_decisions_summary,
    build_governance_export,
)
from pharabius.schemas.candidate import (
    CandidateFinding,
    CandidateFindingsArtifact,
    CandidateProvenance,
)
from pharabius.schemas.review import DecisionStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_candidate(
    candidate_id: str = "CAND-0001",
    connector_name: str = "trivy",
) -> CandidateFinding:
    return CandidateFinding(
        id=candidate_id,
        category="TD-VULN",
        title=f"Test finding {candidate_id}",
        description="Test",
        provenance=CandidateProvenance(
            connector_name=connector_name,
            source_format=connector_name,
            evidence_count=1,
            evidence_ids=["EXT-001"],
            source_types=["external_scanner_result"],
        ),
    )


def _setup_workspace(
    tmp_path: Path,
    *candidates: CandidateFinding,
) -> Path:
    from collections import Counter

    by_connector = dict(Counter(c.provenance.connector_name for c in candidates))
    by_category = dict(Counter(c.category for c in candidates))

    from pharabius.schemas.candidate import CandidateFindingsSummary

    summary = CandidateFindingsSummary(
        total_candidates=len(candidates),
        by_connector=by_connector,
        by_category=by_category,
    )
    artifact = CandidateFindingsArtifact(candidates=list(candidates), summary=summary)
    write_candidate_artifact(artifact, tmp_path)
    ai_debt = tmp_path / ".ai-debt"
    ai_debt.mkdir(exist_ok=True)
    (ai_debt / "project-profile.json").write_text(
        json.dumps({"project_name": "test", "repository_root": str(tmp_path)})
    )
    (ai_debt / "evidence.json").write_text(json.dumps({"repository": "test", "evidence": []}))
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
    return tmp_path


# ---------------------------------------------------------------------------
# S03: Candidate decision report section
# ---------------------------------------------------------------------------


class TestCandidateDecisionReport:
    """Report shows candidate review decisions."""

    def test_report_shows_review_decision_summary(self, tmp_path: Path) -> None:
        from pharabius.core.reporter import write_reports

        _setup_workspace(
            tmp_path,
            _make_candidate("CAND-0001"),
            _make_candidate("CAND-0002"),
            _make_candidate("CAND-0003"),
        )
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED, reviewer="alice")
        review_candidate(tmp_path, "CAND-0002", DecisionStatus.REJECTED, reviewer="bob")

        result = write_reports(tmp_path)
        foundation = next(p for p in result.files_written if p.name == "foundation-audit-report.md")
        content = foundation.read_text(encoding="utf-8")

        assert "Review Decision Summary" in content
        assert "CandidateAccepted" in content
        assert "CandidateRejected" in content
        assert "Pending review" in content

    def test_report_shows_reviewer_on_candidates(self, tmp_path: Path) -> None:
        from pharabius.core.reporter import write_reports

        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED, reviewer="alice")

        result = write_reports(tmp_path)
        foundation = next(p for p in result.files_written if p.name == "foundation-audit-report.md")
        content = foundation.read_text(encoding="utf-8")

        assert "alice" in content

    def test_report_shows_review_level_only_label(self, tmp_path: Path) -> None:
        from pharabius.core.reporter import write_reports

        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        result = write_reports(tmp_path)
        foundation = next(p for p in result.files_written if p.name == "foundation-audit-report.md")
        content = foundation.read_text(encoding="utf-8")

        assert "review-level only" in content

    def test_report_no_decisions_shows_pending(self, tmp_path: Path) -> None:
        from pharabius.core.reporter import write_reports

        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))

        result = write_reports(tmp_path)
        foundation = next(p for p in result.files_written if p.name == "foundation-audit-report.md")
        content = foundation.read_text(encoding="utf-8")

        assert "Pending review" in content

    def test_report_without_candidates_no_candidate_section(self, tmp_path: Path) -> None:
        from pharabius.core.reporter import write_reports

        _setup_workspace(tmp_path)  # No candidates

        result = write_reports(tmp_path)
        foundation = next(p for p in result.files_written if p.name == "foundation-audit-report.md")
        content = foundation.read_text(encoding="utf-8")

        assert "Candidate Findings" not in content


# ---------------------------------------------------------------------------
# S03: Lifecycle audit trail in report
# ---------------------------------------------------------------------------


class TestLifecycleAuditTrail:
    """Report shows lifecycle audit trail for candidates."""

    def test_report_shows_lifecycle_audit_trail(self, tmp_path: Path) -> None:
        from pharabius.core.reporter import write_reports

        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(
            tmp_path,
            "CAND-0001",
            DecisionStatus.ACCEPTED,
            reviewer="alice",
            rationale="Confirmed real vulnerability",
        )

        result = write_reports(tmp_path)
        foundation = next(p for p in result.files_written if p.name == "foundation-audit-report.md")
        content = foundation.read_text(encoding="utf-8")

        assert "Candidate Lifecycle Audit Trail" in content
        assert "Candidate" in content  # from_status
        assert "CandidateAccepted" in content  # to_status
        assert "alice" in content  # actor

    def test_report_shows_rationale_in_audit_trail(self, tmp_path: Path) -> None:
        from pharabius.core.reporter import write_reports

        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(
            tmp_path,
            "CAND-0001",
            DecisionStatus.REJECTED,
            rationale="False positive — test fixture",
        )

        result = write_reports(tmp_path)
        foundation = next(p for p in result.files_written if p.name == "foundation-audit-report.md")
        content = foundation.read_text(encoding="utf-8")

        assert "False positive" in content

    def test_report_no_audit_trail_without_lifecycle_history(self, tmp_path: Path) -> None:
        from pharabius.core.reporter import write_reports

        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        # No review → no lifecycle history

        result = write_reports(tmp_path)
        foundation = next(p for p in result.files_written if p.name == "foundation-audit-report.md")
        content = foundation.read_text(encoding="utf-8")

        assert "Lifecycle Audit Trail" not in content


# ---------------------------------------------------------------------------
# S06: Orphaned decision warnings
# ---------------------------------------------------------------------------


class TestOrphanedDecisionWarnings:
    """Report warns about decisions for unknown candidates."""

    def test_orphaned_decision_warning_in_report(self, tmp_path: Path) -> None:
        from pharabius.core.reporter import write_reports

        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))

        # Manually inject an orphaned decision
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        # Add orphaned decision manually
        sidecar = tmp_path / ".ai-debt" / "review" / "decisions.json"
        data = json.loads(sidecar.read_text())
        data["decisions"].append(
            {
                "finding_id": "CAND-9999",
                "status": "accepted",
                "reviewed_at": "2026-06-07T00:00:00Z",
                "reviewer": "test",
            }
        )
        sidecar.write_text(json.dumps(data, indent=2) + "\n")

        result = write_reports(tmp_path)
        foundation = next(p for p in result.files_written if p.name == "foundation-audit-report.md")
        content = foundation.read_text(encoding="utf-8")

        assert "Warning" in content
        assert "CAND-9999" in content


# ---------------------------------------------------------------------------
# S05: Governance export visibility
# ---------------------------------------------------------------------------


class TestGovernanceExportCandidateDecisions:
    """Governance export includes candidate decision summary."""

    def test_export_includes_candidate_decisions(self) -> None:
        summary = build_candidate_decisions_summary(
            total_candidates=5,
            accepted=2,
            rejected=1,
            deferred=0,
            pending=2,
            by_connector={"trivy": 3, "sarif": 2},
        )
        export = build_governance_export(candidate_decisions=summary)

        assert "candidate_decisions" in export
        assert export["candidate_decisions"]["total_candidates"] == 5
        assert export["candidate_decisions"]["accepted"] == 2
        assert export["candidate_decisions"]["rejected"] == 1
        assert export["candidate_decisions"]["pending"] == 2

    def test_export_without_candidate_decisions(self) -> None:
        export = build_governance_export()
        assert "candidate_decisions" not in export

    def test_export_no_forbidden_fields(self) -> None:
        summary = build_candidate_decisions_summary()
        for key in summary:
            assert key.lower() not in {
                "pass",
                "fail",
                "score",
                "grade",
                "compliant",
                "noncompliant",
                "healthy",
                "unhealthy",
            }

    def test_export_additive_only(self) -> None:
        """Existing fields still present when candidate_decisions added."""
        export = build_governance_export(candidate_decisions={})
        assert "schema_version" in export
        assert "governance_quality" in export
        assert "governance_trends" in export

    def test_build_summary_defaults(self) -> None:
        summary = build_candidate_decisions_summary()
        assert summary["total_candidates"] == 0
        assert summary["accepted"] == 0
        assert summary["rejected"] == 0
        assert summary["deferred"] == 0
        assert summary["pending"] == 0
        assert summary["by_connector"] == {}


# ---------------------------------------------------------------------------
# S04: Status reader candidate decision summary
# ---------------------------------------------------------------------------


class TestStatusReaderCandidateDecisions:
    """Status reader shows candidate review decisions."""

    def test_status_shows_reviewed_counts(self, tmp_path: Path) -> None:
        from pharabius.core.status_reader import read_status

        _setup_workspace(
            tmp_path,
            _make_candidate("CAND-0001"),
            _make_candidate("CAND-0002"),
        )
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)
        review_candidate(tmp_path, "CAND-0002", DecisionStatus.REJECTED)

        status = read_status(tmp_path)
        assert "Reviewed:" in status
        assert "accepted" in status
        assert "rejected" in status

    def test_status_shows_pending(self, tmp_path: Path) -> None:
        from pharabius.core.status_reader import read_status

        _setup_workspace(
            tmp_path,
            _make_candidate("CAND-0001"),
            _make_candidate("CAND-0002"),
        )
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        status = read_status(tmp_path)
        assert "Pending" in status

    def test_status_no_candidate_artifact(self, tmp_path: Path) -> None:
        """Status reader handles missing candidate artifact gracefully."""
        from pharabius.core.status_reader import read_status

        # Minimal workspace without candidates
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        (ai_debt / "project-profile.json").write_text(
            json.dumps({"project_name": "test", "repository_root": str(tmp_path)})
        )
        status = read_status(tmp_path)
        # Candidates section absent when no artifact
        assert "Candidates:" not in status


# ---------------------------------------------------------------------------
# S07: No mutation
# ---------------------------------------------------------------------------


class TestNoMutation:
    """Reporting does not mutate any artifact."""

    def test_candidate_artifact_unchanged_after_report(self, tmp_path: Path) -> None:
        from pharabius.core.reporter import write_reports

        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        cand_path = tmp_path / ".ai-debt" / "candidate-findings.json"
        orig = cand_path.read_text()

        write_reports(tmp_path)

        assert cand_path.read_text() == orig

    def test_debt_register_unchanged_after_report(self, tmp_path: Path) -> None:
        from pharabius.core.reporter import write_reports

        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        reg_path = tmp_path / ".ai-debt" / "debt-register.json"
        orig = reg_path.read_text()

        write_reports(tmp_path)

        assert reg_path.read_text() == orig

    def test_lifecycle_history_unchanged_after_report(self, tmp_path: Path) -> None:
        from pharabius.core.reporter import write_reports

        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        lh_path = tmp_path / ".ai-debt" / "lifecycle-history.json"
        orig = lh_path.read_text()

        write_reports(tmp_path)

        assert lh_path.read_text() == orig

    def test_review_sidecar_unchanged_after_report(self, tmp_path: Path) -> None:
        from pharabius.core.reporter import write_reports

        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        sidecar = tmp_path / ".ai-debt" / "review" / "decisions.json"
        orig = sidecar.read_text()

        write_reports(tmp_path)

        assert sidecar.read_text() == orig


# ---------------------------------------------------------------------------
# No debt-register promotion
# ---------------------------------------------------------------------------


class TestNoDebtRegisterPromotion:
    """Reporting does not promote candidates to findings."""

    def test_no_finding_created_from_accepted_candidate(self, tmp_path: Path) -> None:
        from pharabius.core.reporter import write_reports

        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        write_reports(tmp_path)

        reg = json.loads((tmp_path / ".ai-debt" / "debt-register.json").read_text())
        assert reg["summary"]["total_findings"] == 0

    def test_no_work_packages_from_candidates(self, tmp_path: Path) -> None:
        from pharabius.core.reporter import write_reports

        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        write_reports(tmp_path)

        assert not (tmp_path / ".ai-debt" / "work-packages").exists()
