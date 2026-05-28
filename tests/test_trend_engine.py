"""Tests for trend computation engine (v2.1.0 S03)."""

from __future__ import annotations

from pharabius.core.trend_engine import compute_trend
from pharabius.schemas.trend import TrendPoint


def _point(
    run_id: str = "RUN-001",
    ts: str = "2026-01-01T00:00:00+00:00",
    **kwargs: int,
) -> TrendPoint:
    return TrendPoint(
        run_id=run_id,
        timestamp=ts,
        total_findings=kwargs.get(
            "total",
            kwargs.get("critical", 0)
            + kwargs.get("high", 0)
            + kwargs.get("medium", 0)
            + kwargs.get("low", 0),
        ),
        critical=kwargs.get("critical", 0),
        high=kwargs.get("high", 0),
        medium=kwargs.get("medium", 0),
        low=kwargs.get("low", 0),
    )


class TestInsufficientData:
    def test_zero_points(self) -> None:
        result = compute_trend([])
        assert result.trajectory == "insufficient_data"
        assert result.run_count == 0
        assert result.deltas == {}
        assert any("Insufficient" in w for w in result.warnings)

    def test_single_point(self) -> None:
        result = compute_trend([_point()])
        assert result.trajectory == "insufficient_data"
        assert result.run_count == 1


class TestImproving:
    def test_critical_decreased(self) -> None:
        points = [
            _point(run_id="RUN-1", ts="2026-01-01", critical=3, high=2),
            _point(run_id="RUN-2", ts="2026-01-02", critical=1, high=2),
        ]
        result = compute_trend(points)
        assert result.trajectory == "improving"
        assert result.deltas["critical"] == -2

    def test_high_decreased(self) -> None:
        points = [
            _point(run_id="RUN-1", ts="2026-01-01", high=5),
            _point(run_id="RUN-2", ts="2026-01-02", high=2),
        ]
        result = compute_trend(points)
        assert result.trajectory == "improving"
        assert result.deltas["high"] == -3


class TestWorsening:
    def test_critical_increased(self) -> None:
        points = [
            _point(run_id="RUN-1", ts="2026-01-01", critical=0),
            _point(run_id="RUN-2", ts="2026-01-02", critical=1),
        ]
        result = compute_trend(points)
        assert result.trajectory == "worsening"
        assert result.deltas["critical"] == 1

    def test_high_increased(self) -> None:
        points = [
            _point(run_id="RUN-1", ts="2026-01-01", high=3),
            _point(run_id="RUN-2", ts="2026-01-02", high=5),
        ]
        result = compute_trend(points)
        assert result.trajectory == "worsening"


class TestStable:
    def test_no_critical_high_change(self) -> None:
        points = [
            _point(run_id="RUN-1", ts="2026-01-01", critical=1, high=2, medium=5),
            _point(run_id="RUN-2", ts="2026-01-02", critical=1, high=2, medium=3),
        ]
        result = compute_trend(points)
        assert result.trajectory == "stable"
        assert result.deltas["critical"] == 0
        assert result.deltas["high"] == 0
        assert result.deltas["medium"] == -2


class TestDeltas:
    def test_total_delta(self) -> None:
        points = [
            _point(run_id="RUN-1", ts="2026-01-01", critical=2, high=3, medium=5, low=1),
            _point(run_id="RUN-2", ts="2026-01-02", critical=1, high=4, medium=3, low=2),
        ]
        result = compute_trend(points)
        assert result.deltas["total"] == -1  # 11 → 10
        assert result.deltas["critical"] == -1
        assert result.deltas["high"] == 1
        assert result.deltas["medium"] == -2
        assert result.deltas["low"] == 1


class TestBaselineAndLatest:
    def test_sets_baseline_and_latest(self) -> None:
        points = [
            _point(run_id="RUN-1", ts="2026-01-01"),
            _point(run_id="RUN-2", ts="2026-01-02"),
            _point(run_id="RUN-3", ts="2026-01-03"),
        ]
        result = compute_trend(points)
        assert result.baseline_run_id == "RUN-1"
        assert result.latest_run_id == "RUN-3"
        assert result.run_count == 3


class TestWarnings:
    def test_gate_approximation_warning(self) -> None:
        points = [
            _point(run_id="RUN-1", ts="2026-01-01"),
            _point(run_id="RUN-2", ts="2026-01-02"),
        ]
        result = compute_trend(points)
        assert any("approximated" in w.lower() for w in result.warnings)

    def test_category_unavailable_warning(self) -> None:
        points = [
            _point(run_id="RUN-1", ts="2026-01-01"),
            _point(run_id="RUN-2", ts="2026-01-02"),
        ]
        result = compute_trend(points)
        assert any("category" in w.lower() for w in result.warnings)

    def test_readiness_unavailable_warning(self) -> None:
        points = [
            _point(run_id="RUN-1", ts="2026-01-01"),
            _point(run_id="RUN-2", ts="2026-01-02"),
        ]
        result = compute_trend(points)
        assert any("readiness" in w.lower() for w in result.warnings)

    def test_existing_warnings_preserved(self) -> None:
        points = [
            _point(run_id="RUN-1", ts="2026-01-01"),
            _point(run_id="RUN-2", ts="2026-01-02"),
        ]
        result = compute_trend(points, existing_warnings=["Malformed run skipped"])
        assert any("Malformed" in w for w in result.warnings)
