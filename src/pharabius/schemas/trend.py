"""Temporal trend schemas for tracking debt over time (v2.1.0).

TrendPoint captures a single run snapshot.
TrendSummary aggregates points with trajectory classification.

Design constraints:
- Gate result is approximated from severity counts when no gate artifact exists.
- Readiness status is "unknown" unless a readiness artifact is persisted.
- Category data is only populated when historical category data is available.
- Trajectory is heuristic, not a scientific measure of engineering quality.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TrendPoint(BaseModel):
    """A single run snapshot in the trend timeline."""

    model_config = {"extra": "forbid"}

    run_id: str
    timestamp: str
    commit: str | None = None
    branch: str | None = None
    total_findings: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    gate_result: Literal["pass", "fail", "unknown"] = "unknown"
    gate_approximated: bool = True
    readiness_status: Literal["ready", "partial", "needs_review", "unknown"] = "unknown"
    category_counts: dict[str, int] = Field(default_factory=dict)
    category_data_available: bool = False


class TrendSummary(BaseModel):
    """Aggregated trend summary with trajectory classification."""

    model_config = {"extra": "forbid"}

    schema_version: str = "1.0"
    generated_at: str = ""
    repository: str | None = None
    baseline_run_id: str | None = None
    latest_run_id: str | None = None
    run_count: int = 0
    points: list[TrendPoint] = Field(default_factory=list)
    deltas: dict[str, int] = Field(default_factory=dict)
    trajectory: Literal["improving", "stable", "worsening", "insufficient_data"] = (
        "insufficient_data"
    )
    warnings: list[str] = Field(default_factory=list)
