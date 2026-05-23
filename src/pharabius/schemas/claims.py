"""Operational claim schemas for Pharabius.

Defines first-class operational claims derived from evidence, findings,
and work packages. Claims are specification/handoff artifacts — they do
not modify source code or canonical Pharabius outputs.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

CLAIM_TYPES = (
    "behavior",
    "architecture",
    "dependency",
    "test",
    "security",
    "compliance",
    "operational",
    "business_rule",
    "data",
    "documentation",
)

CLAIM_STATUSES = ("confirmed", "inferred", "gap")

CLAIM_CONFIDENCES = ("High", "Medium", "Low")

CLAIM_SOURCES = (
    "evidence",
    "finding",
    "work_package",
    "report",
    "derived",
)


class OperationalClaim(BaseModel):
    """A single operational claim about the repository."""

    model_config = {"extra": "forbid"}

    claim_id: str
    claim_type: Literal[
        "behavior",
        "architecture",
        "dependency",
        "test",
        "security",
        "compliance",
        "operational",
        "business_rule",
        "data",
        "documentation",
    ]
    statement: str
    status: Literal["confirmed", "inferred", "gap"]
    confidence: Literal["High", "Medium", "Low"]
    evidence_ids: list[str] = Field(default_factory=list)
    linked_findings: list[str] = Field(default_factory=list)
    linked_work_packages: list[str] = Field(default_factory=list)
    requires_human_validation: bool = False
    validation_question: str | None = None
    source: Literal[
        "evidence",
        "finding",
        "work_package",
        "report",
        "derived",
    ]
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_claim_rules(self) -> OperationalClaim:
        # Confirmed claims must have evidence IDs
        if self.status == "confirmed" and not self.evidence_ids:
            msg = "Confirmed claims must have at least one evidence ID"
            raise ValueError(msg)
        # Gap claims must have a validation question
        if self.status == "gap" and not self.validation_question:
            msg = "Gap claims must have a validation_question"
            raise ValueError(msg)
        # Human validation requires a question
        if self.requires_human_validation and not self.validation_question:
            msg = "requires_human_validation=True requires a validation_question"
            raise ValueError(msg)
        # Statement must not be empty
        if not self.statement.strip():
            msg = "Claim statement must not be empty"
            raise ValueError(msg)
        return self


class GapItem(BaseModel):
    """A single gap item in the gap registry."""

    model_config = {"extra": "forbid"}

    gap_id: str
    claim_id: str | None = None
    linked_findings: list[str] = Field(default_factory=list)
    linked_work_packages: list[str] = Field(default_factory=list)
    severity: Literal["blocking", "non_blocking"]
    question: str
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    recommended_owner: str | None = None


class QuestionItem(BaseModel):
    """A single question item in the question registry."""

    model_config = {"extra": "forbid"}

    question_id: str
    claim_id: str | None = None
    linked_findings: list[str] = Field(default_factory=list)
    question: str
    category: Literal[
        "product_engineering",
        "architecture",
        "security_compliance",
        "testing_verification",
        "general",
    ] = "general"


class ClaimCompleteness(BaseModel):
    """Per-claim completeness assessment."""

    model_config = {"extra": "forbid"}

    claim_id: str
    status: Literal["complete", "partial", "needs_review"]
    evidence_linked: bool = False
    finding_linked: bool = False
    work_package_linked: bool = False
    has_validation_question: bool = False
    blocking_gap: bool = False
    warnings: list[str] = Field(default_factory=list)


class ClaimRegisterCompleteness(BaseModel):
    """Register-level completeness summary."""

    model_config = {"extra": "forbid"}

    total_claims: int = 0
    complete: int = 0
    partial: int = 0
    needs_review: int = 0
    claims: list[ClaimCompleteness] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class OperationalClaimsRegisterSummary(BaseModel):
    """Summary counts for the claims register."""

    model_config = {"extra": "forbid"}

    total_claims: int = 0
    confirmed: int = 0
    inferred: int = 0
    gap: int = 0
    high_confidence: int = 0
    medium_confidence: int = 0
    low_confidence: int = 0
    requiring_validation: int = 0


class OperationalClaimsRegister(BaseModel):
    """Register of operational claims for a repository."""

    model_config = {"extra": "forbid"}

    schema_version: str = "1.0"
    generated_at: str = ""
    project_name: str | None = None
    repository: str | None = None
    branch: str | None = None
    commit: str | None = None
    claims: list[OperationalClaim] = Field(default_factory=list)
    summary: OperationalClaimsRegisterSummary = Field(
        default_factory=OperationalClaimsRegisterSummary
    )
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_register(self) -> OperationalClaimsRegister:
        seen: set[str] = set()
        for claim in self.claims:
            if claim.claim_id in seen:
                msg = f"Duplicate claim_id: {claim.claim_id}"
                raise ValueError(msg)
            seen.add(claim.claim_id)
        return self
