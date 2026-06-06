"""Tests for v3.9.0 — Candidate Promotion Gate.

Gate-only: checks eligibility for promotion without performing it.
No writing to debt-register.json. No creating DebtFinding.
No work packages. No tickets. No mutation.

Key invariant:
Pharabius can answer "Is this candidate eligible for promotion?"
without actually promoting it.
"""

from __future__ import annotations

from pathlib import Path

from pharabius.core.connectors.candidate import write_candidate_artifact
from pharabius.core.connectors.candidate_gate import (
    GateCheck,
    GateStatus,
    check_all_promotion_eligibility,
    check_promotion_eligibility,
    format_batch_eligibility_report,
    format_eligibility_report,
)
from pharabius.core.connectors.candidate_review import review_candidate
from pharabius.schemas.candidate import (
    CandidateFinding,
    CandidateFindingsArtifact,
    CandidateFindingsSummary,
    CandidateProvenance,
)
from pharabius.schemas.review import DecisionStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_candidate(
    candidate_id: str = "CAND-0001",
    connector_name: str = "trivy",
    category: str = "TD-VULN",
    title: str = "Test vulnerability",
    description: str = "A real security issue",
    evidence_ids: list[str] | None = None,
) -> CandidateFinding:
    return CandidateFinding(
        id=candidate_id,
        category=category,
        title=title,
        description=description,
        provenance=CandidateProvenance(
            connector_name=connector_name,
            source_format=connector_name,
            evidence_count=len(evidence_ids) if evidence_ids else 1,
            evidence_ids=evidence_ids or ["EXT-001"],
            source_types=["external_scanner_result"],
        ),
        evidence_ids=evidence_ids or ["EXT-001"],
    )


