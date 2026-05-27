"""Quality gate schemas.

Defines threshold model and evaluation result for CI quality gate
enforcement. Used by `ai-debt gate` command.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class QualityGateThresholds(BaseModel):
    """Configurable quality gate thresholds."""

    model_config = {"extra": "forbid"}

    max_critical: int = 0
    max_high: int = 10
    max_total: int = 50
    fail_on_categories: list[str] = Field(default_factory=list)


class QualityGateConfig(BaseModel):
    """Quality gate configuration section in config.yaml."""

    model_config = {"extra": "forbid"}

    schema_version: str = "1.0"
    thresholds: QualityGateThresholds = Field(default_factory=QualityGateThresholds)
    enabled: bool = True


class QualityGateRuleResult(BaseModel):
    """Result of a single gate rule check."""

    model_config = {"extra": "forbid"}

    rule: str
    threshold: int
    actual: int
    passed: bool
    categories: list[str] = Field(default_factory=list)


class QualityGateResult(BaseModel):
    """Full quality gate evaluation result."""

    model_config = {"extra": "forbid"}

    schema_version: str = "1.0"
    result: str  # "PASS" or "FAIL"
    exit_code: int  # 0 for PASS, 1 for FAIL
    thresholds: QualityGateThresholds
    counts: dict[str, int] = Field(default_factory=dict)
    category_counts: dict[str, int] = Field(default_factory=dict)
    rules: list[QualityGateRuleResult] = Field(default_factory=list)
    failed_rules: list[str] = Field(default_factory=list)
