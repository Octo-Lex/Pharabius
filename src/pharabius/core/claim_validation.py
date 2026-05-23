"""Claim validation — structured error/warning validation for claims registers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from pharabius.schemas.claims import OperationalClaim, OperationalClaimsRegister


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