def _setup_workspace(
    tmp_path: Path,
    *candidates: CandidateFinding,
) -> Path:
    from collections import Counter

    by_connector = dict(Counter(c.provenance.connector_name for c in candidates))
    by_category = dict(Counter(c.category for c in candidates))
    summary = CandidateFindingsSummary(
        total_candidates=len(candidates),
        by_connector=by_connector,
        by_category=by_category,
    )
    artifact = CandidateFindingsArtifact(candidates=list(candidates), summary=summary)
    write_candidate_artifact(artifact, tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Eligibility: candidate exists
# ---------------------------------------------------------------------------


class TestCandidateExists:
    """Gate checks candidate exists."""

    def test_unknown_candidate_not_eligible(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        result = check_promotion_eligibility(tmp_path, "CAND-9999")
        assert not result.eligible
        assert any(c.check == GateCheck.CANDIDATE_EXISTS and not c.passed for c in result.checks)

    def test_known_candidate_passes_existence(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        assert any(c.check == GateCheck.CANDIDATE_EXISTS and c.passed for c in result.checks)


# ---------------------------------------------------------------------------
# Eligibility: accepted decision
# ---------------------------------------------------------------------------


class TestAcceptedDecision:
    """Gate checks candidate has accepted review decision."""

    def test_no_decision_not_eligible(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        assert not result.eligible
        assert any(
            c.check == GateCheck.HAS_ACCEPTED_DECISION and not c.passed for c in result.checks
        )

    def test_rejected_decision_not_eligible(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.REJECTED, reviewer="alice")
        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        assert not result.eligible
        assert any(
            c.check == GateCheck.HAS_ACCEPTED_DECISION and not c.passed for c in result.checks
        )

    def test_accepted_decision_passes(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED, reviewer="alice")
        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        assert any(c.check == GateCheck.HAS_ACCEPTED_DECISION and c.passed for c in result.checks)


# ---------------------------------------------------------------------------
# Eligibility: reviewer and rationale
# ---------------------------------------------------------------------------


class TestReviewerRationale:
    """Gate checks reviewer and rationale are present."""

    def test_no_reviewer_not_eligible(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(
            tmp_path,
            "CAND-0001",
            DecisionStatus.ACCEPTED,
            reviewer="",
            rationale="Good reason",
        )
        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        assert not result.eligible
        assert any(c.check == GateCheck.HAS_REVIEWER and not c.passed for c in result.checks)

    def test_no_rationale_not_eligible(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(
            tmp_path,
            "CAND-0001",
            DecisionStatus.ACCEPTED,
            reviewer="alice",
            rationale="",
        )
        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        assert not result.eligible
        assert any(c.check == GateCheck.HAS_RATIONALE and not c.passed for c in result.checks)

    def test_with_reviewer_and_rationale_passes(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(
            tmp_path,
            "CAND-0001",
            DecisionStatus.ACCEPTED,
            reviewer="alice",
            rationale="Confirmed vulnerability",
        )
        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        assert any(c.check == GateCheck.HAS_REVIEWER and c.passed for c in result.checks)
        assert any(c.check == GateCheck.HAS_RATIONALE and c.passed for c in result.checks)


# ---------------------------------------------------------------------------
# Eligibility: evidence and provenance
# ---------------------------------------------------------------------------


class TestEvidenceProvenance:
    """Gate checks evidence IDs and provenance."""

    def test_no_evidence_ids_not_eligible(self, tmp_path: Path) -> None:
        _setup_workspace(
            tmp_path,
            CandidateFinding(
                id="CAND-0001",
                category="TD-VULN",
                title="Test",
                description="Test",
                evidence_ids=[],
                provenance=CandidateProvenance(
                    connector_name="trivy",
                    source_format="trivy",
                    evidence_count=0,
                    evidence_ids=[],
                    source_types=["external_scanner_result"],
                ),
            ),
        )
        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        assert any(c.check == GateCheck.HAS_EVIDENCE_IDS and not c.passed for c in result.checks)

    def test_has_evidence_ids_passes(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        assert any(c.check == GateCheck.HAS_EVIDENCE_IDS and c.passed for c in result.checks)

    def test_has_provenance_passes(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        assert any(c.check == GateCheck.HAS_PROVENANCE and c.passed for c in result.checks)


# ---------------------------------------------------------------------------
# Eligibility: title, category, description
# ---------------------------------------------------------------------------


class TestRequiredFields:
    """Gate checks title, category, description."""

    def test_has_title_passes(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        assert any(c.check == GateCheck.HAS_TITLE and c.passed for c in result.checks)

    def test_has_category_passes(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        assert any(c.check == GateCheck.HAS_CATEGORY and c.passed for c in result.checks)

    def test_has_description_passes(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        assert any(c.check == GateCheck.HAS_DESCRIPTION and c.passed for c in result.checks)


# ---------------------------------------------------------------------------
# Full eligible candidate
# ---------------------------------------------------------------------------


class TestFullyEligible:
    """Candidate with all checks passing is eligible."""

    def test_fully_eligible_candidate(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(
            tmp_path,
            "CAND-0001",
            DecisionStatus.ACCEPTED,
            reviewer="alice",
            rationale="Confirmed real vulnerability",
        )

        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        assert result.eligible
        assert result.status == GateStatus.ELIGIBLE
        assert len(result.blocking_reasons) == 0

    def test_all_checks_pass(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(
            tmp_path,
            "CAND-0001",
            DecisionStatus.ACCEPTED,
            reviewer="alice",
            rationale="Confirmed",
        )

        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        for check in result.checks:
            assert check.passed, f"{check.check.value} failed: {check.reason}"


# ---------------------------------------------------------------------------
# No mutation
# ---------------------------------------------------------------------------


class TestNoMutation:
    """Gate check does not modify any artifact."""

    def test_candidate_artifact_unchanged(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        cand_path = tmp_path / ".ai-debt" / "candidate-findings.json"
        orig = cand_path.read_text()

        check_promotion_eligibility(tmp_path, "CAND-0001")

        assert cand_path.read_text() == orig

    def test_debt_register_not_created(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(
            tmp_path,
            "CAND-0001",
            DecisionStatus.ACCEPTED,
            reviewer="alice",
            rationale="Good",
        )

        check_promotion_eligibility(tmp_path, "CAND-0001")

        assert not (tmp_path / ".ai-debt" / "debt-register.json").exists()

    def test_no_work_packages_created(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(
            tmp_path,
            "CAND-0001",
            DecisionStatus.ACCEPTED,
            reviewer="alice",
            rationale="Good",
        )

        check_promotion_eligibility(tmp_path, "CAND-0001")

        assert not (tmp_path / ".ai-debt" / "work-packages").exists()


# ---------------------------------------------------------------------------
# Batch eligibility
# ---------------------------------------------------------------------------


class TestBatchEligibility:
    """Batch check for all candidates."""

    def test_empty_workspace(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path)
        batch = check_all_promotion_eligibility(tmp_path)
        assert batch.total_candidates == 0
        assert batch.eligible_count == 0

    def test_mixed_eligibility(self, tmp_path: Path) -> None:
        _setup_workspace(
            tmp_path,
            _make_candidate("CAND-0001"),
            _make_candidate("CAND-0002"),
            _make_candidate("CAND-0003"),
        )
        # Only CAND-0001 is fully reviewed
        review_candidate(
            tmp_path,
            "CAND-0001",
            DecisionStatus.ACCEPTED,
            reviewer="alice",
            rationale="Good",
        )
        # CAND-0002 rejected
        review_candidate(
            tmp_path,
            "CAND-0002",
            DecisionStatus.REJECTED,
            reviewer="bob",
            rationale="False positive",
        )
        # CAND-0003 has no review

        batch = check_all_promotion_eligibility(tmp_path)
        assert batch.total_candidates == 3
        assert "CAND-0001" in batch.eligible
        assert "CAND-0002" in batch.not_eligible
        assert "CAND-0003" in batch.not_eligible

    def test_batch_no_mutation(self, tmp_path: Path) -> None:
        _setup_workspace(
            tmp_path,
            _make_candidate("CAND-0001"),
            _make_candidate("CAND-0002"),
        )
        review_candidate(
            tmp_path,
            "CAND-0001",
            DecisionStatus.ACCEPTED,
            reviewer="alice",
            rationale="Good",
        )

        orig_cand = (tmp_path / ".ai-debt" / "candidate-findings.json").read_text()

        check_all_promotion_eligibility(tmp_path)

        assert (tmp_path / ".ai-debt" / "candidate-findings.json").read_text() == orig_cand


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


class TestFormatting:
    """Eligibility reports format correctly."""

    def test_single_eligibility_report(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(
            tmp_path,
            "CAND-0001",
            DecisionStatus.ACCEPTED,
            reviewer="alice",
            rationale="Good",
        )

        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        text = format_eligibility_report(result)
        assert "CAND-0001" in text
        assert "eligible" in text

    def test_single_not_eligible_report(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        text = format_eligibility_report(result)
        assert "not_eligible" in text
        assert "Blocking" in text

    def test_batch_report(self, tmp_path: Path) -> None:
        _setup_workspace(
            tmp_path,
            _make_candidate("CAND-0001"),
            _make_candidate("CAND-0002"),
        )
        review_candidate(
            tmp_path,
            "CAND-0001",
            DecisionStatus.ACCEPTED,
            reviewer="alice",
            rationale="Good",
        )

        batch = check_all_promotion_eligibility(tmp_path)
        text = format_batch_eligibility_report(batch)
        assert "Eligible:" in text
        assert "not promoted" in text or "gate-only" in text
        assert "CAND-0001" in text


# ---------------------------------------------------------------------------
# Gate checks: 9 checks total
# ---------------------------------------------------------------------------


class TestAllNineChecks:
    """All 9 gate checks run for existing candidates."""

    def test_nine_checks_run(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        check_types = {c.check for c in result.checks}
        assert len(check_types) == 9
        assert GateCheck.CANDIDATE_EXISTS in check_types
        assert GateCheck.HAS_ACCEPTED_DECISION in check_types
        assert GateCheck.HAS_REVIEWER in check_types
        assert GateCheck.HAS_RATIONALE in check_types
        assert GateCheck.HAS_EVIDENCE_IDS in check_types
        assert GateCheck.HAS_PROVENANCE in check_types
        assert GateCheck.HAS_TITLE in check_types
        assert GateCheck.HAS_CATEGORY in check_types
        assert GateCheck.HAS_DESCRIPTION in check_types


# ---------------------------------------------------------------------------
# Empty workspace
# ---------------------------------------------------------------------------


class TestEmptyWorkspace:
    """Gate handles empty workspace gracefully."""

    def test_empty_candidate_artifact(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path)  # No candidates
        result = check_promotion_eligibility(tmp_path, "CAND-0001")
        assert not result.eligible

    def test_batch_empty(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path)
        batch = check_all_promotion_eligibility(tmp_path)
        assert batch.total_candidates == 0
        assert batch.eligible_count == 0
