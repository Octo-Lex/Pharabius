"""Tests for trend schemas (v2.1.0 S01)."""

from __future__ import annotations

import json

from pharabius.schemas.trend import TrendPoint, TrendSummary


class TestTrendPoint:
    def test_create_with_defaults(self) -> None:
        tp = TrendPoint(run_id="RUN-001", timestamp="2026-01-01T00:00:00+00:00")
        assert tp.run_id == "RUN-001"
        assert tp.total_findings == 0
        assert tp.critical == 0
        assert tp.gate_result == "unknown"
        assert tp.gate_approximated is True
        assert tp.readiness_status == "unknown"
        assert tp.category_counts == {}
        assert tp.category_data_available is False

    def test_create_with_all_fields(self) -> None:
        tp = TrendPoint(
            run_id="RUN-002",
            timestamp="2026-01-02T00:00:00+00:00",
            commit="abc123",
            branch="main",
            total_findings=10,
            critical=1,
            high=3,
            medium=4,
            low=2,
            gate_result="fail",
            gate_approximated=True,
            readiness_status="partial",
            category_counts={"TD-DEP": 5, "TD-ARCH": 3},
            category_data_available=True,
        )
        assert tp.critical == 1
        assert tp.category_data_available is True

    def test_serialization_roundtrip(self) -> None:
        tp = TrendPoint(run_id="RUN-001", timestamp="2026-01-01T00:00:00+00:00", critical=2)
        data = json.loads(tp.model_dump_json())
        tp2 = TrendPoint.model_validate(data)
        assert tp2 == tp

    def test_extra_fields_rejected(self) -> None:
        import pytest

        with pytest.raises(Exception, match="Extra inputs"):
            TrendPoint(
                run_id="RUN-001",
                timestamp="2026-01-01T00:00:00+00:00",
                nonexistent_field=True,
            )


class TestTrendSummary:
    def test_create_with_defaults(self) -> None:
        ts = TrendSummary()
        assert ts.schema_version == "1.0"
        assert ts.run_count == 0
        assert ts.points == []
        assert ts.trajectory == "insufficient_data"
        assert ts.warnings == []

    def test_create_with_points(self) -> None:
        points = [
            TrendPoint(run_id="RUN-001", timestamp="2026-01-01T00:00:00+00:00"),
            TrendPoint(run_id="RUN-002", timestamp="2026-01-02T00:00:00+00:00"),
        ]
        ts = TrendSummary(
            run_count=2,
            points=points,
            baseline_run_id="RUN-001",
            latest_run_id="RUN-002",
            trajectory="stable",
        )
        assert len(ts.points) == 2
        assert ts.baseline_run_id == "RUN-001"

    def test_serialization_roundtrip(self) -> None:
        ts = TrendSummary(
            run_count=1,
            points=[TrendPoint(run_id="RUN-001", timestamp="2026-01-01T00:00:00+00:00")],
            deltas={"total": 5},
            warnings=["Single run only"],
        )
        data = json.loads(ts.model_dump_json())
        ts2 = TrendSummary.model_validate(data)
        assert ts2.deltas == {"total": 5}
        assert ts2.warnings == ["Single run only"]

    def test_extra_fields_rejected(self) -> None:
        import pytest

        with pytest.raises(Exception, match="Extra inputs"):
            TrendSummary(nonexistent=True)

    def test_trajectory_literals(self) -> None:
        for val in ("improving", "stable", "worsening", "insufficient_data"):
            ts = TrendSummary(trajectory=val)
            assert ts.trajectory == val
