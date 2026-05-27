"""Run diff schemas for temporal comparison (W53-S03)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DiffSummary(BaseModel):
    """Summary counts for a diff."""

    model_config = {"extra": "forbid"}

    before_total: int
    after_total: int
    new_count: int
    resolved_count: int
    severity_change_count: int
    confidence_change_count: int
    net_change: int


class FindingChange(BaseModel):
    """A change in a single finding."""

    model_config = {"extra": "forbid"}

    id: str
    from_value: str
    to_value: str


class RunDiff(BaseModel):
    """Diff between two analysis runs."""

    model_config = {"extra": "forbid"}

    schema_version: str = "1.0"
    before_run_id: str
    after_run_id: str
    new_findings: list[str] = Field(default_factory=list)
    resolved_findings: list[str] = Field(default_factory=list)
    severity_changes: list[FindingChange] = Field(default_factory=list)
    confidence_changes: list[FindingChange] = Field(default_factory=list)
    summary: DiffSummary
