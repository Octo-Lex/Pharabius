"""Quality gate evaluation engine.

Reads debt-register.json and evaluates configurable thresholds.
Deterministic, read-only, no network access.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from pharabius.schemas.quality_gate import (
    QualityGateConfig,
    QualityGateResult,
    QualityGateRuleResult,
    QualityGateThresholds,
)

SEVERITY_ORDER = ["Critical", "High", "Medium", "Low", "Info"]


def _count_by_severity(findings: list[dict[str, object]]) -> dict[str, int]:
    """Count findings by severity level."""
    counts: dict[str, int] = dict.fromkeys(SEVERITY_ORDER, 0)
    for f in findings:
        sev = cast(str, f.get("severity", "Info"))
        if sev in counts:
            counts[sev] += 1
        else:
            counts["Info"] += 1
    return counts


def _count_by_category(findings: list[dict[str, object]]) -> dict[str, int]:
    """Count findings by category."""
    counts: dict[str, int] = {}
    for f in findings:
        cat = cast(str, f.get("category", "unknown"))
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def evaluate_quality_gate(
    debt_register_path: Path,
    thresholds: QualityGateThresholds | None = None,
) -> QualityGateResult:
    """Evaluate quality gate against a debt register.

    Args:
        debt_register_path: Path to debt-register.json
        thresholds: Threshold model (uses defaults if None)

    Returns:
        QualityGateResult with pass/fail and rule details
    """
    if thresholds is None:
        thresholds = QualityGateThresholds()

    # Read debt register
    if not debt_register_path.exists():
        return QualityGateResult(
            result="FAIL",
            exit_code=1,
            thresholds=thresholds,
            counts={},
            category_counts={},
            rules=[
                QualityGateRuleResult(
                    rule="debt_register_exists",
                    threshold=1,
                    actual=0,
                    passed=False,
                )
            ],
            failed_rules=["debt_register_exists"],
        )

    try:
        data = json.loads(debt_register_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return QualityGateResult(
            result="FAIL",
            exit_code=1,
            thresholds=thresholds,
            counts={},
            category_counts={},
            rules=[
                QualityGateRuleResult(
                    rule="debt_register_valid",
                    threshold=1,
                    actual=0,
                    passed=False,
                )
            ],
            failed_rules=["debt_register_valid"],
        )

    findings_raw: object = data.get("findings", [])
    findings = cast(list[dict[str, object]], findings_raw)
    severity_counts = _count_by_severity(findings)
    category_counts = _count_by_category(findings)
    total = len(findings)

    rules: list[QualityGateRuleResult] = []
    failed_rules: list[str] = []

    # Rule: max_critical
    critical_actual = severity_counts.get("Critical", 0)
    critical_passed = critical_actual <= thresholds.max_critical
    rules.append(
        QualityGateRuleResult(
            rule="max_critical",
            threshold=thresholds.max_critical,
            actual=critical_actual,
            passed=critical_passed,
        )
    )
    if not critical_passed:
        failed_rules.append("max_critical")

    # Rule: max_high
    high_actual = severity_counts.get("High", 0)
    high_passed = high_actual <= thresholds.max_high
    rules.append(
        QualityGateRuleResult(
            rule="max_high",
            threshold=thresholds.max_high,
            actual=high_actual,
            passed=high_passed,
        )
    )
    if not high_passed:
        failed_rules.append("max_high")

    # Rule: max_total
    total_passed = total <= thresholds.max_total
    rules.append(
        QualityGateRuleResult(
            rule="max_total",
            threshold=thresholds.max_total,
            actual=total,
            passed=total_passed,
        )
    )
    if not total_passed:
        failed_rules.append("max_total")

    # Rule: fail_on_categories
    blocked_cats = [cat for cat in thresholds.fail_on_categories if cat in category_counts]
    cat_passed = len(blocked_cats) == 0
    rules.append(
        QualityGateRuleResult(
            rule="fail_on_categories",
            threshold=0,
            actual=len(blocked_cats),
            passed=cat_passed,
            categories=blocked_cats,
        )
    )
    if not cat_passed:
        failed_rules.append("fail_on_categories")

    result = "PASS" if len(failed_rules) == 0 else "FAIL"
    exit_code = 0 if result == "PASS" else 1

    return QualityGateResult(
        result=result,
        exit_code=exit_code,
        thresholds=thresholds,
        counts=severity_counts,
        category_counts=category_counts,
        rules=rules,
        failed_rules=failed_rules,
    )


def get_default_gate_config() -> QualityGateConfig:
    """Return default quality gate configuration."""
    return QualityGateConfig()
