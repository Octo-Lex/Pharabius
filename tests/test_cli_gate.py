"""Tests for ai-debt gate CLI command (W53-S02)."""

from __future__ import annotations

import json
from pathlib import Path

import typer.testing

from pharabius.cli import app

runner = typer.testing.CliRunner()


def _write_debt_register(path: Path, findings: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema_version": "1.0", "findings": findings}),
        encoding="utf-8",
    )


def _finding(severity: str = "Medium") -> dict:
    return {
        "id": "TD-DEP-001",
        "category": "TD-DEP",
        "title": "Test",
        "description": "Test",
        "severity": severity,
        "confidence": "High",
        "evidence_ids": ["EVD-001"],
        "locations": [{"file": "test.py", "line": 1}],
    }


class TestGatePass:
    def test_pass_zero_findings(self, tmp_path: Path) -> None:
        _write_debt_register(tmp_path / ".ai-debt" / "debt-register.json", [])
        result = runner.invoke(app, ["gate", "-r", str(tmp_path)])
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_pass_within_thresholds(self, tmp_path: Path) -> None:
        findings = [_finding(severity="Medium") for _ in range(5)]
        _write_debt_register(tmp_path / ".ai-debt" / "debt-register.json", findings)
        result = runner.invoke(app, ["gate", "-r", str(tmp_path)])
        assert result.exit_code == 0


class TestGateFail:
    def test_fail_critical_exceeded(self, tmp_path: Path) -> None:
        _write_debt_register(
            tmp_path / ".ai-debt" / "debt-register.json",
            [_finding(severity="Critical")],
        )
        result = runner.invoke(app, ["gate", "-r", str(tmp_path)])
        assert result.exit_code == 1
        assert "FAIL" in result.output

    def test_fail_high_exceeded(self, tmp_path: Path) -> None:
        findings = [_finding(severity="High") for _ in range(11)]
        _write_debt_register(tmp_path / ".ai-debt" / "debt-register.json", findings)
        result = runner.invoke(app, ["gate", "-r", str(tmp_path)])
        assert result.exit_code == 1

    def test_fail_total_exceeded(self, tmp_path: Path) -> None:
        findings = [_finding(severity="Low") for _ in range(51)]
        _write_debt_register(tmp_path / ".ai-debt" / "debt-register.json", findings)
        result = runner.invoke(app, ["gate", "-r", str(tmp_path)])
        assert result.exit_code == 1

    def test_fail_missing_debt_register(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["gate", "-r", str(tmp_path)])
        assert result.exit_code == 1


class TestGateCLIOverrides:
    def test_override_max_critical(self, tmp_path: Path) -> None:
        _write_debt_register(
            tmp_path / ".ai-debt" / "debt-register.json",
            [_finding(severity="Critical")],
        )
        result = runner.invoke(
            app, ["gate", "-r", str(tmp_path), "--max-critical", "1"]
        )
        assert result.exit_code == 0

    def test_override_max_high(self, tmp_path: Path) -> None:
        findings = [_finding(severity="High") for _ in range(5)]
        _write_debt_register(tmp_path / ".ai-debt" / "debt-register.json", findings)
        result = runner.invoke(
            app, ["gate", "-r", str(tmp_path), "--max-high", "3"]
        )
        assert result.exit_code == 1


class TestGateJSON:
    def test_json_output(self, tmp_path: Path) -> None:
        _write_debt_register(tmp_path / ".ai-debt" / "debt-register.json", [])
        result = runner.invoke(app, ["gate", "-r", str(tmp_path), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["result"] == "PASS"
        assert data["exit_code"] == 0
        assert data["schema_version"] == "1.0"

    def test_json_fail_output(self, tmp_path: Path) -> None:
        _write_debt_register(
            tmp_path / ".ai-debt" / "debt-register.json",
            [_finding(severity="Critical")],
        )
        result = runner.invoke(app, ["gate", "-r", str(tmp_path), "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["result"] == "FAIL"
        assert "max_critical" in data["failed_rules"]


class TestGateReadonly:
    def test_gate_does_not_modify_files(self, tmp_path: Path) -> None:
        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        _write_debt_register(ai / "debt-register.json", [])
        before = set(p.name for p in ai.iterdir())
        runner.invoke(app, ["gate", "-r", str(tmp_path)])
        after = set(p.name for p in ai.iterdir())
        assert before == after
