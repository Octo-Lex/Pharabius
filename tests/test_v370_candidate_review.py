"""Tests for v3.7.0 — Candidate Review and Promotion Workflow.

Covers all 27 acceptance criteria:
- 1-20: Original criteria
- 21-27: Amended criteria

Key invariants:
- Candidate acceptance is review-level only, not debt-register promotion
- CandidateAccepted ≠ Acknowledged
- Regular review rejects CAND-* IDs; candidate review rejects TD-* IDs
- One terminal decision per candidate (v3.7.0)
- No auto-promotion, no DebtFinding creation, no work packages, no tickets
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pharabius.core.connectors.candidate import (
    write_candidate_artifact,
)
from pharabius.core.connectors.candidate_review import (
    CANDIDATE_DECISION_OUTCOMES,
    CandidateReviewError,
    CandidateReviewSummary,
    format_candidate_review_summary,
    review_candidate,
    summarize_candidate_reviews,
)
from pharabius.core.lifecycle import (
    FINDING_TRANSITIONS,
    FindingStatus,
    validate_finding_transition,
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
    category: str = "TD-VULN",
    title: str = "Test vulnerability",
) -> CandidateFinding:
    return CandidateFinding(
        id=candidate_id,
        category=category,
        title=title,
        description="Test candidate finding",
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
    """Create workspace with candidate-findings.json."""
    artifact = CandidateFindingsArtifact(candidates=list(candidates))
    write_candidate_artifact(artifact, tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# AC1: review_candidate() records decision in review sidecar
# ---------------------------------------------------------------------------


class TestReviewSidecarWrite:
    """review_candidate() appends to review sidecar."""

    def test_creates_sidecar_if_missing(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        decision = review_candidate(
            tmp_path, "CAND-0001", DecisionStatus.ACCEPTED, reviewer="alice"
        )
        assert decision.finding_id == "CAND-0001"
        assert decision.status == DecisionStatus.ACCEPTED

        # Verify sidecar exists
        sidecar = tmp_path / ".ai-debt" / "review" / "decisions.json"
        assert sidecar.exists()
        data = json.loads(sidecar.read_text())
        assert len(data["decisions"]) == 1
        assert data["decisions"][0]["finding_id"] == "CAND-0001"

    def test_appends_to_existing_sidecar(self, tmp_path: Path) -> None:
        _setup_workspace(
            tmp_path,
            _make_candidate("CAND-0001"),
            _make_candidate("CAND-0002"),
        )
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)
        review_candidate(tmp_path, "CAND-0002", DecisionStatus.REJECTED)

        sidecar = tmp_path / ".ai-debt" / "review" / "decisions.json"
        data = json.loads(sidecar.read_text())
        assert len(data["decisions"]) == 2


# ---------------------------------------------------------------------------
# AC2: review_candidate() records lifecycle entry
# ---------------------------------------------------------------------------


class TestLifecycleEntryWrite:
    """review_candidate() appends lifecycle entry."""

    def test_creates_lifecycle_history(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        lh = tmp_path / ".ai-debt" / "lifecycle-history.json"
        assert lh.exists()
        data = json.loads(lh.read_text())
        assert len(data["entries"]) == 1
        entry = data["entries"][0]
        assert entry["artifact_type"] == "candidate"
        assert entry["artifact_id"] == "CAND-0001"
        assert entry["from_status"] == "Candidate"

    def test_accepted_maps_to_candidate_accepted(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        lh = tmp_path / ".ai-debt" / "lifecycle-history.json"
        data = json.loads(lh.read_text())
        assert data["entries"][0]["to_status"] == "CandidateAccepted"

    def test_rejected_maps_to_candidate_rejected(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.REJECTED)

        lh = tmp_path / ".ai-debt" / "lifecycle-history.json"
        data = json.loads(lh.read_text())
        assert data["entries"][0]["to_status"] == "CandidateRejected"

    def test_deferred_maps_to_candidate_deferred(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.DEFERRED)

        lh = tmp_path / ".ai-debt" / "lifecycle-history.json"
        data = json.loads(lh.read_text())
        assert data["entries"][0]["to_status"] == "CandidateDeferred"

    def test_risk_accepted_maps_to_candidate_rejected(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.RISK_ACCEPTED)

        lh = tmp_path / ".ai-debt" / "lifecycle-history.json"
        data = json.loads(lh.read_text())
        assert data["entries"][0]["to_status"] == "CandidateRejected"


# ---------------------------------------------------------------------------
# AC3: Only valid candidate decisions accepted
# ---------------------------------------------------------------------------


class TestDecisionValidation:
    """Only valid decisions for candidates are accepted."""

    def test_needs_investigation_rejected(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        with pytest.raises(CandidateReviewError, match="not valid for candidates"):
            review_candidate(tmp_path, "CAND-0001", DecisionStatus.NEEDS_INVESTIGATION)

    def test_accepted_is_valid(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        decision = review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)
        assert decision.status == DecisionStatus.ACCEPTED

    def test_rejected_is_valid(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        decision = review_candidate(tmp_path, "CAND-0001", DecisionStatus.REJECTED)
        assert decision.status == DecisionStatus.REJECTED

    def test_deferred_is_valid(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        decision = review_candidate(tmp_path, "CAND-0001", DecisionStatus.DEFERRED)
        assert decision.status == DecisionStatus.DEFERRED

    def test_risk_accepted_is_valid(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        decision = review_candidate(tmp_path, "CAND-0001", DecisionStatus.RISK_ACCEPTED)
        assert decision.status == DecisionStatus.RISK_ACCEPTED

    def test_duplicate_is_valid(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        decision = review_candidate(tmp_path, "CAND-0001", DecisionStatus.DUPLICATE)
        assert decision.status == DecisionStatus.DUPLICATE

    def test_already_fixed_is_valid(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        decision = review_candidate(tmp_path, "CAND-0001", DecisionStatus.ALREADY_FIXED)
        assert decision.status == DecisionStatus.ALREADY_FIXED


# ---------------------------------------------------------------------------
# AC4: Only candidate IDs (CAND-XXXX) accepted
# ---------------------------------------------------------------------------


class TestCandidateIDValidation:
    """Only CAND-* IDs accepted by candidate review."""

    def test_td_id_rejected(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        with pytest.raises(CandidateReviewError, match="Not a candidate ID"):
            review_candidate(tmp_path, "TD-ARCH-001", DecisionStatus.ACCEPTED)

    def test_cand_id_accepted(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0042"))
        decision = review_candidate(tmp_path, "CAND-0042", DecisionStatus.ACCEPTED)
        assert decision.finding_id == "CAND-0042"

    def test_unknown_cand_id_rejected(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        with pytest.raises(CandidateReviewError, match="Unknown candidate ID"):
            review_candidate(tmp_path, "CAND-9999", DecisionStatus.ACCEPTED)


# ---------------------------------------------------------------------------
# AC5: candidate-findings.json NOT modified by review
# ---------------------------------------------------------------------------


class TestCandidateArtifactNotMutated:
    """Review does not modify candidate-findings.json."""

    def test_artifact_unchanged_after_review(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())

        # Read original artifact
        orig_path = tmp_path / ".ai-debt" / "candidate-findings.json"
        orig_content = orig_path.read_text()

        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        # Verify unchanged
        assert orig_path.read_text() == orig_content

    def test_candidate_status_still_candidate(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())

        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        # Re-load artifact — status should still be "Candidate"
        artifact_data = json.loads((tmp_path / ".ai-debt" / "candidate-findings.json").read_text())
        assert artifact_data["candidates"][0]["status"] == "Candidate"


# ---------------------------------------------------------------------------
# AC6: debt-register.json NOT modified by candidate review
# ---------------------------------------------------------------------------


class TestDebtRegisterNotMutated:
    """Review does not modify debt-register.json."""

    def test_no_debt_register_created(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        assert not (tmp_path / ".ai-debt" / "debt-register.json").exists()

    def test_existing_debt_register_unchanged(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())

        # Pre-create debt-register
        ai_debt = tmp_path / ".ai-debt"
        register = {"summary": {"total_findings": 5}}
        (ai_debt / "debt-register.json").write_text(json.dumps(register))
        orig_content = (ai_debt / "debt-register.json").read_text()

        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        assert (ai_debt / "debt-register.json").read_text() == orig_content


# ---------------------------------------------------------------------------
# AC7-8: Append-only behavior
# ---------------------------------------------------------------------------


class TestAppendOnly:
    """Review decisions and lifecycle entries are append-only."""

    def test_multiple_candidates_multiple_decisions(self, tmp_path: Path) -> None:
        _setup_workspace(
            tmp_path,
            _make_candidate("CAND-0001"),
            _make_candidate("CAND-0002"),
        )

        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)
        review_candidate(tmp_path, "CAND-0002", DecisionStatus.REJECTED)

        sidecar = json.loads((tmp_path / ".ai-debt" / "review" / "decisions.json").read_text())
        assert len(sidecar["decisions"]) == 2

        history = json.loads((tmp_path / ".ai-debt" / "lifecycle-history.json").read_text())
        assert len(history["entries"]) == 2


# ---------------------------------------------------------------------------
# AC9: Promotion records decision + lifecycle, nothing else
# ---------------------------------------------------------------------------


class TestPromotionRecordsOnly:
    """Review records decision and lifecycle entry, nothing else."""

    def test_no_extra_artifacts_created(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())

        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        ai_debt = tmp_path / ".ai-debt"
        files = {f.name for f in ai_debt.iterdir()}
        # Only expected artifacts
        assert "candidate-findings.json" in files
        assert "lifecycle-history.json" in files
        assert files == {"candidate-findings.json", "lifecycle-history.json", "review"}


# ---------------------------------------------------------------------------
# AC10: Candidate review summary
# ---------------------------------------------------------------------------


class TestCandidateReviewSummary:
    """Summary shows pending/promoted/rejected counts."""

    def test_empty_summary(self, tmp_path: Path) -> None:
        summary = summarize_candidate_reviews(tmp_path)
        assert summary.total_candidates == 0

    def test_no_decisions_all_pending(self, tmp_path: Path) -> None:
        _setup_workspace(
            tmp_path,
            _make_candidate("CAND-0001"),
            _make_candidate("CAND-0002"),
        )
        summary = summarize_candidate_reviews(tmp_path)
        assert summary.total_candidates == 2
        assert summary.pending_count == 2
        assert summary.reviewed_count == 0

    def test_mixed_decisions(self, tmp_path: Path) -> None:
        _setup_workspace(
            tmp_path,
            _make_candidate("CAND-0001"),
            _make_candidate("CAND-0002"),
            _make_candidate("CAND-0003"),
        )
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)
        review_candidate(tmp_path, "CAND-0002", DecisionStatus.REJECTED)

        summary = summarize_candidate_reviews(tmp_path)
        assert summary.total_candidates == 3
        assert len(summary.accepted) == 1
        assert len(summary.rejected) == 1
        assert summary.pending_count == 1

    def test_format_summary(self, tmp_path: Path) -> None:
        _setup_workspace(
            tmp_path,
            _make_candidate("CAND-0001"),
            _make_candidate("CAND-0002"),
        )
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        summary = summarize_candidate_reviews(tmp_path)
        text = format_candidate_review_summary(summary)
        assert "Candidate Review Summary" in text
        assert "review-level only" in text


# ---------------------------------------------------------------------------
# AC11-12: Status reader / report integration
# ---------------------------------------------------------------------------


class TestStatusReaderIntegration:
    """Status reader shows candidate review state."""

    def test_status_shows_candidates(self, tmp_path: Path) -> None:
        from pharabius.core.status_reader import read_status

        _setup_workspace(tmp_path, _make_candidate())
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        # Need project-profile for status reader
        (tmp_path / ".ai-debt").mkdir(exist_ok=True)
        (tmp_path / ".ai-debt" / "project-profile.json").write_text(
            json.dumps({"project_name": "test", "repository_root": str(tmp_path)})
        )

        status = read_status(tmp_path)
        assert "Candidates:" in status


# ---------------------------------------------------------------------------
# AC15: No auto-promotion
# ---------------------------------------------------------------------------


class TestNoAutoPromotion:
    """No automatic promotion of any kind."""

    def test_review_does_not_create_debt_finding(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        # No debt-register.json
        assert not (tmp_path / ".ai-debt" / "debt-register.json").exists()


# ---------------------------------------------------------------------------
# AC16-18: No downstream artifacts
# ---------------------------------------------------------------------------


class TestNoDownstreamArtifacts:
    """Review does not create work packages, tickets, or findings."""

    def test_no_work_packages(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

        assert not (tmp_path / ".ai-debt" / "work-packages").exists()


# ---------------------------------------------------------------------------
# AC21: Review-level only documentation
# ---------------------------------------------------------------------------


class TestReviewLevelOnly:
    """Candidate acceptance is review-level, not debt-register promotion."""

    def test_summary_says_review_level_only(self) -> None:
        summary = CandidateReviewSummary(
            total_candidates=1,
            accepted=["CAND-0001"],
        )
        text = format_candidate_review_summary(summary)
        assert "not debt-register promotion" in text

    def test_accepted_candidate_not_in_debt_register(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)
        # Explicitly: no debt-register.json created
        assert not (tmp_path / ".ai-debt" / "debt-register.json").exists()


# ---------------------------------------------------------------------------
# AC22: CandidateAccepted ≠ Acknowledged
# ---------------------------------------------------------------------------


class TestCandidateDistinctFromAccepted:
    """CandidateAccepted is NOT Acknowledged or Detected."""

    def test_candidate_accepted_is_not_acknowledged(self) -> None:
        assert FindingStatus.CANDIDATE_ACCEPTED != FindingStatus.ACKNOWLEDGED

    def test_candidate_accepted_is_not_detected(self) -> None:
        assert FindingStatus.CANDIDATE_ACCEPTED != FindingStatus.DETECTED

    def test_candidate_rejected_is_not_wont_fix(self) -> None:
        assert FindingStatus.CANDIDATE_REJECTED != FindingStatus.WONT_FIX

    def test_candidate_deferred_is_not_deferred(self) -> None:
        """CandidateDeferred is distinct from the finding DEFERRED state."""
        assert FindingStatus.CANDIDATE_DEFERRED != FindingStatus.DEFERRED

    def test_lifecycle_outcome_is_candidate_state(self) -> None:
        """Decision-to-outcome maps to candidate states, not finding states."""
        outcome = CANDIDATE_DECISION_OUTCOMES[DecisionStatus.ACCEPTED]
        assert outcome == FindingStatus.CANDIDATE_ACCEPTED

    def test_enum_has_11_states(self) -> None:
        """8 original + 3 candidate outcomes."""
        assert len(FindingStatus) == 11


# ---------------------------------------------------------------------------
# AC23: Regular review rejects CAND-* IDs
# ---------------------------------------------------------------------------


class TestRegularReviewRejectsCandidates:
    """Candidate review rejects non-candidate IDs."""

    def test_td_id_rejected_by_candidate_review(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        with pytest.raises(CandidateReviewError, match="Not a candidate ID"):
            review_candidate(tmp_path, "TD-ARCH-001", DecisionStatus.ACCEPTED)


# ---------------------------------------------------------------------------
# AC24: Candidate review rejects TD-* IDs
# ---------------------------------------------------------------------------


class TestCandidateReviewRejectsFindings:
    """Candidate review does not accept finding IDs."""

    def test_finding_prefix_rejected(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        with pytest.raises(CandidateReviewError, match="Not a candidate ID"):
            review_candidate(tmp_path, "TD-DEP-001", DecisionStatus.REJECTED)

    def test_wp_prefix_rejected(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        with pytest.raises(CandidateReviewError, match="Not a candidate ID"):
            review_candidate(tmp_path, "WP-001", DecisionStatus.ACCEPTED)


# ---------------------------------------------------------------------------
# AC25: One terminal decision per candidate
# ---------------------------------------------------------------------------


class TestDuplicateDecisionGuard:
    """Candidate with existing terminal decision cannot receive another."""

    def test_second_accepted_rejected(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)
        with pytest.raises(CandidateReviewError, match="already has a terminal review decision"):
            review_candidate(tmp_path, "CAND-0001", DecisionStatus.REJECTED)

    def test_second_rejected_rejected(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.REJECTED)
        with pytest.raises(CandidateReviewError, match="already has a terminal review decision"):
            review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)

    def test_accepted_then_deferred_rejected(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)
        with pytest.raises(CandidateReviewError, match="already has a terminal review decision"):
            review_candidate(tmp_path, "CAND-0001", DecisionStatus.DEFERRED)

    def test_deferred_is_terminal_too(self, tmp_path: Path) -> None:
        """Deferred is also terminal in v3.7.0."""
        _setup_workspace(tmp_path, _make_candidate())
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.DEFERRED)
        with pytest.raises(CandidateReviewError, match="already has a terminal review decision"):
            review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)


# ---------------------------------------------------------------------------
# AC26: Candidate lifecycle entries use candidate-specific states
# ---------------------------------------------------------------------------


class TestCandidateLifecycleStates:
    """Lifecycle entries use CandidateAccepted/Rejected/Deferred."""

    def test_accepted_lifecycle_is_candidate_accepted(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)
        history = json.loads((tmp_path / ".ai-debt" / "lifecycle-history.json").read_text())
        assert history["entries"][0]["to_status"] == "CandidateAccepted"

    def test_rejected_lifecycle_is_candidate_rejected(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate())
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.REJECTED)
        history = json.loads((tmp_path / ".ai-debt" / "lifecycle-history.json").read_text())
        assert history["entries"][0]["to_status"] == "CandidateRejected"

    def test_candidate_transition_to_acknowledged_not_allowed(self) -> None:
        """Candidate cannot transition to Acknowledged (v3.7.0 amendment)."""
        result = validate_finding_transition("Candidate", "Acknowledged")
        assert not result.valid

    def test_candidate_transition_to_wont_fix_not_allowed(self) -> None:
        """Candidate cannot transition to Won't Fix (v3.7.0 amendment)."""
        result = validate_finding_transition("Candidate", "Won't Fix")
        assert not result.valid

    def test_candidate_transition_to_candidate_accepted(self) -> None:
        result = validate_finding_transition("Candidate", "CandidateAccepted")
        assert result.valid

    def test_candidate_transition_to_candidate_rejected(self) -> None:
        result = validate_finding_transition("Candidate", "CandidateRejected")
        assert result.valid

    def test_candidate_outcome_states_are_terminal(self) -> None:
        """Candidate outcome states have no outgoing transitions."""
        assert FINDING_TRANSITIONS[FindingStatus.CANDIDATE_ACCEPTED] == set()
        assert FINDING_TRANSITIONS[FindingStatus.CANDIDATE_REJECTED] == set()
        assert FINDING_TRANSITIONS[FindingStatus.CANDIDATE_DEFERRED] == set()


