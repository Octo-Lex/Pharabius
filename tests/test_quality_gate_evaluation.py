"""Tests for quality gate evaluation engine (W53-S01)."""

from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.quality_gate import evaluate_quality_gate, get_default_gate_config
from pharabius.schemas.quality_gate import QualityGateThresholds


def _write_debt_register(path: Path, findings: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema_version": "1.0", "findings": findings}),
        encoding="utf-8",
    )


def _finding(
    fid: str = "TD-DEP-001",
    category: str = "TD-DEP",
    severity: str = "Medium",
    confidence: str = "High",
) -> dict:
    return {
        "id": fid,
        "category": category,
        "title": "Test finding",
        "description": "Test",
        "severity": severity,
        "confidence": confidence,
        "evidence_ids": ["EVD-001"],
        "locations": [{"file": "test.py", "line": 1}],
    }


class TestEvaluationPass:
    def test_pass_with_zero_findings(self, tmp_path: Path) -> None:
        reg = tmp_path / ".ai-debt" / "debt-register.json"
        _write_debt_register(reg, [])
        result = evaluate_quality_gate(reg)
        assert result.result == "PASS"
        assert result.exit_code == 0
        assert result.failed_rules == []

    def test_pass_with_findings_within_thresholds(self, tmp_path: Path) -> None:
        reg = tmp_path / ".ai-debt" / "debt-register.json"
        findings = [_finding(fid=f"TD-DEP-{i:03d}", severity="Medium") for i in range(5)]
        _write_debt_register(reg, findings)
        result = evaluate_quality_gate(reg)
        assert result.result == "PASS"
        assert result.exit_code == 0

    def test_pass_with_high_within_limit(self, tmp_path: Path) -> None:
        reg = tmp_path / ".ai-debt" / "debt-register.json"
        findings = [_finding(fid=f"TD-DEP-{i:03d}", severity="High") for i in range(10)]
        _write_debt_register(reg, findings)
        result = evaluate_quality_gate(reg, QualityGateThresholds(max_high=10))
        assert result.result == "PASS"


class TestEvaluationFail:
    def test_fail_critical_exceeded(self, tmp_path: Path) -> None:
        reg = tmp_path / ".ai-debt" / "debt-register.json"
        _write_debt_register(reg, [_finding(severity="Critical")])
        result = evaluate_quality_gate(reg)
        assert result.result == "FAIL"
        assert "max_critical" in result.failed_rules

    def test_fail_high_exceeded(self, tmp_path: Path) -> None:
        reg = tmp_path / ".ai-debt" / "debt-register.json"
        findings = [_finding(fid=f"TD-DEP-{i:03d}", severity="High") for i in range(11)]
        _write_debt_register(reg, findings)
        result = evaluate_quality_gate(reg)
        assert result.result == "FAIL"
        assert "max_high" in result.failed_rules

    def test_fail_total_exceeded(self, tmp_path: Path) -> None:
        reg = tmp_path / ".ai-debt" / "debt-register.json"
        findings = [_finding(fid=f"TD-DEP-{i:03d}", severity="Low") for i in range(51)]
        _write_debt_register(reg, findings)
        result = evaluate_quality_gate(reg)
        assert result.result == "FAIL"
        assert "max_total" in result.failed_rules

    def test_fail_blocked_category(self, tmp_path: Path) -> None:
        reg = tmp_path / ".ai-debt" / "debt-register.json"
        _write_debt_register(reg, [_finding(category="TD-SEC")])
        result = evaluate_quality_gate(
            reg,
            QualityGateThresholds(fail_on_categories=["TD-SEC"]),
        )
        assert result.result == "FAIL"
        assert "fail_on_categories" in result.failed_rules

    def test_fail_missing_debt_register(self, tmp_path: Path) -> None:
        reg = tmp_path / ".ai-debt" / "debt-register.json"
        result = evaluate_quality_gate(reg)
        assert result.result == "FAIL"
        assert "debt_register_exists" in result.failed_rules

    def test_fail_invalid_json(self, tmp_path: Path) -> None:
        reg = tmp_path / ".ai-debt" / "debt-register.json"
        reg.parent.mkdir(parents=True, exist_ok=True)
        reg.write_text("not json", encoding="utf-8")
        result = evaluate_quality_gate(reg)
        assert result.result == "FAIL"
        assert "debt_register_valid" in result.failed_rules


class TestEvaluationRules:
    def test_rules_report_threshold_and_actual(self, tmp_path: Path) -> None:
        reg = tmp_path / ".ai-debt" / "debt-register.json"
        _write_debt_register(reg, [_finding(severity="Critical")])
        result = evaluate_quality_gate(reg)
        critical_rule = next(r for r in result.rules if r.rule == "max_critical")
        assert critical_rule.threshold == 0
        assert critical_rule.actual == 1
        assert critical_rule.passed is False

    def test_blocked_categories_listed(self, tmp_path: Path) -> None:
        reg = tmp_path / ".ai-debt" / "debt-register.json"
        _write_debt_register(
            reg,
            [_finding(category="TD-SEC"), _finding(category="TD-DEP")],
        )
        result = evaluate_quality_gate(
            reg,
            QualityGateThresholds(fail_on_categories=["TD-SEC", "TD-ARCH"]),
        )
        cat_rule = next(r for r in result.rules if r.rule == "fail_on_categories")
        assert cat_rule.categories == ["TD-SEC"]


class TestDefaultConfig:
    def test_get_default_config(self) -> None:
        config = get_default_gate_config()
        assert config.schema_version == "1.0"
        assert config.enabled is True
        assert config.thresholds.max_critical == 0
