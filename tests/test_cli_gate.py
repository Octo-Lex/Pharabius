"""Tests for ai-debt gate CLI command (W53-S02 + v2.0.1 correction)."""

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
        result = runner.invoke(app, ["gate", "-r", str(tmp_path), "--max-critical", "1"])
        assert result.exit_code == 0

    def test_override_max_high(self, tmp_path: Path) -> None:
        findings = [_finding(severity="High") for _ in range(5)]
        _write_debt_register(tmp_path / ".ai-debt" / "debt-register.json", findings)
        result = runner.invoke(app, ["gate", "-r", str(tmp_path), "--max-high", "3"])
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


class TestGateMarkdownReport:
    """Gate writes .ai-debt/reports/quality-gate.md."""

    def test_pass_writes_quality_gate_md(self, tmp_path: Path) -> None:
        _write_debt_register(tmp_path / ".ai-debt" / "debt-register.json", [])
        runner.invoke(app, ["gate", "-r", str(tmp_path)])
        md_path = tmp_path / ".ai-debt" / "reports" / "quality-gate.md"
        assert md_path.exists()

    def test_fail_writes_quality_gate_md(self, tmp_path: Path) -> None:
        _write_debt_register(
            tmp_path / ".ai-debt" / "debt-register.json",
            [_finding(severity="Critical")],
        )
        runner.invoke(app, ["gate", "-r", str(tmp_path)])
        md_path = tmp_path / ".ai-debt" / "reports" / "quality-gate.md"
        assert md_path.exists()

    def test_pass_markdown_has_result_heading(self, tmp_path: Path) -> None:
        _write_debt_register(tmp_path / ".ai-debt" / "debt-register.json", [])
        runner.invoke(app, ["gate", "-r", str(tmp_path)])
        md = (tmp_path / ".ai-debt" / "reports" / "quality-gate.md").read_text(encoding="utf-8")
        assert "PASS" in md
        assert "## Result:" in md

    def test_fail_markdown_has_blocking_violations(self, tmp_path: Path) -> None:
        _write_debt_register(
            tmp_path / ".ai-debt" / "debt-register.json",
            [_finding(severity="Critical")],
        )
        runner.invoke(app, ["gate", "-r", str(tmp_path)])
        md = (tmp_path / ".ai-debt" / "reports" / "quality-gate.md").read_text(encoding="utf-8")
        assert "FAIL" in md
        assert "Blocking Violations" in md

    def test_markdown_has_recommended_actions(self, tmp_path: Path) -> None:
        _write_debt_register(tmp_path / ".ai-debt" / "debt-register.json", [])
        runner.invoke(app, ["gate", "-r", str(tmp_path)])
        md = (tmp_path / ".ai-debt" / "reports" / "quality-gate.md").read_text(encoding="utf-8")
        assert "Recommended Actions" in md

    def test_markdown_has_safety_boundary(self, tmp_path: Path) -> None:
        _write_debt_register(tmp_path / ".ai-debt" / "debt-register.json", [])
        runner.invoke(app, ["gate", "-r", str(tmp_path)])
        md = (tmp_path / ".ai-debt" / "reports" / "quality-gate.md").read_text(encoding="utf-8")
        assert "Safety Boundary" in md

    def test_markdown_is_deterministic(self, tmp_path: Path) -> None:
        _write_debt_register(
            tmp_path / ".ai-debt" / "debt-register.json",
            [_finding(severity="Medium")],
        )
        runner.invoke(app, ["gate", "-r", str(tmp_path)])
        md1 = (tmp_path / ".ai-debt" / "reports" / "quality-gate.md").read_text(encoding="utf-8")
        runner.invoke(app, ["gate", "-r", str(tmp_path)])
        md2 = (tmp_path / ".ai-debt" / "reports" / "quality-gate.md").read_text(encoding="utf-8")
        assert md1 == md2

    def test_missing_debt_register_still_writes_report(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["gate", "-r", str(tmp_path)])
        assert result.exit_code == 1
        md_path = tmp_path / ".ai-debt" / "reports" / "quality-gate.md"
        assert md_path.exists()
        md = md_path.read_text(encoding="utf-8")
        assert "FAIL" in md


class TestGateArtifactBoundary:
    """Gate only writes to .ai-debt/reports/, never mutates canonical files."""

    def test_does_not_modify_debt_register(self, tmp_path: Path) -> None:
        dr = tmp_path / ".ai-debt" / "debt-register.json"
        _write_debt_register(dr, [])
        before = dr.read_text(encoding="utf-8")
        runner.invoke(app, ["gate", "-r", str(tmp_path)])
        after = dr.read_text(encoding="utf-8")
        assert before == after
