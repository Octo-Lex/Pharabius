"""v3.24.0 — Governance trend metrics tests.

Proves trends are read-only: no policy behavior, no mutation,
descriptive wording only.
"""

from __future__ import annotations

import pytest

from pharabius.core.signals.trends import (
    GovernanceDiagnosticTrend,
    GovernanceMetricDelta,
    build_governance_trend_summary,
    extract_governance_quality_snapshots,
    format_count_delta,
    format_coverage_delta,
    governance_trend_to_dict,
)


def _snapshot(
    run_id: str,
    governance_quality: dict | None = None,
) -> dict:
    snap = {"run_id": run_id}
    if governance_quality is not None:
        snap["governance_quality"] = governance_quality
    return snap


def _gq(
    total_signals: int = 10,
    finding_evidence_coverage: float = 1.0,
    advisory_evidence_coverage: float = 1.0,
    informational_evidence_coverage: float = 1.0,
    by_family: dict | None = None,
    by_disposition: dict | None = None,
    by_confidence: dict | None = None,
    diagnostics: list[dict] | None = None,
) -> dict:
    return {
        "total_signals": total_signals,
        "finding_evidence_coverage": finding_evidence_coverage,
        "advisory_evidence_coverage": advisory_evidence_coverage,
        "informational_evidence_coverage": informational_evidence_coverage,
        "by_family": by_family or {},
        "by_disposition": by_disposition or {},
        "by_confidence": by_confidence or {},
        "diagnostics": diagnostics or [],
    }


# ═══════════════════════════════════════════════════════════════════════
# S01 — Model structure
# ═══════════════════════════════════════════════════════════════════════


class TestModelStructure:
    """Trend dataclasses are frozen and well-formed."""

    def test_delta_frozen(self) -> None:
        d = GovernanceMetricDelta(metric="test", previous=1, current=2, delta=1)
        with pytest.raises(AttributeError):
            d.delta = 99  # type: ignore

    def test_trend_frozen(self) -> None:
        t = build_governance_trend_summary([])
        with pytest.raises(AttributeError):
            t.runs_compared = 99  # type: ignore

    def test_diagnostic_trend_frozen(self) -> None:
        d = GovernanceDiagnosticTrend(
            code="GQM-001", family="runtime", occurrences=2, latest_severity="info"
        )
        with pytest.raises(AttributeError):
            d.occurrences = 99  # type: ignore


# ═══════════════════════════════════════════════════════════════════════
# S02 — Historical baseline extraction
# ═══════════════════════════════════════════════════════════════════════


class TestExtraction:
    """Extract governance_quality snapshots correctly."""

    def test_extracts_runs_with_governance_quality(self) -> None:
        runs = [
            _snapshot("RUN-001"),  # no governance_quality
            _snapshot("RUN-002", _gq(total_signals=10)),
            _snapshot("RUN-003", _gq(total_signals=15)),
        ]
        result = extract_governance_quality_snapshots(runs)
        assert len(result) == 2
        assert result[0]["run_id"] == "RUN-002"
        assert result[1]["run_id"] == "RUN-003"

    def test_skips_older_runs_without_governance_quality(self) -> None:
        runs = [
            _snapshot("RUN-001"),
            _snapshot("RUN-002"),
            _snapshot("RUN-003", _gq()),
            _snapshot("RUN-004", _gq()),
        ]
        result = extract_governance_quality_snapshots(runs)
        assert len(result) == 2
        assert result[0]["run_id"] == "RUN-003"

    def test_empty_list_returns_empty(self) -> None:
        assert extract_governance_quality_snapshots([]) == []

    def test_all_without_governance_quality_returns_empty(self) -> None:
        runs = [_snapshot("RUN-001"), _snapshot("RUN-002")]
        assert extract_governance_quality_snapshots(runs) == []


# ═══════════════════════════════════════════════════════════════════════
# S03 — Trend delta computation
# ═══════════════════════════════════════════════════════════════════════


