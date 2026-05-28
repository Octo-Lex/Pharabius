"""Trend computation engine (v2.1.0 S03).

Computes deltas, trajectory classification, and warnings from collected
TrendPoints. Deterministic, read-only, no network access.

Trajectory rules are heuristic, not a scientific measure:
- improving: critical+high decreased from baseline
- worsening: critical+high increased from baseline
- stable: critical+high unchanged
- insufficient_data: fewer than 2 valid points
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pharabius.schemas.trend import TrendPoint, TrendSummary


def _compute_deltas(baseline: TrendPoint, latest: TrendPoint) -> dict[str, int]:
    """Compute severity deltas (baseline → latest)."""
    return {
        "total": latest.total_findings - baseline.total_findings,
        "critical": latest.critical - baseline.critical,
        "high": latest.high - baseline.high,
        "medium": latest.medium - baseline.medium,
        "low": latest.low - baseline.low,
    }


def _classify_trajectory(deltas: dict[str, int]) -> Literal["improving", "stable", "worsening"]:
    """Classify trajectory from severity deltas.

    Heuristic rules:
    - worsening: critical or high increased
    - improving: critical+high decreased (neither increased)
    - stable: critical+high unchanged
    """
    crit_delta = deltas.get("critical", 0)
    high_delta = deltas.get("high", 0)
    combined = crit_delta + high_delta

    if combined > 0:
        return "worsening"
    elif combined < 0:
        return "improving"
    else:
        return "stable"


def compute_trend(
    points: list[TrendPoint],
    repository: str | None = None,
    existing_warnings: list[str] | None = None,
) -> TrendSummary:
    """Compute trend summary from collected run points.

    Args:
        points: Sorted list of TrendPoint (oldest first)
        repository: Optional repository path
        existing_warnings: Warnings from collection phase

    Returns:
        TrendSummary with trajectory and deltas
    """
    warnings = list(existing_warnings) if existing_warnings else []

    now = datetime.now(UTC).replace(microsecond=0).isoformat()

    if len(points) < 2:
        warnings.append(
            f"Insufficient data: {len(points)} run(s). "
            "At least 2 runs required for trajectory analysis."
        )
        return TrendSummary(
            generated_at=now,
            repository=repository,
            baseline_run_id=points[0].run_id if points else None,
            latest_run_id=points[-1].run_id if points else None,
            run_count=len(points),
            points=points,
            deltas={},
            trajectory="insufficient_data",
            warnings=warnings,
        )

    baseline = points[0]
    latest = points[-1]
    deltas = _compute_deltas(baseline, latest)
    trajectory = _classify_trajectory(deltas)

    traj_literal: Literal["improving", "stable", "worsening", "insufficient_data"] = trajectory

    if baseline.gate_approximated:
        warnings.append(
            "Gate results are approximated from severity counts "
            "using default thresholds. Actual gate thresholds may differ."
        )
    if not baseline.category_data_available:
        warnings.append(
            "Category trends unavailable: run metadata does not store per-run category breakdowns."
        )
    if baseline.readiness_status == "unknown":
        warnings.append("Readiness trends unavailable: readiness status is not persisted per run.")

    return TrendSummary(
        generated_at=now,
        repository=repository,
        baseline_run_id=baseline.run_id,
        latest_run_id=latest.run_id,
        run_count=len(points),
        points=points,
        deltas=deltas,
        trajectory=traj_literal,
        warnings=warnings,
    )
