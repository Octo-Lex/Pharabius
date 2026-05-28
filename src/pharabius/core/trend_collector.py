"""Run history collector for temporal trends (v2.1.0 S02).

Reads .ai-debt/runs/RUN-*.json files and extracts TrendPoint data.

Design constraints:
- Gate result is approximated from RunSummary severity counts using
  default thresholds. This is NOT the actual gate result — the original
  thresholds are not stored in run metadata.
- Category counts are NOT available from run metadata (RunSummary only
  stores severity counts). category_data_available is always False.
- Readiness is always 'unknown' (not persisted per run).
- Does not mutate .ai-debt/runs/ or any canonical artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path

from pharabius.schemas.run_metadata import RunMetadata
from pharabius.schemas.trend import TrendPoint


def _approximate_gate_result(
    critical: int, high: int, total: int
) -> tuple[str, bool]:
    """Approximate gate result from severity counts using default thresholds.

    Returns (result, approximated=True).
    Default thresholds: max_critical=0, max_high=10, max_total=50.
    """
    if critical > 0:
        return "fail", True
    if high > 10:
        return "fail", True
    if total > 50:
        return "fail", True
    return "pass", True


def collect_run_points(
    runs_dir: Path, warnings: list[str] | None = None
) -> list[TrendPoint]:
    """Collect TrendPoint data from run metadata files.

    Args:
        runs_dir: Path to .ai-debt/runs/
        warnings: Optional list to collect warning messages

    Returns:
        Sorted list of TrendPoint (oldest first, deterministic by run_id)
    """
    if warnings is None:
        warnings = []

    if not runs_dir.exists():
        warnings.append("No runs directory found")
        return []

    run_files = sorted(runs_dir.glob("RUN-*.json"))
    if not run_files:
        warnings.append("No run files found in runs directory")
        return []

    points: list[TrendPoint] = []
    for rf in run_files:
        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
            metadata = RunMetadata.model_validate(data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            warnings.append(f"Malformed run file skipped: {rf.name}")
            continue
        except Exception:
            warnings.append(f"Unreadable run file skipped: {rf.name}")
            continue

        summary = metadata.summary
        total = (
            summary.critical_findings
            + summary.high_findings
            + summary.medium_findings
            + summary.low_findings
        )

        gate_result, gate_approximated = _approximate_gate_result(
            summary.critical_findings, summary.high_findings, total
        )

        points.append(
            TrendPoint(
                run_id=metadata.run_id,
                timestamp=metadata.timestamp,
                commit=metadata.commit or None,
                branch=metadata.branch or None,
                total_findings=total,
                critical=summary.critical_findings,
                high=summary.high_findings,
                medium=summary.medium_findings,
                low=summary.low_findings,
                gate_result=gate_result,
                gate_approximated=gate_approximated,
                readiness_status="unknown",
                category_counts={},
                category_data_available=False,
            )
        )

    # Sort by timestamp, deterministic tie-break on run_id
    points.sort(key=lambda p: (p.timestamp, p.run_id))
    return points
