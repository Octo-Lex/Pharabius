"""Tests for trend reports and examples (v2.1.0 S05)."""

from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.trend_engine import compute_trend
from pharabius.core.trend_reports import (
    render_category_trends_md,
    render_gate_trends_md,
    render_risk_trends_md,
)
from pharabius.schemas.trend import TrendPoint

REPO_ROOT = Path(__file__).resolve().parent.parent


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


class TestRiskTrends:
    def test_improving_report(self) -> None:
        points = [
            _point(run_id="RUN-1", ts="2026-01-01", critical=2, high=3),
            _point(run_id="RUN-2", ts="2026-01-02", critical=0, high=1),
        ]
        summary = compute_trend(points)
        md = render_risk_trends_md(summary)
        assert "improving" in md
        assert "Severity Movement" in md
        assert "not a scientific measure" in md

    def test_worsening_report(self) -> None:
        points = [
            _point(run_id="RUN-1", ts="2026-01-01", critical=0),
            _point(run_id="RUN-2", ts="2026-01-02", critical=1),
        ]
        summary = compute_trend(points)
        md = render_risk_trends_md(summary)
        assert "worsening" in md

    def test_insufficient_data(self) -> None:
        summary = compute_trend([_point()])
        md = render_risk_trends_md(summary)
        assert "Insufficient data" in md


class TestCategoryTrends:
    def test_no_data_available(self) -> None:
        points = [
            _point(run_id="RUN-1", ts="2026-01-01"),
            _point(run_id="RUN-2", ts="2026-01-02"),
        ]
        summary = compute_trend(points)
        md = render_category_trends_md(summary)
        assert "Insufficient data" in md
        assert "not currently archived" in md

    def test_with_data_available(self) -> None:
        points = [
            TrendPoint(
                run_id="RUN-1",
                timestamp="2026-01-01T00:00:00+00:00",
                total_findings=5,
                category_counts={"TD-DEP": 3, "TD-ARCH": 2},
                category_data_available=True,
            ),
            TrendPoint(
                run_id="RUN-2",
                timestamp="2026-01-02T00:00:00+00:00",
                total_findings=4,
                category_counts={"TD-DEP": 2, "TD-ARCH": 2},
                category_data_available=True,
            ),
        ]
        summary = compute_trend(points)
        md = render_category_trends_md(summary)
        assert "TD-DEP" in md
        assert "Delta" in md


class TestGateTrends:
    def test_gate_table_rendered(self) -> None:
        points = [
            _point(run_id="RUN-1", ts="2026-01-01", critical=1),
            _point(run_id="RUN-2", ts="2026-01-02", critical=0),
        ]
        summary = compute_trend(points)
        md = render_gate_trends_md(summary)
        assert "Quality Gate Trends" in md
        assert "approximated" in md

    def test_empty_points(self) -> None:
        summary = compute_trend([])
        md = render_gate_trends_md(summary)
        assert "No run data" in md


class TestExampleFile:
    def test_example_json_valid(self) -> None:
        path = REPO_ROOT / "docs" / "examples" / "trends" / "trend-summary.example.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.0"
        assert data["trajectory"] == "improving"
        assert len(data["points"]) == 4
        assert data["run_count"] == 4
        assert "warnings" in data

    def test_example_has_honest_warnings(self) -> None:
        path = REPO_ROOT / "docs" / "examples" / "trends" / "trend-summary.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        warnings_text = " ".join(data["warnings"])
        assert "approximated" in warnings_text.lower()
        assert "category" in warnings_text.lower()
        assert "readiness" in warnings_text.lower()
