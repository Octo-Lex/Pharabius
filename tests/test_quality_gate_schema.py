"""Tests for quality gate schemas (W53-S01)."""

from __future__ import annotations

from pydantic import ValidationError

from pharabius.schemas.quality_gate import (
    QualityGateConfig,
    QualityGateResult,
    QualityGateThresholds,
)


class TestQualityGateThresholds:
    def test_default_thresholds(self) -> None:
        t = QualityGateThresholds()
        assert t.max_critical == 0
        assert t.max_high == 10
        assert t.max_total == 50
        assert t.fail_on_categories == []

    def test_custom_thresholds(self) -> None:
        t = QualityGateThresholds(max_critical=1, max_high=5, max_total=20)
        assert t.max_critical == 1
        assert t.max_high == 5
        assert t.max_total == 20

    def test_forbids_extra_fields(self) -> None:
        import pytest

        with pytest.raises(ValidationError):
            QualityGateThresholds(unknown_field=42)  # type: ignore[call-arg]

    def test_schema_version(self) -> None:
        c = QualityGateConfig()
        assert c.schema_version == "1.0"


class TestQualityGateConfig:
    def test_default_config_enabled(self) -> None:
        c = QualityGateConfig()
        assert c.enabled is True
        assert c.thresholds.max_critical == 0

    def test_custom_thresholds_in_config(self) -> None:
        c = QualityGateConfig(thresholds=QualityGateThresholds(max_critical=2, max_high=15))
        assert c.thresholds.max_critical == 2


class TestQualityGateResult:
    def test_pass_result(self) -> None:
        r = QualityGateResult(
            result="PASS",
            exit_code=0,
            thresholds=QualityGateThresholds(),
            counts={"Critical": 0, "High": 3},
            failed_rules=[],
        )
        assert r.exit_code == 0
        assert r.result == "PASS"

    def test_fail_result(self) -> None:
        r = QualityGateResult(
            result="FAIL",
            exit_code=1,
            thresholds=QualityGateThresholds(),
            counts={"Critical": 2, "High": 5},
            failed_rules=["max_critical"],
        )
        assert r.exit_code == 1
        assert r.failed_rules == ["max_critical"]

    def test_forbids_extra_fields(self) -> None:
        import pytest

        with pytest.raises(ValidationError):
            QualityGateResult(unknown=42)  # type: ignore[call-arg]
