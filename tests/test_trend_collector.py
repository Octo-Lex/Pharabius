"""Tests for run history collector (v2.1.0 S02)."""

from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.trend_collector import collect_run_points
from pharabius.schemas.run_metadata import RunMetadata, RunSummary


def _write_run(path: Path, run_id: str, timestamp: str, **kwargs: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = RunSummary(
        critical_findings=kwargs.get("critical", 0),
        high_findings=kwargs.get("high", 0),
        medium_findings=kwargs.get("medium", 0),
        low_findings=kwargs.get("low", 0),
    )
    meta = RunMetadata(
        run_id=run_id,
        timestamp=timestamp,
        commit=kwargs.get("commit", ""),
        branch=kwargs.get("branch", ""),
        summary=summary,
    )
    path.write_text(meta.model_dump_json(indent=2), encoding="utf-8")


class TestNoRuns:
    def test_missing_directory(self, tmp_path: Path) -> None:
        warnings: list[str] = []
        points = collect_run_points(tmp_path / "nonexistent", warnings)
        assert points == []
        assert any("No runs directory" in w for w in warnings)

    def test_empty_directory(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        runs.mkdir()
        warnings: list[str] = []
        points = collect_run_points(runs, warnings)
        assert points == []
        assert any("No run files" in w for w in warnings)


class TestSingleRun:
    def test_single_run(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        _write_run(runs / "RUN-001.json", "RUN-001", "2026-01-01T00:00:00+00:00")
        points = collect_run_points(runs)
        assert len(points) == 1
        assert points[0].run_id == "RUN-001"

    def test_single_run_preserves_severity(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        _write_run(
            runs / "RUN-001.json",
            "RUN-001",
            "2026-01-01T00:00:00+00:00",
            critical=2,
            high=3,
            medium=5,
            low=1,
        )
        points = collect_run_points(runs)
        assert points[0].critical == 2
        assert points[0].high == 3
        assert points[0].medium == 5
        assert points[0].low == 1
        assert points[0].total_findings == 11


class TestMultipleRuns:
    def test_sorted_by_timestamp(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        _write_run(runs / "RUN-002.json", "RUN-002", "2026-01-02T00:00:00+00:00")
        _write_run(runs / "RUN-001.json", "RUN-001", "2026-01-01T00:00:00+00:00")
        _write_run(runs / "RUN-003.json", "RUN-003", "2026-01-03T00:00:00+00:00")
        points = collect_run_points(runs)
        assert [p.run_id for p in points] == ["RUN-001", "RUN-002", "RUN-003"]

    def test_deterministic_tiebreak(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        _write_run(runs / "RUN-B.json", "RUN-B", "2026-01-01T00:00:00+00:00")
        _write_run(runs / "RUN-A.json", "RUN-A", "2026-01-01T00:00:00+00:00")
        points = collect_run_points(runs)
        assert [p.run_id for p in points] == ["RUN-A", "RUN-B"]


class TestMalformedRuns:
    def test_malformed_json_skipped(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        runs.mkdir()
        (runs / "RUN-bad.json").write_text("not json{{{", encoding="utf-8")
        _write_run(runs / "RUN-001.json", "RUN-001", "2026-01-01T00:00:00+00:00")
        warnings: list[str] = []
        points = collect_run_points(runs, warnings)
        assert len(points) == 1
        assert any("Malformed" in w for w in warnings)

    def test_invalid_schema_skipped(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        runs.mkdir()
        # run_id must be a string; passing a number triggers validation error
        (runs / "RUN-bad.json").write_text(
            json.dumps({"schema_version": "1.0", "run_id": 12345}),
            encoding="utf-8",
        )
        _write_run(runs / "RUN-001.json", "RUN-001", "2026-01-01T00:00:00+00:00")
        warnings: list[str] = []
        points = collect_run_points(runs, warnings)
        assert len(points) == 1
        assert any("skipped" in w.lower() for w in warnings)


class TestGateApproximation:
    def test_critical_fails(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        _write_run(
            runs / "RUN-001.json",
            "RUN-001",
            "2026-01-01T00:00:00+00:00",
            critical=1,
        )
        points = collect_run_points(runs)
        assert points[0].gate_result == "fail"
        assert points[0].gate_approximated is True

    def test_within_thresholds_passes(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        _write_run(
            runs / "RUN-001.json",
            "RUN-001",
            "2026-01-01T00:00:00+00:00",
            medium=5,
        )
        points = collect_run_points(runs)
        assert points[0].gate_result == "pass"

    def test_high_over_threshold_fails(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        _write_run(
            runs / "RUN-001.json",
            "RUN-001",
            "2026-01-01T00:00:00+00:00",
            high=11,
        )
        points = collect_run_points(runs)
        assert points[0].gate_result == "fail"


class TestCategoryData:
    def test_category_data_not_available(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        _write_run(runs / "RUN-001.json", "RUN-001", "2026-01-01T00:00:00+00:00")
        points = collect_run_points(runs)
        assert points[0].category_data_available is False
        assert points[0].category_counts == {}

    def test_readiness_always_unknown(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        _write_run(runs / "RUN-001.json", "RUN-001", "2026-01-01T00:00:00+00:00")
        points = collect_run_points(runs)
        assert points[0].readiness_status == "unknown"


class TestNoMutation:
    def test_does_not_mutate_runs(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        _write_run(runs / "RUN-001.json", "RUN-001", "2026-01-01T00:00:00+00:00")
        before = (runs / "RUN-001.json").read_text(encoding="utf-8")
        collect_run_points(runs)
        after = (runs / "RUN-001.json").read_text(encoding="utf-8")
        assert before == after
