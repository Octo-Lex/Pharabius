"""Tests for ai-debt trend CLI command (v2.1.0 S04)."""

from __future__ import annotations

import json
from pathlib import Path

import typer.testing

from pharabius.cli import app
from pharabius.schemas.run_metadata import RunMetadata, RunSummary

runner = typer.testing.CliRunner()


def _write_run(
    runs_dir: Path, run_id: str, timestamp: str, critical: int = 0, high: int = 0
) -> None:
    runs_dir.mkdir(parents=True, exist_ok=True)
    summary = RunSummary(
        critical_findings=critical,
        high_findings=high,
        medium_findings=2,
        low_findings=1,
    )
    meta = RunMetadata(run_id=run_id, timestamp=timestamp, summary=summary)
    (runs_dir / f"{run_id}.json").write_text(meta.model_dump_json(indent=2), encoding="utf-8")


class TestTrendBasic:
    def test_no_runs_exit_0(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["trend", "-r", str(tmp_path)])
        assert result.exit_code == 0
        assert "insufficient_data" in result.output

    def test_single_run_exit_0(self, tmp_path: Path) -> None:
        runs = tmp_path / ".ai-debt" / "runs"
        _write_run(runs, "RUN-001", "2026-01-01T00:00:00+00:00")
        result = runner.invoke(app, ["trend", "-r", str(tmp_path)])
        assert result.exit_code == 0
        assert "insufficient_data" in result.output

    def test_two_runs_trajectory(self, tmp_path: Path) -> None:
        runs = tmp_path / ".ai-debt" / "runs"
        _write_run(runs, "RUN-001", "2026-01-01T00:00:00+00:00", critical=2)
        _write_run(runs, "RUN-002", "2026-01-02T00:00:00+00:00", critical=0)
        result = runner.invoke(app, ["trend", "-r", str(tmp_path)])
        assert result.exit_code == 0
        assert "improving" in result.output


class TestTrendOutput:
    def test_json_output_written(self, tmp_path: Path) -> None:
        runs = tmp_path / ".ai-debt" / "runs"
        _write_run(runs, "RUN-001", "2026-01-01T00:00:00+00:00", critical=1)
        _write_run(runs, "RUN-002", "2026-01-02T00:00:00+00:00", critical=0)
        runner.invoke(app, ["trend", "-r", str(tmp_path)])
        json_path = tmp_path / ".ai-debt" / "trends" / "trend-summary.json"
        assert json_path.exists()
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.0"
        assert data["trajectory"] == "improving"

    def test_markdown_output_written(self, tmp_path: Path) -> None:
        runs = tmp_path / ".ai-debt" / "runs"
        _write_run(runs, "RUN-001", "2026-01-01T00:00:00+00:00")
        _write_run(runs, "RUN-002", "2026-01-02T00:00:00+00:00")
        runner.invoke(app, ["trend", "-r", str(tmp_path)])
        md_path = tmp_path / ".ai-debt" / "trends" / "trend-summary.md"
        assert md_path.exists()
        md = md_path.read_text(encoding="utf-8")
        assert "Trajectory" in md
        assert "not a scientific measure" in md

    def test_format_json_only(self, tmp_path: Path) -> None:
        runs = tmp_path / ".ai-debt" / "runs"
        _write_run(runs, "RUN-001", "2026-01-01T00:00:00+00:00")
        _write_run(runs, "RUN-002", "2026-01-02T00:00:00+00:00")
        runner.invoke(app, ["trend", "-r", str(tmp_path), "--format", "json"])
        assert (tmp_path / ".ai-debt" / "trends" / "trend-summary.json").exists()
        assert not (tmp_path / ".ai-debt" / "trends" / "trend-summary.md").exists()


class TestTrendLastN:
    def test_last_flag_limits_runs(self, tmp_path: Path) -> None:
        runs = tmp_path / ".ai-debt" / "runs"
        _write_run(runs, "RUN-001", "2026-01-01T00:00:00+00:00", critical=5)
        _write_run(runs, "RUN-002", "2026-01-02T00:00:00+00:00", critical=3)
        _write_run(runs, "RUN-003", "2026-01-03T00:00:00+00:00", critical=1)
        result = runner.invoke(app, ["trend", "-r", str(tmp_path), "--last", "2"])
        assert result.exit_code == 0
        json_path = tmp_path / ".ai-debt" / "trends" / "trend-summary.json"
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["run_count"] == 2


class TestTrendNoMutation:
    def test_does_not_mutate_runs(self, tmp_path: Path) -> None:
        runs = tmp_path / ".ai-debt" / "runs"
        _write_run(runs, "RUN-001", "2026-01-01T00:00:00+00:00")
        _write_run(runs, "RUN-002", "2026-01-02T00:00:00+00:00")
        before1 = (runs / "RUN-001.json").read_text(encoding="utf-8")
        before2 = (runs / "RUN-002.json").read_text(encoding="utf-8")
        runner.invoke(app, ["trend", "-r", str(tmp_path)])
        assert (runs / "RUN-001.json").read_text(encoding="utf-8") == before1
        assert (runs / "RUN-002.json").read_text(encoding="utf-8") == before2