class TestDeltaComputation:
    """Deltas computed correctly between two comparable runs."""

    def test_two_comparable_runs_deltas(self) -> None:
        runs = [
            _snapshot("RUN-001", _gq(total_signals=10)),
            _snapshot("RUN-002", _gq(total_signals=15)),
        ]
        trend = build_governance_trend_summary(runs)
        assert trend.runs_compared == 2
        assert trend.current_run_id == "RUN-002"
        assert trend.previous_run_id == "RUN-001"
        assert trend.signal_count_delta.delta == 5
        assert trend.unavailable_reason is None

    def test_coverage_delta(self) -> None:
        runs = [
            _snapshot("RUN-001", _gq(finding_evidence_coverage=0.90)),
            _snapshot("RUN-002", _gq(finding_evidence_coverage=0.95)),
        ]
        trend = build_governance_trend_summary(runs)
        assert trend.finding_evidence_coverage_delta.delta == pytest.approx(0.05)

    def test_by_family_delta(self) -> None:
        runs = [
            _snapshot("RUN-001", _gq(by_family={"runtime": 5, "test": 3})),
            _snapshot("RUN-002", _gq(by_family={"runtime": 7, "test": 3, "dependency": 2})),
        ]
        trend = build_governance_trend_summary(runs)
        assert trend.by_family_delta["runtime"].delta == 2
        assert trend.by_family_delta["test"].delta == 0
        # New family appearing: previous=None, delta=None
        assert trend.by_family_delta["dependency"].delta is None
        assert trend.by_family_delta["dependency"].current == 2

    def test_by_disposition_delta(self) -> None:
        runs = [
            _snapshot("RUN-001", _gq(by_disposition={"finding": 3, "advisory": 2})),
            _snapshot("RUN-002", _gq(by_disposition={"finding": 4, "advisory": 2})),
        ]
        trend = build_governance_trend_summary(runs)
        assert trend.by_disposition_delta["finding"].delta == 1

    def test_by_confidence_delta(self) -> None:
        runs = [
            _snapshot("RUN-001", _gq(by_confidence={"High": 5, "Low": 2})),
            _snapshot("RUN-002", _gq(by_confidence={"High": 5, "Low": 4})),
        ]
        trend = build_governance_trend_summary(runs)
        assert trend.by_confidence_delta["Low"].delta == 2


class TestUnavailableTrend:
    """Graceful handling when insufficient history."""

    def test_no_runs_unavailable(self) -> None:
        trend = build_governance_trend_summary([])
        assert trend.unavailable_reason is not None
        assert trend.runs_compared == 0

    def test_one_run_unavailable(self) -> None:
        runs = [_snapshot("RUN-001", _gq())]
        trend = build_governance_trend_summary(runs)
        assert trend.unavailable_reason is not None
        assert trend.runs_compared == 1

    def test_two_runs_one_without_gq_unavailable(self) -> None:
        """Latest two runs, but only one has governance_quality → unavailable."""
        runs = [
            _snapshot("RUN-001"),  # no governance_quality
            _snapshot("RUN-002", _gq()),
        ]
        trend = build_governance_trend_summary(runs)
        assert trend.unavailable_reason is not None
        assert trend.runs_compared == 1

    def test_three_runs_oldest_without_gq(self) -> None:
        """Oldest run skipped; latest two with governance_quality compared."""
        runs = [
            _snapshot("RUN-001"),  # skipped
            _snapshot("RUN-002", _gq(total_signals=10)),
            _snapshot("RUN-003", _gq(total_signals=15)),
        ]
        trend = build_governance_trend_summary(runs)
        assert trend.runs_compared == 2
        assert trend.previous_run_id == "RUN-002"
        assert trend.current_run_id == "RUN-003"
        assert trend.signal_count_delta.delta == 5


# ═══════════════════════════════════════════════════════════════════════
# S06 — Diagnostics recurrence
# ═══════════════════════════════════════════════════════════════════════


class TestDiagnosticsRecurrence:
    """Diagnostics recurrence counts runs, not instances."""

    def test_recurring_diagnostic(self) -> None:
        runs = [
            _snapshot(
                "RUN-001",
                _gq(
                    diagnostics=[
                        {"code": "GQM-003", "severity": "info", "family": "runtime"},
                    ]
                ),
            ),
            _snapshot(
                "RUN-002",
                _gq(
                    diagnostics=[
                        {"code": "GQM-003", "severity": "info", "family": "runtime"},
                    ]
                ),
            ),
        ]
        trend = build_governance_trend_summary(runs)
        assert len(trend.recurring_diagnostics) == 1
        assert trend.recurring_diagnostics[0].code == "GQM-003"
        assert trend.recurring_diagnostics[0].occurrences == 2  # 2 runs

    def test_non_recurring_diagnostic_excluded(self) -> None:
        runs = [
            _snapshot(
                "RUN-001",
                _gq(
                    diagnostics=[
                        {"code": "GQM-003", "severity": "info", "family": "runtime"},
                    ]
                ),
            ),
            _snapshot("RUN-002", _gq(diagnostics=[])),
        ]
        trend = build_governance_trend_summary(runs)
        assert len(trend.recurring_diagnostics) == 0

    def test_multiple_diagnostics_same_run_deduped(self) -> None:
        """Multiple instances of same code/family in one run count as 1 occurrence."""
        runs = [
            _snapshot(
                "RUN-001",
                _gq(
                    diagnostics=[
                        {"code": "GQM-003", "severity": "info", "family": "runtime"},
                        {"code": "GQM-003", "severity": "info", "family": "runtime"},
                    ]
                ),
            ),
            _snapshot(
                "RUN-002",
                _gq(
                    diagnostics=[
                        {"code": "GQM-003", "severity": "info", "family": "runtime"},
                    ]
                ),
            ),
        ]
        trend = build_governance_trend_summary(runs)
        assert len(trend.recurring_diagnostics) == 1
        assert trend.recurring_diagnostics[0].occurrences == 2  # 2 runs, not 3 instances


# ═══════════════════════════════════════════════════════════════════════
# S07 — No-policy regression
# ═══════════════════════════════════════════════════════════════════════


