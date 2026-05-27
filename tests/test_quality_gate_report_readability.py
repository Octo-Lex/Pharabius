"""Tests for quality gate report readability (v2.0.1 S03)."""

from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.quality_gate import evaluate_quality_gate, render_quality_gate_markdown


def _write_register(path: Path, findings: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema_version": "1.0", "findings": findings}),
        encoding="utf-8",
    )


def _f(sev: str = "Medium") -> dict:
    return {
        "id": "TD-DEP-001",
        "category": "TD-DEP",
        "title": "Test",
        "description": "Test",
        "severity": sev,
        "confidence": "High",
        "evidence_ids": ["EVD-001"],
        "locations": [{"file": "test.py", "line": 1}],
    }


class TestReportStructure:
    def test_pass_report_has_result_heading(self, tmp_path: Path) -> None:
        dr = tmp_path / ".ai-debt" / "debt-register.json"
        _write_register(dr, [])
        result = evaluate_quality_gate(dr)
        md = render_quality_gate_markdown(result)
        assert "## Result:" in md
        assert "PASS" in md

    def test_fail_report_has_result_heading(self, tmp_path: Path) -> None:
        dr = tmp_path / ".ai-debt" / "debt-register.json"
        _write_register(dr, [_f("Critical")])
        result = evaluate_quality_gate(dr)
        md = render_quality_gate_markdown(result)
        assert "## Result:" in md
        assert "FAIL" in md

    def test_fail_report_has_blocking_violations(self, tmp_path: Path) -> None:
        dr = tmp_path / ".ai-debt" / "debt-register.json"
        _write_register(dr, [_f("Critical")])
        result = evaluate_quality_gate(dr)
        md = render_quality_gate_markdown(result)
        assert "Blocking Violations" in md

    def test_pass_report_no_blocking_violations(self, tmp_path: Path) -> None:
        dr = tmp_path / ".ai-debt" / "debt-register.json"
        _write_register(dr, [])
        result = evaluate_quality_gate(dr)
        md = render_quality_gate_markdown(result)
        assert "Blocking Violations" not in md

    def test_report_has_rule_summary_table(self, tmp_path: Path) -> None:
        dr = tmp_path / ".ai-debt" / "debt-register.json"
        _write_register(dr, [])
        result = evaluate_quality_gate(dr)
        md = render_quality_gate_markdown(result)
        assert "Rule Summary" in md
        assert "| Rule |" in md

    def test_report_has_severity_counts(self, tmp_path: Path) -> None:
        dr = tmp_path / ".ai-debt" / "debt-register.json"
        _write_register(dr, [_f("High"), _f("Medium")])
        result = evaluate_quality_gate(dr)
        md = render_quality_gate_markdown(result)
        assert "Severity Counts" in md
        assert "High" in md
        assert "Medium" in md

    def test_report_has_ci_exit_behavior(self, tmp_path: Path) -> None:
        dr = tmp_path / ".ai-debt" / "debt-register.json"
        _write_register(dr, [])
        result = evaluate_quality_gate(dr)
        md = render_quality_gate_markdown(result)
        assert "CI Exit Behavior" in md

    def test_report_has_safety_boundary(self, tmp_path: Path) -> None:
        dr = tmp_path / ".ai-debt" / "debt-register.json"
        _write_register(dr, [])
        result = evaluate_quality_gate(dr)
        md = render_quality_gate_markdown(result)
        assert "Safety Boundary" in md

    def test_report_has_recommended_actions(self, tmp_path: Path) -> None:
        dr = tmp_path / ".ai-debt" / "debt-register.json"
        _write_register(dr, [])
        result = evaluate_quality_gate(dr)
        md = render_quality_gate_markdown(result)
        assert "Recommended Actions" in md

    def test_fail_report_recommends_fix(self, tmp_path: Path) -> None:
        dr = tmp_path / ".ai-debt" / "debt-register.json"
        _write_register(dr, [_f("Critical")])
        result = evaluate_quality_gate(dr)
        md = render_quality_gate_markdown(result)
        assert "blocking violations" in md.lower()


class TestReportDeterminism:
    def test_same_input_same_output(self, tmp_path: Path) -> None:
        dr = tmp_path / ".ai-debt" / "debt-register.json"
        _write_register(dr, [_f("Medium")])
        result = evaluate_quality_gate(dr)
        md1 = render_quality_gate_markdown(result)
        md2 = render_quality_gate_markdown(result)
        assert md1 == md2

    def test_gate_decision_unchanged(self, tmp_path: Path) -> None:
        """Rendering does not affect gate decision."""
        dr = tmp_path / ".ai-debt" / "debt-register.json"
        _write_register(dr, [_f("Critical")])
        result = evaluate_quality_gate(dr)
        assert result.result == "FAIL"
        assert result.exit_code == 1
        render_quality_gate_markdown(result)
        assert result.result == "FAIL"
        assert result.exit_code == 1
