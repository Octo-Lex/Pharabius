"""Candidate promotion execution (v3.10.0).

Promotes an eligible candidate finding to an accepted DebtFinding.
Requires gate pass from v3.9.0. Appends to existing debt-register.json.

Key invariants:
- Promotion must be explicit — no auto-promotion
- Promotion must require gate pass
- Promotion must preserve candidate lineage in risk_breakdown
- Promotion must not delete or rewrite candidate-findings.json
- Promotion must not auto-generate work packages, tickets, or remediation
- Promotion must not rewrite historical review decisions
- One promotion per candidate — duplicate guard
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pharabius.core.connectors.candidate import load_candidate_artifact
from pharabius.core.connectors.candidate_gate import (
    check_promotion_eligibility,
)
from pharabius.core.connectors.candidate_review import (
    _load_lifecycle_history,
    _load_review_decisions,
    _save_lifecycle_history,
)
from pharabius.schemas.candidate import CandidateFinding
from pharabius.schemas.finding import DebtFinding, DebtRegister, DebtRegisterSummary
from pharabius.schemas.lifecycle import LifecycleEntry


class PromotionError(Exception):
    """Error during candidate promotion."""


# ---------------------------------------------------------------------------
# Lineage metadata keys
# ---------------------------------------------------------------------------

LINEAGE_KEY = "_promotion_lineage"


def _build_lineage_metadata(
    candidate: CandidateFinding,
    decision: dict[str, Any],
) -> dict[str, Any]:
    """Build lineage metadata for promoted finding."""
    return {
        "source": "candidate_promotion",
        "candidate_id": candidate.id,
        "connector_name": candidate.provenance.connector_name,
        "source_format": candidate.provenance.source_format,
        "original_evidence_ids": candidate.provenance.evidence_ids,
        "promoted_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reviewer": decision.get("reviewer", ""),
        "review_rationale": decision.get("rationale", ""),
        "reviewed_at": decision.get("reviewed_at", ""),
    }


# ---------------------------------------------------------------------------
# Finding ID generation
# ---------------------------------------------------------------------------


def _next_finding_id(register: DebtRegister, category: str) -> str:
    """Generate the next finding ID for a given category."""
    existing_ids = {f.id for f in register.findings}
    counter = 0
    while True:
        counter += 1
        candidate_id = f"{category}-{counter:03d}"
        if candidate_id not in existing_ids:
            return candidate_id


# ---------------------------------------------------------------------------
# Load / save register (append-safe)
# ---------------------------------------------------------------------------


def _load_debt_register(root: Path) -> DebtRegister:
    """Load existing debt-register.json. Returns empty if missing."""
    path = root / ".ai-debt" / "debt-register.json"
    if not path.exists():
        return DebtRegister()
    try:
        return DebtRegister.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return DebtRegister()


def _resummary(register: DebtRegister) -> None:
    """Recalculate register summary from findings list."""
    from collections import Counter

    findings = register.findings
    severity_counts = Counter(f.severity.lower() for f in findings)
    category_counts = Counter(f.category for f in findings)
    tech_debt = sum(1 for f in findings if f.issue_type != "advisory")
    advisory = sum(1 for f in findings if f.issue_type == "advisory")

    register.summary = DebtRegisterSummary(
        total_findings=len(findings),
        technical_debt_count=tech_debt,
        advisory_count=advisory,
        critical=severity_counts["critical"],
        high=severity_counts["high"],
        medium=severity_counts["medium"],
        low=severity_counts["low"],
        top_categories=[c for c, _ in category_counts.most_common(5)],
    )


def _save_debt_register(root: Path, register: DebtRegister) -> Path:
    """Write debt-register.json."""
    path = root / ".ai-debt" / "debt-register.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        register.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# Duplicate promotion guard
# ---------------------------------------------------------------------------


def _check_not_already_promoted(
    register: DebtRegister,
    candidate_id: str,
) -> None:
    """Guard against duplicate promotion."""
    for f in register.findings:
        lineage = f.risk_breakdown.get(LINEAGE_KEY, {})
        if lineage.get("candidate_id") == candidate_id:
            msg = (
                f"Candidate {candidate_id} already promoted to "
                f"finding {f.id}. Each candidate may only be promoted once."
            )
            raise PromotionError(msg)


# ---------------------------------------------------------------------------
# Main: promote_candidate
# ---------------------------------------------------------------------------


def promote_candidate(
    root: Path,
    candidate_id: str,
) -> DebtFinding:
    """Promote an eligible candidate to an accepted DebtFinding.

    Steps:
    1. Check promotion gate (v3.9.0) — must pass all 9 checks
    2. Verify not already promoted
    3. Convert candidate to DebtFinding with lineage
    4. Append to existing debt-register.json
    5. Append lifecycle entry
    6. Return the new DebtFinding

    Raises PromotionError for:
    - Gate check failures
    - Duplicate promotions
    - Missing artifacts

    Does NOT:
    - Delete or rewrite candidate-findings.json
    - Auto-generate work packages
    - Create tickets
    - Modify historical review decisions
    """
    # Step 1: Gate check
    gate_result = check_promotion_eligibility(root, candidate_id)
    if not gate_result.eligible:
        reasons = "; ".join(gate_result.blocking_reasons)
        msg = (
            f"Promotion gate failed for {candidate_id}: {reasons}. "
            "Resolve blocking issues before promoting."
        )
        raise PromotionError(msg)

    # Step 2: Load candidate
    artifact = load_candidate_artifact(root)
    candidate: CandidateFinding | None = None
    for c in artifact.candidates:
        if c.id == candidate_id:
            candidate = c
            break

    if candidate is None:
        msg = f"Candidate {candidate_id} not found."
        raise PromotionError(msg)

    # Step 3: Load review decision
    decisions = _load_review_decisions(root)
    decision: dict[str, Any] = {}
    for d in decisions:
        if d.get("finding_id") == candidate_id:
            decision = d
            break

    # Step 4: Load existing register and check duplicate
    register = _load_debt_register(root)
    _check_not_already_promoted(register, candidate_id)

    # Step 5: Build DebtFinding
    lineage = _build_lineage_metadata(candidate, decision)
    finding_id = _next_finding_id(register, candidate.category)

    # Severity from candidate (informational, not scored)
    severity = candidate.severity if candidate.severity != "Unscored" else "Low"

    new_finding = DebtFinding(
        id=finding_id,
        category=candidate.category,
        issue_type="technical_debt",
        title=candidate.title,
        description=candidate.description,
        severity=severity,
        confidence=candidate.confidence,
        status="Detected",
        locations=candidate.locations,
        evidence_ids=candidate.evidence_ids,
        technical_impact=(
            f"Identified by {candidate.provenance.connector_name} scanner. "
            "Impact assessment from external evidence."
        ),
        business_impact=(
            "Promoted from candidate finding. "
            "Validate business impact with Product Engineering Team."
        ),
        risk_score=25,  # Default moderate risk for promoted findings
        priority="Medium",
        risk_breakdown={
            LINEAGE_KEY: lineage,
            "source": "candidate_promotion",
            "promotion_candidate_id": candidate_id,
        },
        recommended_action=(
            f"Review and address finding from {candidate.provenance.connector_name}. "
            "External evidence should be validated before remediation."
        ),
        verification_recommendations=[
            "Verify the external finding still applies to current codebase.",
            "Confirm remediation addresses the actual issue.",
        ],
    )

    # Step 6: Append to register
    register.findings.append(new_finding)
    _resummary(register)
    _save_debt_register(root, register)

    # Step 7: Append lifecycle entry
    history = _load_lifecycle_history(root)
    entry = LifecycleEntry(
        artifact_type="candidate_promotion",
        artifact_id=candidate_id,
        from_status="CandidateAccepted",
        to_status="Detected",
        actor=decision.get("reviewer", "operator"),
        rationale=f"Promoted to accepted finding {finding_id}",
        metadata={"promoted_finding_id": finding_id},
    )
    history.append_entry(entry)
    _save_lifecycle_history(root, history)

    return new_finding
