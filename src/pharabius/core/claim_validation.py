"""Claim validation — structured error/warning validation for claims registers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from pharabius.schemas.claims import (
    ClaimCompleteness,
    ClaimRegisterCompleteness,
    OperationalClaim,
    OperationalClaimsRegister,
)


class ClaimValidationIssue(BaseModel):
    """A single validation issue for a claim or register."""

    model_config = {"extra": "forbid"}

    severity: Literal["error", "warning"]
    code: str
    message: str
    claim_id: str | None = None
    referenced_id: str | None = None
    field: str | None = None


class ClaimValidationResult(BaseModel):
    """Result of validating a claims register."""

    model_config = {"extra": "forbid"}

    valid: bool = True
    errors: list[ClaimValidationIssue] = Field(default_factory=list)
    warnings: list[ClaimValidationIssue] = Field(default_factory=list)


def validate_claim(
    claim: OperationalClaim,
    known_finding_ids: set[str] | None = None,
    known_evidence_ids: set[str] | None = None,
    known_work_package_ids: set[str] | None = None,
) -> ClaimValidationResult:
    """Validate a single operational claim."""
    errors: list[ClaimValidationIssue] = []
    warnings: list[ClaimValidationIssue] = []

    # Confirmed without evidence
    if claim.status == "confirmed" and not claim.evidence_ids:
        errors.append(
            ClaimValidationIssue(
                severity="error",
                code="confirmed_claim_missing_evidence",
                message="Confirmed claims must include at least one evidence ID.",
                claim_id=claim.claim_id,
                field="evidence_ids",
            )
        )

    # Gap without question
    if claim.status == "gap" and not claim.validation_question:
        errors.append(
            ClaimValidationIssue(
                severity="error",
                code="gap_claim_missing_question",
                message="Gap claims must have a validation_question.",
                claim_id=claim.claim_id,
                field="validation_question",
            )
        )

    # Human validation without question
    if claim.requires_human_validation and not claim.validation_question:
        errors.append(
            ClaimValidationIssue(
                severity="error",
                code="human_validation_missing_question",
                message="requires_human_validation=True requires a validation_question.",
                claim_id=claim.claim_id,
                field="validation_question",
            )
        )

    # Empty statement
    if not claim.statement.strip():
        errors.append(
            ClaimValidationIssue(
                severity="error",
                code="empty_statement",
                message="Claim statement must not be empty.",
                claim_id=claim.claim_id,
                field="statement",
            )
        )

    # Cross-reference warnings
    if known_finding_ids is not None:
        for fid in claim.linked_findings:
            if fid not in known_finding_ids:
                warnings.append(
                    ClaimValidationIssue(
                        severity="warning",
                        code="unknown_finding_reference",
                        message=f"Finding {fid} not found in debt register.",
                        claim_id=claim.claim_id,
                        referenced_id=fid,
                        field="linked_findings",
                    )
                )

    if known_evidence_ids is not None:
        for eid in claim.evidence_ids:
            if eid not in known_evidence_ids:
                warnings.append(
                    ClaimValidationIssue(
                        severity="warning",
                        code="unknown_evidence_reference",
                        message=f"Evidence {eid} not found in evidence store.",
                        claim_id=claim.claim_id,
                        referenced_id=eid,
                        field="evidence_ids",
                    )
                )

    if known_work_package_ids is not None:
        for wpid in claim.linked_work_packages:
            if wpid not in known_work_package_ids:
                warnings.append(
                    ClaimValidationIssue(
                        severity="warning",
                        code="unknown_work_package_reference",
                        message=f"Work package {wpid} not found.",
                        claim_id=claim.claim_id,
                        referenced_id=wpid,
                        field="linked_work_packages",
                    )
                )

    # Inferred without limitations
    if claim.status == "inferred" and not claim.limitations:
        warnings.append(
            ClaimValidationIssue(
                severity="warning",
                code="inferred_claim_no_limitations",
                message="Inferred claims should document limitations or basis.",
                claim_id=claim.claim_id,
                field="limitations",
            )
        )

    valid = len(errors) == 0
    return ClaimValidationResult(valid=valid, errors=errors, warnings=warnings)


def validate_claims_register(
    register: OperationalClaimsRegister,
    known_finding_ids: set[str] | None = None,
    known_evidence_ids: set[str] | None = None,
    known_work_package_ids: set[str] | None = None,
) -> ClaimValidationResult:
    """Validate an entire claims register."""
    all_errors: list[ClaimValidationIssue] = []
    all_warnings: list[ClaimValidationIssue] = []

    # Duplicate claim IDs
    seen: set[str] = set()
    for claim in register.claims:
        if claim.claim_id in seen:
            all_errors.append(
                ClaimValidationIssue(
                    severity="error",
                    code="duplicate_claim_id",
                    message=f"Duplicate claim_id: {claim.claim_id}",
                    claim_id=claim.claim_id,
                    field="claim_id",
                )
            )
        seen.add(claim.claim_id)

    # Per-claim validation
    for claim in register.claims:
        result = validate_claim(
            claim, known_finding_ids, known_evidence_ids, known_work_package_ids
        )
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)

    # High-priority finding with only inferred/gap claims
    if known_finding_ids is not None:
        finding_best_status: dict[str, str] = {}
        for claim in register.claims:
            for fid in claim.linked_findings:
                if claim.status == "confirmed":
                    finding_best_status[fid] = "confirmed"
                elif fid not in finding_best_status or finding_best_status[fid] != "confirmed":
                    finding_best_status[fid] = claim.status

    valid = len(all_errors) == 0
    return ClaimValidationResult(valid=valid, errors=all_errors, warnings=all_warnings)


def assess_claim_completeness(claim: OperationalClaim) -> ClaimCompleteness:
    """Assess a single claim's completeness."""
    evidence_linked = bool(claim.evidence_ids)
    finding_linked = bool(claim.linked_findings)
    work_package_linked = bool(claim.linked_work_packages)
    has_question = bool(claim.validation_question)
    is_gap = claim.status == "gap"
    is_blocking_gap = is_gap  # Gap claims represent missing evidence

    warnings: list[str] = []

    if claim.status == "confirmed" and evidence_linked and finding_linked:
        status = "complete"
    elif claim.status == "inferred" and evidence_linked:
        status = "partial"
        if not claim.limitations:
            warnings.append("Inferred claim lacks documented limitations.")
    elif is_gap:
        status = "needs_review"
        if has_question and work_package_linked:
            warnings.append("Work package should not proceed until validation is complete.")
    elif not evidence_linked:
        status = "needs_review"
    else:
        status = "partial"

    return ClaimCompleteness(
        claim_id=claim.claim_id,
        status=status,  # type: ignore[arg-type]
        evidence_linked=evidence_linked,
        finding_linked=finding_linked,
        work_package_linked=work_package_linked,
        has_validation_question=has_question,
        blocking_gap=is_blocking_gap,
        warnings=warnings,
    )


def assess_register_completeness(
    register: OperationalClaimsRegister,
) -> ClaimRegisterCompleteness:
    """Assess completeness for an entire claims register."""
    items: list[ClaimCompleteness] = []
    warnings: list[str] = []

    for claim in register.claims:
        items.append(assess_claim_completeness(claim))

    complete = sum(1 for i in items if i.status == "complete")
    partial = sum(1 for i in items if i.status == "partial")
    needs_review = sum(1 for i in items if i.status == "needs_review")

    # Register-level warnings
    if needs_review > 0 and not warnings:
        warnings.append(f"{needs_review} claim(s) need human review before implementation.")

    return ClaimRegisterCompleteness(
        total_claims=len(items),
        complete=complete,
        partial=partial,
        needs_review=needs_review,
        claims=items,
        warnings=warnings,
    )
