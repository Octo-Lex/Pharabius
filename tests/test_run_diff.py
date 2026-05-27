"""Tests for run diff engine and CLI (W53-S03)."""

from __future__ import annotations

import json
from pathlib import Path

import typer.testing

from pharabius.cli import app
from pharabius.core.differ import compute_run_diff, find_latest_runs

runner = typer.testing.CliRunner()


def _write_register(path: Path, findings: list[dict], run_id: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {"schema_version": "1.0", "findings": findings}
    if run_id:
        data["run_id"] = run_id
    path.write_text(json.dumps(data), encoding="utf-8")


def _f(fid: str, sev: str = "Medium", conf: str = "High") -> dict:
    return {
        "id": fid,
        "category": "TD-DEP",
        "title": "Test",
        "description": "Test",
        "severity": sev,
        "confidence": conf,
        "evidence_ids": ["EVD-001"],
        "locations": [{"file": "test.py", "line": 1}],
    }


class TestDiffEngine:
    def test_detects_new_findings(self, tmp_path: Path) -> None:
        before = tmp_path / "before.json"
        after = tmp_path / "after.json"
        _write_register(before, [_f("TD-001")], "RUN-1")
        _write_register(after, [_f("TD-001"), _f("TD-002")], "RUN-2")
        diff = compute_run_diff(before, after)
        assert "TD-002" in diff.new_findings
        assert diff.summary.new_count == 1

    def test_detects_resolved_findings(self, tmp_path: Path) -> None:
        before = tmp_path / "before.json"
        after = tmp_path / "after.json"
        _write_register(before, [_f("TD-001"), _f("TD-002")], "RUN-1")
        _write_register(after, [_f("TD-001")], "RUN-2")
        diff = compute_run_diff(before, after)
        assert "TD-002" in diff.resolved_findings
        assert diff.summary.resolved_count == 1

    def test_detects_severity_changes(self, tmp_path: Path) -> None:
        before = tmp_path / "before.json"
        after = tmp_path / "after.json"
        _write_register(before, [_f("TD-001", sev="Medium")], "RUN-1")
        _write_register(after, [_f("TD-001", sev="High")], "RUN-2")
        diff = compute_run_diff(before, after)
        assert len(diff.severity_changes) == 1
        assert diff.severity_changes[0].from_value == "Medium"
        assert diff.severity_changes[0].to_value == "High"

    def test_detects_confidence_changes(self, tmp_path: Path) -> None:
        before = tmp_path / "before.json"
        after = tmp_path / "after.json"
        _write_register(before, [_f("TD-001", conf="Low")], "RUN-1")
        _write_register(after, [_f("TD-001", conf="High")], "RUN-2")
        diff = compute_run_diff(before, after)
        assert len(diff.confidence_changes) == 1

    def test_empty_diff_when_identical(self, tmp_path: Path) -> None:
        before = tmp_path / "before.json"
        after = tmp_path / "after.json"
        _write_register(before, [_f("TD-001")], "RUN-1")
        _write_register(after, [_f("TD-001")], "RUN-2")
        diff = compute_run_diff(before, after)
        assert diff.new_findings == []
        assert diff.resolved_findings == []
        assert diff.severity_changes == []
        assert diff.summary.net_change == 0

    def test_missing_before_file(self, tmp_path: Path) -> None:
        import pytest

        after = tmp_path / "after.json"
        _write_register(after, [_f("TD-001")], "RUN-2")
        with pytest.raises(FileNotFoundError):
            compute_run_diff(tmp_path / "missing.json", after)

    def test_net_change_calculation(self, tmp_path: Path) -> None:
        before = tmp_path / "before.json"
        after = tmp_path / "after.json"
        _write_register(before, [_f("TD-001"), _f("TD-002")], "RUN-1")
        _write_register(
            after, [_f("TD-001"), _f("TD-003"), _f("TD-004")], "RUN-2"
        )
        diff = compute_run_diff(before, after)
        assert diff.summary.net_change == 1  # 2 → 3


class TestFindLatestRuns:
    def test_finds_two_latest(self, tmp_path: Path) -> None:
        runs = tmp_path / ".ai-debt" / "runs"
        runs.mkdir(parents=True)
        (runs / "RUN-001.json").write_text("{}", encoding="utf-8")
        (runs / "RUN-002.json").write_text("{}", encoding="utf-8")
        result = find_latest_runs(tmp_path / ".ai-debt")
        assert result is not None
        assert result[0].name == "RUN-001.json"
        assert result[1].name == "RUN-002.json"

    def test_returns_none_with_one_run(self, tmp_path: Path) -> None:
        runs = tmp_path / ".ai-debt" / "runs"
        runs.mkdir(parents=True)
        (runs / "RUN-001.json").write_text("{}", encoding="utf-8")
        assert find_latest_runs(tmp_path / ".ai-debt") is None


class TestCLIDiff:
    def test_diff_before_after(self, tmp_path: Path) -> None:
        before = tmp_path / "before.json"
        after = tmp_path / "after.json"
        _write_register(before, [_f("TD-001")], "RUN-1")
        _write_register(after, [_f("TD-001"), _f("TD-002")], "RUN-2")
        result = runner.invoke(
            app,
            ["diff", "--before", str(before), "--after", str(after)],
        )
        assert result.exit_code == 0
        assert "RUN-1" in result.output
        assert "TD-002" in result.output

    def test_diff_json(self, tmp_path: Path) -> None:
        before = tmp_path / "before.json"
        after = tmp_path / "after.json"
        _write_register(before, [_f("TD-001")], "RUN-1")
        _write_register(after, [_f("TD-001"), _f("TD-002")], "RUN-2")
        result = runner.invoke(
            app,
            ["diff", "--before", str(before), "--after", str(after), "--json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["schema_version"] == "1.0"
        assert "TD-002" in data["new_findings"]

    def test_diff_missing_args(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["diff", "-r", str(tmp_path)])
        assert result.exit_code == 1