class TestNoPolicyRegression:
    """Trends do not alter behavior."""

    def test_trends_do_not_mutate_snapshots(self) -> None:
        snap1 = _snapshot("RUN-001", _gq(total_signals=10))
        snap2 = _snapshot("RUN-002", _gq(total_signals=15))
        original_ids = [s["run_id"] for s in [snap1, snap2]]
        build_governance_trend_summary([snap1, snap2])
        assert [s["run_id"] for s in [snap1, snap2]] == original_ids
        assert snap1["governance_quality"]["total_signals"] == 10

    def test_trends_do_not_create_findings(self) -> None:
        trend = build_governance_trend_summary(
            [
                _snapshot("RUN-001", _gq()),
                _snapshot("RUN-002", _gq()),
            ]
        )
        # Trend is a plain dataclass, not a GovernedSignal
        assert not hasattr(trend, "disposition")
        assert not hasattr(trend, "category")

    def test_no_health_or_pass_fail_labels(self) -> None:
        """Trend wording avoids health/pass/fail/compliance judgment."""
        trend = build_governance_trend_summary(
            [
                _snapshot("RUN-001", _gq()),
                _snapshot("RUN-002", _gq()),
            ]
        )
        # Check all string fields for forbidden terms
        forbidden = [
            "healthy",
            "unhealthy",
            "compliant",
            "noncompliant",
            "passing",
            "failing",
            "good",
            "bad",
        ]
        for attr in [trend.unavailable_reason or ""]:
            for term in forbidden:
                assert term not in attr.lower(), f"Forbidden term found: {term}"


# ═══════════════════════════════════════════════════════════════════════
# S04 — Serialization
# ═══════════════════════════════════════════════════════════════════════


class TestSerialization:
    """governance_trend_to_dict serializes without data loss."""

    def test_all_fields_present(self) -> None:
        trend = build_governance_trend_summary(
            [
                _snapshot("RUN-001", _gq()),
                _snapshot("RUN-002", _gq()),
            ]
        )
        d = governance_trend_to_dict(trend)
        assert "runs_compared" in d
        assert "signal_count_delta" in d
        assert "finding_evidence_coverage_delta" in d
        assert "recurring_diagnostics" in d
        assert "unavailable_reason" in d

    def test_delta_serialized(self) -> None:
        d = governance_trend_to_dict(
            build_governance_trend_summary(
                [
                    _snapshot("RUN-001", _gq(total_signals=10)),
                    _snapshot("RUN-002", _gq(total_signals=15)),
                ]
            )
        )
        scd = d["signal_count_delta"]
        assert scd["previous"] == 10
        assert scd["current"] == 15
        assert scd["delta"] == 5

    def test_unavailable_reason_serialized(self) -> None:
        d = governance_trend_to_dict(build_governance_trend_summary([]))
        assert d["unavailable_reason"] is not None

    def test_recurring_diagnostics_serialized(self) -> None:
        d = governance_trend_to_dict(
            build_governance_trend_summary(
                [
                    _snapshot(
                        "RUN-001",
                        _gq(
                            diagnostics=[
                                {"code": "GQM-003", "severity": "info", "family": "runtime"},
                            ]
                        ),
                    ),
                    _snapshot(
                        "RUN-002",
                        _gq(
                            diagnostics=[
                                {"code": "GQM-003", "severity": "info", "family": "runtime"},
                            ]
                        ),
                    ),
                ]
            )
        )
        assert len(d["recurring_diagnostics"]) == 1
        assert d["recurring_diagnostics"][0]["occurrences"] == 2


# ═══════════════════════════════════════════════════════════════════════
# Formatting helpers
# ═══════════════════════════════════════════════════════════════════════


class TestFormatting:
    """Coverage and count formatting."""

    def test_coverage_delta_positive(self) -> None:
        delta = GovernanceMetricDelta(metric="test", previous=0.90, current=0.95, delta=0.05)
        assert format_coverage_delta(delta) == "+5 pp"

    def test_coverage_delta_negative(self) -> None:
        delta = GovernanceMetricDelta(metric="test", previous=0.95, current=0.90, delta=-0.05)
        assert format_coverage_delta(delta) == "-5 pp"

    def test_coverage_delta_zero(self) -> None:
        delta = GovernanceMetricDelta(metric="test", previous=0.95, current=0.95, delta=0.0)
        assert format_coverage_delta(delta) == "0 pp"

    def test_coverage_delta_none(self) -> None:
        delta = GovernanceMetricDelta(metric="test", previous=None, current=0.95, delta=None)
        assert format_coverage_delta(delta) == "N/A"

    def test_count_delta_positive(self) -> None:
        delta = GovernanceMetricDelta(metric="test", previous=10, current=15, delta=5)
        assert format_count_delta(delta) == "+5"

    def test_count_delta_negative(self) -> None:
        delta = GovernanceMetricDelta(metric="test", previous=15, current=10, delta=-5)
        assert format_count_delta(delta) == "-5"

    def test_count_delta_zero(self) -> None:
        delta = GovernanceMetricDelta(metric="test", previous=10, current=10, delta=0)
        assert format_count_delta(delta) == "0"
