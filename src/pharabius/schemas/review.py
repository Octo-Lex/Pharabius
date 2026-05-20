"""Review decision sidecar schemas.

Non-canonical PET workflow state. Review decisions never mutate
canonical artifacts (debt-register.json, evidence.json, etc.).
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DecisionStatus(enum.StrEnum):
    """Allowed review decision statuses."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    NEEDS_INVESTIGATION = "needs-investigation"
    DUPLICATE = "duplicate"
    ALREADY_FIXED = "already-fixed"
    RISK_ACCEPTED = "risk-accepted"


_VALID_STATUSES = {s.value for s in DecisionStatus}


class ReviewDecision(BaseModel):
    """A single review decision for a finding.

    Required fields: finding_id, status, reviewed_at.
    All other fields are optional free-text.
    """

    model_config = {"extra": "forbid"}

    finding_id: str
    status: DecisionStatus
    reviewed_at: datetime
    reviewer: str = ""
    rationale: str = ""
    ticket_url: str = ""
    owner_area: str = ""
    target_release: str = ""
    notes: str = ""

    @field_validator("finding_id")
    @classmethod
    def _finding_id_non_empty(cls, v: str) -> str:
        if not v.strip():
            msg = "finding_id must not be empty"
            raise ValueError(msg)
        return v


class ReviewDecisions(BaseModel):
    """Top-level review decision sidecar."""

    model_config = {"extra": "ignore"}

    schema_version: str = "1.0"
    generated_by: str = "pharabius"
    repository: str = ""
    branch: str = ""
    commit: str = ""
    decisions: list[ReviewDecision] = Field(default_factory=list)


class ValidationNotice(BaseModel):
    """A single validation notice (warning or error)."""

    level: str  # "warning" or "error"
    finding_id: str
    message: str


class ReviewValidationResult(BaseModel):
    """Result of validating review decisions against debt-register."""

    valid: bool
    total_decisions: int = 0
    notices: list[ValidationNotice] = Field(default_factory=list)
    status_counts: dict[str, int] = Field(default_factory=dict)
    unknown_finding_ids: list[str] = Field(default_factory=list)
    duplicate_finding_ids: list[str] = Field(default_factory=list)
    stale_finding_ids: list[str] = Field(default_factory=list)
    undecided_finding_ids: list[str] = Field(default_factory=list)


class ReviewSummary(BaseModel):
    """Summary of review decisions for display."""

    total_findings: int = 0
    decisions_recorded: int = 0
    undecided_count: int = 0
    status_counts: dict[str, int] = Field(default_factory=dict)
    decided_findings: list[dict[str, Any]] = Field(default_factory=list)
    undecided_findings: list[str] = Field(default_factory=list)
    stale_decisions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