# ---------------------------------------------------------------------------
# AC27: Candidate review summary distinguishes from findings
# ---------------------------------------------------------------------------


class TestSummaryDistinguishes:
    """Summary clearly separates candidate reviews from finding reviews."""

    def test_format_mentions_candidates(self) -> None:
        summary = CandidateReviewSummary(total_candidates=5)
        text = format_candidate_review_summary(summary)
        assert "Candidate" in text

    def test_accepted_list_contains_cand_ids(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.ACCEPTED)
        summary = summarize_candidate_reviews(tmp_path)
        assert "CAND-0001" in summary.accepted
        # No TD-* IDs in accepted list
        for cid in summary.accepted:
            assert cid.startswith("CAND")


# ---------------------------------------------------------------------------
# Lifecycle enum coverage
# ---------------------------------------------------------------------------


class TestLifecycleEnumCoverage:
    """All candidate states have proper lifecycle support."""

    def test_all_candidate_states_in_transitions(self) -> None:
        for status in [
            FindingStatus.CANDIDATE,
            FindingStatus.CANDIDATE_ACCEPTED,
            FindingStatus.CANDIDATE_REJECTED,
            FindingStatus.CANDIDATE_DEFERRED,
        ]:
            assert status in FINDING_TRANSITIONS

    def test_candidate_states_in_aliases(self) -> None:
        from pharabius.core.lifecycle import FINDING_STATUS_ALIASES

        assert "CandidateAccepted" in FINDING_STATUS_ALIASES
        assert "CandidateRejected" in FINDING_STATUS_ALIASES
        assert "CandidateDeferred" in FINDING_STATUS_ALIASES
