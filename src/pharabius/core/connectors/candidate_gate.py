"""Candidate promotion gate (v3.9.0).

Defines eligibility rules for promoting a candidate finding to an accepted
DebtFinding. This module is GATE-ONLY — it checks eligibility but never
writes to debt-register.json or creates any artifact.

Key invariants:
- No writing to debt-register.json
- No creating accepted DebtFinding objects
- No work package generation
- No ticket creation
- No automatic lifecycle transitions
- No mutation of any artifact

The gate answers: "Is this candidate eligible for promotion?"
It does NOT perform the promotion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from pharabius.core.connectors.candidate import load_candidate_artifact
from pharabius.core.connectors.candidate_review import (
    _load_review_decisions,
)
from pharabius.schemas.candidate import CandidateFinding

# ---------------------------------------------------------------------------
# Eligibility check types
# ---------------------------------------------------------------------------


class GateCheck(StrEnum):
    """Individual gate checks for candidate promotion eligibility."""

    CANDIDATE_EXISTS = "candidate_exists"
    HAS_ACCEPTED_DECISION = "has_accepted_decision"
    HAS_REVIEWER = "has_reviewer"
    HAS_RATIONALE = "has_rationale"
    HAS_EVIDENCE_IDS = "has_evidence_ids"
    HAS_PROVENANCE = "has_provenance"
    HAS_TITLE = "has_title"
    HAS_CATEGORY = "has_category"
    HAS_DESCRIPTION = "has_description"


class GateStatus(StrEnum):
    """Overall gate result."""

    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    ERROR = "error"


@dataclass
class GateCheckResult:
    """Result of a single gate check."""

    check: GateCheck
    passed: bool
    reason: str = ""


@dataclass
class PromotionGateResult:
    """Result of checking candidate promotion eligibility.

    Does NOT perform promotion. Only reports eligibility.
    """

    candidate_id: str
    status: GateStatus
    checks: list[GateCheckResult] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)

    @property
    def eligible(self) -> bool:
        return self.status == GateStatus.ELIGIBLE


# ---------------------------------------------------------------------------
# Gate checks
# ---------------------------------------------------------------------------


def _check_candidate_exists(
    candidate: CandidateFinding | None,
) -> GateCheckResult:
    if candidate is None:
        return GateCheckResult(
            check=GateCheck.CANDIDATE_EXISTS,
            passed=False,
            reason="Candidate not found in candidate-findings.json",
        )
    return GateCheckResult(check=GateCheck.CANDIDATE_EXISTS, passed=True)


def _check_has_accepted_decision(
    candidate_id: str,
    decisions: list[dict],
) -> GateCheckResult:
    for d in decisions:
        if d.get("finding_id") == candidate_id:
            status = d.get("status", "")
            if status == "accepted":
                return GateCheckResult(check=GateCheck.HAS_ACCEPTED_DECISION, passed=True)
            return GateCheckResult(
                check=GateCheck.HAS_ACCEPTED_DECISION,
                passed=False,
                reason=f"Decision is '{status}', not 'accepted'",
            )
    return GateCheckResult(
        check=GateCheck.HAS_ACCEPTED_DECISION,
        passed=False,
        reason="No review decision found",
    )


def _check_has_reviewer(decisions: list[dict], candidate_id: str) -> GateCheckResult:
    for d in decisions:
        if d.get("finding_id") == candidate_id:
            reviewer = d.get("reviewer", "")
            if reviewer.strip():
                return GateCheckResult(check=GateCheck.HAS_REVIEWER, passed=True)
            return GateCheckResult(
                check=GateCheck.HAS_REVIEWER,
                passed=False,
                reason="Reviewer field is empty",
            )
    return GateCheckResult(
        check=GateCheck.HAS_REVIEWER,
        passed=False,
        reason="No review decision found",
    )


def _check_has_rationale(decisions: list[dict], candidate_id: str) -> GateCheckResult:
    for d in decisions:
        if d.get("finding_id") == candidate_id:
            rationale = d.get("rationale", "")
            if rationale.strip():
                return GateCheckResult(check=GateCheck.HAS_RATIONALE, passed=True)
            return GateCheckResult(
                check=GateCheck.HAS_RATIONALE,
                passed=False,
                reason="Rationale field is empty",
            )
    return GateCheckResult(
        check=GateCheck.HAS_RATIONALE,
        passed=False,
        reason="No review decision found",
    )


def _check_has_evidence_ids(candidate: CandidateFinding) -> GateCheckResult:
    if candidate.evidence_ids:
        return GateCheckResult(check=GateCheck.HAS_EVIDENCE_IDS, passed=True)
    return GateCheckResult(
        check=GateCheck.HAS_EVIDENCE_IDS,
        passed=False,
        reason="No evidence IDs attached",
    )


def _check_has_provenance(candidate: CandidateFinding) -> GateCheckResult:
    if candidate.provenance and candidate.provenance.connector_name:
        return GateCheckResult(check=GateCheck.HAS_PROVENANCE, passed=True)
    return GateCheckResult(
        check=GateCheck.HAS_PROVENANCE,
        passed=False,
        reason="No provenance metadata",
    )


def _check_has_title(candidate: CandidateFinding) -> GateCheckResult:
    if candidate.title.strip():
        return GateCheckResult(check=GateCheck.HAS_TITLE, passed=True)
    return GateCheckResult(
        check=GateCheck.HAS_TITLE,
        passed=False,
        reason="Title is empty",
    )


def _check_has_category(candidate: CandidateFinding) -> GateCheckResult:
    if candidate.category.strip():
        return GateCheckResult(check=GateCheck.HAS_CATEGORY, passed=True)
    return GateCheckResult(
        check=GateCheck.HAS_CATEGORY,
        passed=False,
        reason="Category is empty",
    )


def _check_has_description(candidate: CandidateFinding) -> GateCheckResult:
    if candidate.description.strip():
        return GateCheckResult(check=GateCheck.HAS_DESCRIPTION, passed=True)
    return GateCheckResult(
        check=GateCheck.HAS_DESCRIPTION,
        passed=False,
        reason="Description is empty",
    )


# ---------------------------------------------------------------------------
# Main gate function
# ---------------------------------------------------------------------------


def check_promotion_eligibility(
    root: Path,
    candidate_id: str,
) -> PromotionGateResult:
    """Check whether a candidate is eligible for promotion.

    This is a READ-ONLY operation. It does not modify any artifact.

    Returns a PromotionGateResult with:
    - status: ELIGIBLE or NOT_ELIGIBLE
    - checks: list of individual gate check results
    - blocking_reasons: reasons for any failed checks
    """
    # Load candidate
    artifact = load_candidate_artifact(root)
    candidate: CandidateFinding | None = None
    for c in artifact.candidates:
        if c.id == candidate_id:
            candidate = c
            break

    # Load decisions
    decisions = _load_review_decisions(root)

    # Run all checks
    checks: list[GateCheckResult] = []
    checks.append(_check_candidate_exists(candidate))

    if candidate is None:
        # Short-circuit: candidate doesn't exist
        blocking = [c.reason for c in checks if not c.passed]
        return PromotionGateResult(
            candidate_id=candidate_id,
            status=GateStatus.NOT_ELIGIBLE,
            checks=checks,
            blocking_reasons=blocking,
        )

    # Remaining checks
    checks.append(_check_has_accepted_decision(candidate_id, decisions))
    checks.append(_check_has_reviewer(decisions, candidate_id))
    checks.append(_check_has_rationale(decisions, candidate_id))
    checks.append(_check_has_evidence_ids(candidate))
    checks.append(_check_has_provenance(candidate))
    checks.append(_check_has_title(candidate))
    checks.append(_check_has_category(candidate))
    checks.append(_check_has_description(candidate))

    # Determine result
    blocking = [c.reason for c in checks if not c.passed]
    status = GateStatus.ELIGIBLE if not blocking else GateStatus.NOT_ELIGIBLE

    return PromotionGateResult(
        candidate_id=candidate_id,
        status=status,
        checks=checks,
        blocking_reasons=blocking,
    )


# ---------------------------------------------------------------------------
# Batch eligibility
# ---------------------------------------------------------------------------


@dataclass
class PromotionGateBatch:
    """Batch eligibility check for all candidates."""

    total_candidates: int = 0
    eligible: list[str] = field(default_factory=list)
    not_eligible: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    results: list[PromotionGateResult] = field(default_factory=list)

    @property
    def eligible_count(self) -> int:
        return len(self.eligible)

    @property
    def not_eligible_count(self) -> int:
        return len(self.not_eligible)


def check_all_promotion_eligibility(root: Path) -> PromotionGateBatch:
    """Check promotion eligibility for all candidates.

    READ-ONLY. Does not modify any artifact.
    """
    artifact = load_candidate_artifact(root)
    if not artifact.candidates:
        return PromotionGateBatch()

    batch = PromotionGateBatch(total_candidates=len(artifact.candidates))

    for c in artifact.candidates:
        result = check_promotion_eligibility(root, c.id)
        batch.results.append(result)
        if result.eligible:
            batch.eligible.append(c.id)
        elif result.status == GateStatus.ERROR:
            batch.errors.append(c.id)
        else:
            batch.not_eligible.append(c.id)

    return batch


def format_eligibility_report(result: PromotionGateResult) -> str:
    """Format a single eligibility check result for display."""
    lines: list[str] = []
    lines.append(f"Promotion Gate: {result.candidate_id}")
    lines.append(f"Status: {result.status.value}")
    lines.append("")

    for check in result.checks:
        mark = "✓" if check.passed else "✗"
        reason = f" — {check.reason}" if check.reason else ""
        lines.append(f"  {mark} {check.check.value}{reason}")

    if result.blocking_reasons:
        lines.append("")
        lines.append("Blocking reasons:")
        for r in result.blocking_reasons:
            lines.append(f"  - {r}")

    return "\n".join(lines)


def format_batch_eligibility_report(batch: PromotionGateBatch) -> str:
    """Format batch eligibility report for display."""
    lines: list[str] = []
    lines.append("Candidate Promotion Eligibility")
    lines.append("")
    lines.append(f"Total candidates:  {batch.total_candidates}")
    lines.append(f"Eligible:          {batch.eligible_count}")
    lines.append(f"Not eligible:      {batch.not_eligible_count}")

    if batch.eligible:
        lines.append("")
        lines.append("Eligible candidates:")
        for cid in batch.eligible:
            lines.append(f"  {cid}")

    if batch.not_eligible:
        lines.append("")
        lines.append("Not eligible:")
        for cid in batch.not_eligible:
            lines.append(f"  {cid}")

    lines.append("")
    lines.append("> Eligibility is gate-only. No candidates are promoted by this check.")

    return "\n".join(lines)
