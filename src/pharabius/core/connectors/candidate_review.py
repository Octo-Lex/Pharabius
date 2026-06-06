"""Candidate review decision recording (v3.7.0).

Records reviewer decisions on candidate findings. Decisions are append-only
records in the review sidecar and lifecycle history. The candidate artifact
itself is NOT mutated.

Key invariants:
- Candidate acceptance is review-level only, not debt-register promotion.
- CandidateAccepted ≠ Acknowledged. Candidates remain candidates.
- Regular review rejects CAND-* IDs. Candidate review rejects TD-* IDs.
- One terminal decision per candidate (v3.7.0).
- No auto-promotion. No DebtFinding creation. No work packages. No tickets.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pharabius.core.connectors.candidate import load_candidate_artifact
from pharabius.core.lifecycle import (
    FindingStatus,
)
from pharabius.schemas.lifecycle import LifecycleEntry, LifecycleHistory
from pharabius.schemas.review import DecisionStatus, ReviewDecision

# ---------------------------------------------------------------------------
# Decision → lifecycle outcome mapping
# ---------------------------------------------------------------------------

CANDIDATE_DECISION_OUTCOMES: dict[DecisionStatus, FindingStatus] = {
    DecisionStatus.ACCEPTED: FindingStatus.CANDIDATE_ACCEPTED,
    DecisionStatus.REJECTED: FindingStatus.CANDIDATE_REJECTED,
    DecisionStatus.RISK_ACCEPTED: FindingStatus.CANDIDATE_REJECTED,
    DecisionStatus.DUPLICATE: FindingStatus.CANDIDATE_REJECTED,
    DecisionStatus.ALREADY_FIXED: FindingStatus.CANDIDATE_REJECTED,
    DecisionStatus.DEFERRED: FindingStatus.CANDIDATE_DEFERRED,
}

# Decisions that are terminal (one per candidate in v3.7.0)
TERMINAL_DECISIONS: set[DecisionStatus] = {
    DecisionStatus.ACCEPTED,
    DecisionStatus.REJECTED,
    DecisionStatus.RISK_ACCEPTED,
    DecisionStatus.DUPLICATE,
    DecisionStatus.ALREADY_FIXED,
    DecisionStatus.DEFERRED,
}

# Decisions that are NOT valid for candidates
INVALID_CANDIDATE_DECISIONS: set[DecisionStatus] = {
    DecisionStatus.NEEDS_INVESTIGATION,  # Candidates ARE pre-investigation
}

# Candidate ID prefix
CANDIDATE_ID_PREFIX = "CAND"

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _review_dir(root: Path) -> Path:
    return root / ".ai-debt" / "review"


def _decisions_path(root: Path) -> Path:
    return _review_dir(root) / "decisions.json"


def _lifecycle_path(root: Path) -> Path:
    return root / ".ai-debt" / "lifecycle-history.json"


# ---------------------------------------------------------------------------
# Load / save helpers
# ---------------------------------------------------------------------------


def _load_review_decisions(root: Path) -> list[dict[str, Any]]:
    """Load existing review decisions as raw dicts."""
    path = _decisions_path(root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("decisions", [])
    except (json.JSONDecodeError, OSError):
        return []


def _save_review_decisions(root: Path, decisions_raw: list[dict[str, Any]]) -> None:
    """Save review decisions sidecar."""
    path = _decisions_path(root)
    _review_dir(root).mkdir(parents=True, exist_ok=True)

    # Preserve the sidecar structure
    existing: dict[str, Any] = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}

    existing["decisions"] = decisions_raw
    if "schema_version" not in existing:
        existing["schema_version"] = "1.0"

    path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")


def _load_lifecycle_history(root: Path) -> LifecycleHistory:
    """Load lifecycle history. Returns empty if missing."""
    path = _lifecycle_path(root)
    if not path.exists():
        return LifecycleHistory()
    try:
        return LifecycleHistory.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return LifecycleHistory()


def _save_lifecycle_history(root: Path, history: LifecycleHistory) -> None:
    """Save lifecycle history."""
    path = _lifecycle_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        history.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class CandidateReviewError(Exception):
    """Error during candidate review."""


def _validate_candidate_id(candidate_id: str) -> None:
    """Ensure ID is a candidate ID (CAND-XXXX)."""
    if not candidate_id.startswith(CANDIDATE_ID_PREFIX):
        msg = (
            f"Not a candidate ID: {candidate_id!r}. "
            "Candidate review only accepts CAND-* IDs. "
            "Use regular review for TD-* findings."
        )
        raise CandidateReviewError(msg)


def _validate_decision_for_candidate(decision: DecisionStatus) -> None:
    """Ensure decision is valid for candidates."""
    if decision in INVALID_CANDIDATE_DECISIONS:
        msg = (
            f"Decision {decision.value!r} is not valid for candidates. "
            "Candidates are pre-investigation artifacts. "
            "Accept or reject IS the investigation outcome."
        )
        raise CandidateReviewError(msg)

    if decision not in CANDIDATE_DECISION_OUTCOMES:
        msg = f"Unknown decision status: {decision.value!r}"
        raise CandidateReviewError(msg)


def _check_no_existing_terminal(
    candidate_id: str,
    existing_decisions: list[dict[str, Any]],
) -> None:
    """Ensure candidate has no existing terminal decision (v3.7.0)."""
    for d in existing_decisions:
        if d.get("finding_id") == candidate_id:
            status_str = d.get("status", "")
            try:
                ds = DecisionStatus(status_str)
            except ValueError:
                continue
            if ds in TERMINAL_DECISIONS:
                msg = (
                    f"Candidate {candidate_id} already has a terminal review "
                    f"decision ({status_str!r}). "
                    "Supersession is not supported in v3.7.0."
                )
                raise CandidateReviewError(msg)


# ---------------------------------------------------------------------------
# Core: review_candidate
# ---------------------------------------------------------------------------


def review_candidate(
    root: Path,
    candidate_id: str,
    decision: DecisionStatus,
    reviewer: str = "",
    rationale: str = "",
) -> ReviewDecision:
    """Record a review decision for a candidate finding.

    Appends to review sidecar and lifecycle history.
    Does NOT mutate candidate-findings.json or debt-register.json.

    Raises CandidateReviewError for:
    - Non-candidate IDs (TD-*)
    - Invalid candidate decisions (needs-investigation)
    - Duplicate terminal decisions
    - Unknown candidate IDs
    """
    # Validate inputs
    _validate_candidate_id(candidate_id)
    _validate_decision_for_candidate(decision)

    # Verify candidate exists
    artifact = load_candidate_artifact(root)
    candidate_ids = {c.id for c in artifact.candidates}
    if candidate_id not in candidate_ids:
        msg = (
            f"Unknown candidate ID: {candidate_id!r}. "
            f"Known candidates: {sorted(candidate_ids) or 'none'}"
        )
        raise CandidateReviewError(msg)

    # Check for existing terminal decision
    existing_decisions = _load_review_decisions(root)
    _check_no_existing_terminal(candidate_id, existing_decisions)

    # Create review decision
    review_decision = ReviewDecision(
        finding_id=candidate_id,
        status=decision,
        reviewed_at=datetime.now(UTC),
        reviewer=reviewer,
        rationale=rationale,
    )

    # Append to review sidecar
    decision_dict = json.loads(review_decision.model_dump_json())
    existing_decisions.append(decision_dict)
    _save_review_decisions(root, existing_decisions)

    # Append lifecycle entry
    lifecycle_outcome = CANDIDATE_DECISION_OUTCOMES[decision]
    history = _load_lifecycle_history(root)
    entry = LifecycleEntry(
        artifact_type="candidate",
        artifact_id=candidate_id,
        from_status="Candidate",
        to_status=lifecycle_outcome.value,
        actor=reviewer or "operator",
        rationale=rationale or f"Review decision: {decision.value}",
    )
    history.append_entry(entry)
    _save_lifecycle_history(root, history)

    return review_decision


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


class CandidateReviewSummary:
    """Summary of candidate review decisions."""

    def __init__(
        self,
        total_candidates: int = 0,
        pending: list[str] | None = None,
        accepted: list[str] | None = None,
        rejected: list[str] | None = None,
        deferred: list[str] | None = None,
    ) -> None:
        self.total_candidates = total_candidates
        self.pending = pending or []
        self.accepted = accepted or []
        self.rejected = rejected or []
        self.deferred = deferred or []

    @property
    def reviewed_count(self) -> int:
        return len(self.accepted) + len(self.rejected) + len(self.deferred)

    @property
    def pending_count(self) -> int:
        return len(self.pending)


def summarize_candidate_reviews(root: Path) -> CandidateReviewSummary:
    """Summarize candidate review status.

    Distinguishes accepted candidates from accepted findings.
    """
    artifact = load_candidate_artifact(root)
    if not artifact.candidates:
        return CandidateReviewSummary()

    candidate_ids = {c.id for c in artifact.candidates}
    decisions = _load_review_decisions(root)

    # Map candidate decisions
    accepted: list[str] = []
    rejected: list[str] = []
    deferred: list[str] = []
    decided_ids: set[str] = set()

    for d in decisions:
        fid = d.get("finding_id", "")
        if fid not in candidate_ids:
            continue
        status_str = d.get("status", "")
        if fid in decided_ids:
            continue  # First decision wins
        decided_ids.add(fid)

        if status_str == "accepted":
            accepted.append(fid)
        elif status_str in ("rejected", "risk-accepted", "duplicate", "already-fixed"):
            rejected.append(fid)
        elif status_str == "deferred":
            deferred.append(fid)

    pending = sorted(candidate_ids - decided_ids)

    return CandidateReviewSummary(
        total_candidates=len(candidate_ids),
        pending=pending,
        accepted=sorted(accepted),
        rejected=sorted(rejected),
        deferred=sorted(deferred),
    )


def format_candidate_review_summary(summary: CandidateReviewSummary) -> str:
    """Format candidate review summary for console output."""
    lines: list[str] = []
    lines.append("Candidate Review Summary")
    lines.append("")
    lines.append(f"Total candidates:       {summary.total_candidates}")
    lines.append(f"Reviewed:               {summary.reviewed_count}")
    lines.append(f"Pending review:         {summary.pending_count}")
    lines.append("")
    lines.append(
        "  CandidateAccepted:    "
        f"{len(summary.accepted)} "
        "(review-level only, not debt-register promotion)"
    )
    lines.append(f"  CandidateRejected:    {len(summary.rejected)}")
    lines.append(f"  CandidateDeferred:    {len(summary.deferred)}")

    if summary.pending:
        lines.append("")
        lines.append("Pending candidates:")
        for cid in summary.pending:
            lines.append(f"  {cid}")

    return "\n".join(lines)
