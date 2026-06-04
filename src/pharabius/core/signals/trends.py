"""Governance quality trend metrics.

Read-only historical analytics across run-history snapshots.
Does not create findings, advisories, work packages, or alter behavior.
Trends are descriptive: increased, decreased, unchanged, not enough history.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GovernanceMetricDelta:
    """Delta between two governance metric values."""

    metric: str
    previous: float | int | None
    current: float | int
    delta: float | int | None


@dataclass(frozen=True)
class GovernanceDiagnosticTrend:
    """Recurring diagnostic across comparable runs.

    occurrences = number of comparable runs containing this code/family pair,
    not total diagnostic instances within a single run.
    """

    code: str
    family: str | None
    occurrences: int  # number of RUNS, not instances
    latest_severity: str


@dataclass(frozen=True)
class GovernanceTrendSummary:
    """Read-only governance quality trend across runs.

    Descriptive only. No gates, thresholds, health scores, or pass/fail labels.
    """

    runs_compared: int
    current_run_id: str | None
    previous_run_id: str | None
    signal_count_delta: GovernanceMetricDelta
    finding_evidence_coverage_delta: GovernanceMetricDelta
    advisory_evidence_coverage_delta: GovernanceMetricDelta
    informational_evidence_coverage_delta: GovernanceMetricDelta
    by_disposition_delta: dict[str, GovernanceMetricDelta] = field(default_factory=dict)
    by_family_delta: dict[str, GovernanceMetricDelta] = field(default_factory=dict)
    by_confidence_delta: dict[str, GovernanceMetricDelta] = field(default_factory=dict)
    recurring_diagnostics: list[GovernanceDiagnosticTrend] = field(default_factory=list)
    unavailable_reason: str | None = None


def extract_governance_quality_snapshots(runs: list[dict]) -> list[dict]:
    """Extract runs that contain governance_quality, sorted chronologically.

    Skips older snapshots without governance_quality.
    Does not backfill or mutate older snapshots.
    Does not infer missing governance_quality from raw artifacts.
    """
    result = []
    for run in runs:
        gq = run.get("governance_quality")
        if gq is not None and isinstance(gq, dict):
            result.append(run)
    return result


def _metric_delta(
    name: str,
    previous: float | int | None,
    current: float | int,
) -> GovernanceMetricDelta:
    if previous is None:
        return GovernanceMetricDelta(metric=name, previous=None, current=current, delta=None)
    delta = current - previous
    return GovernanceMetricDelta(metric=name, previous=previous, current=current, delta=delta)


def _dict_delta(
    name_prefix: str,
    previous: dict[str, float | int],
    current: dict[str, float | int],
    all_keys: set[str] | None = None,
) -> dict[str, GovernanceMetricDelta]:
    """Compute deltas for dict-valued metrics (by_family, by_disposition, etc.)."""
    keys = all_keys or (set(previous.keys()) | set(current.keys()))
    result = {}
    for key in sorted(keys):
        prev_val = previous.get(key)
        curr_val = current.get(key, 0)
        if prev_val is None and curr_val == 0:
            continue
        if prev_val is None:
            result[key] = _metric_delta(f"{name_prefix}.{key}", None, curr_val)
        else:
            result[key] = _metric_delta(f"{name_prefix}.{key}", prev_val, curr_val)
    return result


def _compute_recurring_diagnostics(
    snapshots: list[dict],
) -> list[GovernanceDiagnosticTrend]:
    """Compute diagnostics appearing in ≥ 2 comparable runs.

    occurrences = number of runs containing this code/family pair.
    """
    from collections import defaultdict

    # Track per-run diagnostic sets (deduplicated within each run)
    run_diags: list[set[tuple[str, str | None]]] = []
    # Track latest severity per code/family
    latest_severity: dict[tuple[str, str | None], str] = {}

    for snap in snapshots:
        gq = snap.get("governance_quality", {})
        diags = gq.get("diagnostics", [])
        run_set: set[tuple[str, str | None]] = set()
        for d in diags:
            code = d.get("code", "")
            family = d.get("family")
            severity = d.get("severity", "info")
            pair = (code, family)
            run_set.add(pair)
            latest_severity[pair] = severity
        run_diags.append(run_set)

    # Count occurrences across runs
    count: dict[tuple[str, str | None], int] = defaultdict(int)
    for run_set in run_diags:
        for pair in run_set:
            count[pair] += 1

    # Only include diagnostics appearing in ≥ 2 runs
    recurring = []
    for (code, family), occurrences in sorted(
        count.items(), key=lambda x: (x[0][0], x[0][1] or "")
    ):
        if occurrences >= 2:
            recurring.append(
                GovernanceDiagnosticTrend(
                    code=code,
                    family=family,
                    occurrences=occurrences,
                    latest_severity=latest_severity.get((code, family), "info"),
                )
            )

    return recurring


def build_governance_trend_summary(
    run_snapshots: list[dict],
) -> GovernanceTrendSummary:
    """Compute governance quality trend across runs.

    Uses the latest two snapshots that contain governance_quality,
    not merely the latest two runs.
    """
    comparable = extract_governance_quality_snapshots(run_snapshots)

    if len(comparable) < 2:
        return GovernanceTrendSummary(
            runs_compared=len(comparable),
            current_run_id=comparable[-1].get("run_id") if comparable else None,
            previous_run_id=None,
            signal_count_delta=GovernanceMetricDelta(
                metric="total_signals",
                previous=None,
                current=0,
                delta=None,
            ),
            finding_evidence_coverage_delta=GovernanceMetricDelta(
                metric="finding_evidence_coverage",
                previous=None,
                current=1.0,
                delta=None,
            ),
            advisory_evidence_coverage_delta=GovernanceMetricDelta(
                metric="advisory_evidence_coverage",
                previous=None,
                current=1.0,
                delta=None,
            ),
            informational_evidence_coverage_delta=GovernanceMetricDelta(
                metric="informational_evidence_coverage",
                previous=None,
                current=1.0,
                delta=None,
            ),
            unavailable_reason=(
                "Fewer than two runs contain governance_quality metrics."
                if comparable
                else "No runs contain governance_quality metrics."
            ),
        )

    previous = comparable[-2]
    current = comparable[-1]

    prev_gq = previous.get("governance_quality", {})
    curr_gq = current.get("governance_quality", {})

    return GovernanceTrendSummary(
        runs_compared=2,
        current_run_id=current.get("run_id"),
        previous_run_id=previous.get("run_id"),
        signal_count_delta=_metric_delta(
            "total_signals",
            prev_gq.get("total_signals"),
            curr_gq.get("total_signals", 0),
        ),
        finding_evidence_coverage_delta=_metric_delta(
            "finding_evidence_coverage",
            prev_gq.get("finding_evidence_coverage"),
            curr_gq.get("finding_evidence_coverage", 1.0),
        ),
        advisory_evidence_coverage_delta=_metric_delta(
            "advisory_evidence_coverage",
            prev_gq.get("advisory_evidence_coverage"),
            curr_gq.get("advisory_evidence_coverage", 1.0),
        ),
        informational_evidence_coverage_delta=_metric_delta(
            "informational_evidence_coverage",
            prev_gq.get("informational_evidence_coverage"),
            curr_gq.get("informational_evidence_coverage", 1.0),
        ),
        by_disposition_delta=_dict_delta(
            "by_disposition",
            prev_gq.get("by_disposition", {}),
            curr_gq.get("by_disposition", {}),
        ),
        by_family_delta=_dict_delta(
            "by_family",
            prev_gq.get("by_family", {}),
            curr_gq.get("by_family", {}),
        ),
        by_confidence_delta=_dict_delta(
            "by_confidence",
            prev_gq.get("by_confidence", {}),
            curr_gq.get("by_confidence", {}),
        ),
        recurring_diagnostics=_compute_recurring_diagnostics(comparable),
        unavailable_reason=None,
    )


def governance_trend_to_dict(trend: GovernanceTrendSummary) -> dict:
    """Serialize governance trend summary to JSON-compatible dict.

    All fields preserved without data loss.
    """

    def _delta_to_dict(d: GovernanceMetricDelta) -> dict:
        return {
            "metric": d.metric,
            "previous": d.previous,
            "current": d.current,
            "delta": d.delta,
        }

    return {
        "runs_compared": trend.runs_compared,
        "current_run_id": trend.current_run_id,
        "previous_run_id": trend.previous_run_id,
        "signal_count_delta": _delta_to_dict(trend.signal_count_delta),
        "finding_evidence_coverage_delta": _delta_to_dict(trend.finding_evidence_coverage_delta),
        "advisory_evidence_coverage_delta": _delta_to_dict(trend.advisory_evidence_coverage_delta),
        "informational_evidence_coverage_delta": _delta_to_dict(
            trend.informational_evidence_coverage_delta
        ),
        "by_disposition_delta": {
            k: _delta_to_dict(v) for k, v in trend.by_disposition_delta.items()
        },
        "by_family_delta": {k: _delta_to_dict(v) for k, v in trend.by_family_delta.items()},
        "by_confidence_delta": {k: _delta_to_dict(v) for k, v in trend.by_confidence_delta.items()},
        "recurring_diagnostics": [
            {
                "code": d.code,
                "family": d.family,
                "occurrences": d.occurrences,
                "latest_severity": d.latest_severity,
            }
            for d in trend.recurring_diagnostics
        ],
        "unavailable_reason": trend.unavailable_reason,
    }


def format_coverage_delta(delta: GovernanceMetricDelta) -> str:
    """Format coverage ratio delta as percentage points.

    Example: previous=0.92, current=0.95 → "+3 pp"
    """
    if delta.delta is None:
        return "N/A"
    pp = delta.delta * 100
    if pp == 0:
        return "0 pp"
    return f"+{pp:.0f} pp" if pp > 0 else f"{pp:.0f} pp"


def format_count_delta(delta: GovernanceMetricDelta) -> str:
    """Format integer count delta with sign."""
    if delta.delta is None:
        return "N/A"
    d = delta.delta
    if d == 0:
        return "0"
    return f"+{d}" if d > 0 else str(d)
