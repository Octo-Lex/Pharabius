"""Ticket draft schema models for repository-local ticket draft export.

Ticket drafts are sidecar artifacts generated from canonical Pharabius
artifacts (work packages, debt register, review sidecar). They are
intended for human review before creating real tickets in external systems.

Boundary:
- No external tracker integration
- No network calls
- No autonomous ticket creation
- No mutation of debt register, work packages, or review sidecar
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TicketDraftSourceArtifacts(BaseModel):
    """Paths to canonical source artifacts used for ticket generation."""

    debt_register: str
    work_packages_dir: str
    review_sidecar: str | None = None


class TicketDraftSummary(BaseModel):
    """Aggregate counts for the ticket draft index."""

    total_drafts: int = 0
    included_drafts: int = 0
    excluded_by_review: int = 0
    deferred: int = 0
    false_positive: int = 0
    unreviewed: int = 0


class TicketDraft(BaseModel):
    """A single repository-local ticket draft."""

    ticket_id: str
    title: str
    source_type: Literal["work_package", "finding"]
    source_id: str
    artifact_path: str
    linked_debt_items: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    priority: str | None = None
    risk_score: int | None = None
    review_decision: str = "not_reviewed"
    status: Literal["draft", "excluded"] = "draft"
    labels: list[str] = Field(default_factory=list)
    external_system: None = None
    external_id: None = None
    content_hash: str | None = None
    body_markdown: str = ""
    review_summary: dict[str, int] = Field(default_factory=dict)
    excluded_linked_debt_items: list[str] = Field(default_factory=list)
    completeness: TicketDraftCompleteness | None = None


class TicketDraftIndex(BaseModel):
    """Index of all generated ticket drafts for a repository."""

    schema_version: str = "1.0"
    tool_version: str
    generated_at: str
    repository: str | None = None
    commit: str | None = None
    branch: str | None = None
    source_artifacts: TicketDraftSourceArtifacts
    summary: TicketDraftSummary = Field(default_factory=TicketDraftSummary)
    drafts: list[TicketDraft] = Field(default_factory=list)
    validation_issues: list[TicketDraftValidationIssue] = Field(default_factory=list)


class TicketDraftValidationIssue(BaseModel):
    """A validation issue encountered during ticket draft generation."""

    source_path: str
    work_package_id: str | None = None
    code: str
    severity: str = "warning"
    message: str


class TicketDraftCompleteness(BaseModel):
    """Completeness assessment for a generated ticket draft."""

    status: str  # "complete", "partial", "needs_review"
    missing_fields: list[str] = Field(default_factory=list)
    weak_fields: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
