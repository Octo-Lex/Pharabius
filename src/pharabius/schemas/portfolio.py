"""Portfolio summary schemas for Pharabius.

Defines the artifact contract for repository-local or workspace-local
portfolio summaries. Portfolio outputs are read-only rollups over existing
Pharabius artifacts — no server, dashboard, or database is involved.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PortfolioRepositoryEntry(BaseModel):
    """A single repository's summary within a portfolio."""

    model_config = {"extra": "forbid"}

    repository_id: str
    project_name: str
    repository_path: str
    branch: str | None = None
    commit: str | None = None
    generated_at: str | None = None
    total_findings: int = 0
    priority_counts: dict[str, int] = Field(default_factory=dict)
    top_categories: list[str] = Field(default_factory=list)
    highest_priority: str | None = None
    has_ticket_drafts: bool = False
    has_export_bundles: bool = False
    validation_status: Literal["complete", "partial", "needs_review", "unknown"] = "unknown"
    limitations: list[str] = Field(default_factory=list)


class PortfolioRiskRollup(BaseModel):
    """Aggregate risk counts across all repositories."""

    model_config = {"extra": "forbid"}

    total_repositories: int = 0
    total_findings: int = 0
    priority_counts: dict[str, int] = Field(default_factory=dict)
    highest_priority: str | None = None


class PortfolioCategoryRollup(BaseModel):
    """Aggregate category counts across all repositories."""

    model_config = {"extra": "forbid"}

    category_counts: dict[str, int] = Field(default_factory=dict)
    top_categories: list[str] = Field(default_factory=list)


class PortfolioReadinessRollup(BaseModel):
    """Readiness and validation status across repositories."""

    model_config = {"extra": "forbid"}

    total_repositories: int = 0
    status_counts: dict[str, int] = Field(default_factory=dict)
    repositories_needing_review: list[str] = Field(default_factory=list)


class PortfolioSummary(BaseModel):
    """Top-level portfolio summary artifact."""

    model_config = {"extra": "forbid"}

    schema_version: str = "1.0"
    tool_version: str = ""
    generated_at: str = ""
    portfolio_id: str = ""
    repositories: list[PortfolioRepositoryEntry] = Field(default_factory=list)
    risk_rollup: PortfolioRiskRollup = Field(default_factory=PortfolioRiskRollup)
    category_rollup: PortfolioCategoryRollup = Field(default_factory=PortfolioCategoryRollup)
    readiness_rollup: PortfolioReadinessRollup = Field(default_factory=PortfolioReadinessRollup)
    validation_warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
