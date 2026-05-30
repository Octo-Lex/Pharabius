"""Executable finding-quality rubric (v3.6.0).

Defines weighted criteria for evaluating whether findings are useful
or noisy. Each criterion is a callable evaluator, not a string description.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class RubricCriterion:
    """A single quality criterion with an executable evaluator."""

    name: str
    description: str
    weight: int
    evaluator: Callable[[dict, list[dict]], bool]


# ── Evaluator functions ───────────────────────────────────────────────


def has_specific_action(finding: dict, all_findings: list[dict]) -> bool:
    """Finding recommends a concrete action (≥20 chars, not vague)."""
    action = str(finding.get("recommended_action") or "").strip()
    if len(action) < 20:
        return False
    vague = {"review", "fix", "refactor", "update", "change", "improve"}
    return action.lower() not in vague


def has_evidence_link(finding: dict, all_findings: list[dict]) -> bool:
    """Finding has at least one evidence ID."""
    ids = finding.get("evidence_ids") or []
    return len(ids) > 0


def is_not_duplicate(finding: dict, all_findings: list[dict]) -> bool:
    """No other finding shares the same category + location + title prefix."""
    cat = finding.get("category", "")
    locs = finding.get("locations", [])
    title = str(finding.get("title", ""))[:50]
    for other in all_findings:
        if other is finding:
            continue
        if (
            other.get("category") == cat
            and other.get("locations") == locs
            and str(other.get("title", ""))[:50] == title
        ):
            return False
    return True


def is_not_trivial(finding: dict, all_findings: list[dict]) -> bool:
    """Finding has risk_score > 5 or High+ severity."""
    score = int(finding.get("risk_score", 0) or 0)
    severity = str(finding.get("severity", ""))
    return score > 5 or severity in ("High", "Critical")


def has_specific_location(finding: dict, all_findings: list[dict]) -> bool:
    """Finding has at least one non-empty location."""
    locs = finding.get("locations") or []
    return any(loc.strip() for loc in locs if isinstance(loc, str))


# ── Rubric definition ─────────────────────────────────────────────────

RUBRIC_CRITERIA: list[RubricCriterion] = [
    RubricCriterion(
        name="actionable",
        description="Finding suggests a concrete remediation step",
        weight=3,
        evaluator=has_specific_action,
    ),
    RubricCriterion(
        name="evidence_linked",
        description="Finding has at least one evidence ID",
        weight=2,
        evaluator=has_evidence_link,
    ),
    RubricCriterion(
        name="not_duplicate",
        description="No other finding has same category + location + title prefix",
        weight=2,
        evaluator=is_not_duplicate,
    ),
    RubricCriterion(
        name="not_trivial",
        description="Finding risk_score > 5 or High+ severity",
        weight=1,
        evaluator=is_not_trivial,
    ),
    RubricCriterion(
        name="specific_location",
        description="Finding has at least one non-empty location",
        weight=1,
        evaluator=has_specific_location,
    ),
]


# ── Scoring ───────────────────────────────────────────────────────────


def score_finding(finding: dict, all_findings: list[dict]) -> float:
    """Score a finding 0–1.0 on the rubric. Higher is better."""
    total_weight = sum(c.weight for c in RUBRIC_CRITERIA)
    if total_weight == 0:
        return 0.0
    earned = sum(c.weight for c in RUBRIC_CRITERIA if c.evaluator(finding, all_findings))
    return earned / total_weight


def compute_fixture_quality(findings: list[dict]) -> dict[str, Any]:
    """Compute aggregate quality metrics for a fixture's findings."""
    if not findings:
        return {"average_quality": 0.0, "noise_rate": 0.0, "total": 0}

    scores = [score_finding(f, findings) for f in findings]
    noise_count = sum(1 for s in scores if s < 0.4)

    return {
        "average_quality": round(sum(scores) / len(scores), 3),
        "noise_rate": round(noise_count / len(scores), 3),
        "total": len(findings),
        "scores": scores,
    }


# ── Quality targets per fixture type ──────────────────────────────────

QUALITY_TARGETS: dict[str, dict[str, float]] = {
    "clean-baseline": {"min_quality": 0.8, "max_noise": 0.10},
    "small-python-package": {"min_quality": 0.7, "max_noise": 0.15},
    "small-node-package": {"min_quality": 0.7, "max_noise": 0.15},
    "medium-python-service": {"min_quality": 0.6, "max_noise": 0.20},
    "medium-node-app": {"min_quality": 0.6, "max_noise": 0.20},
    "mixed-python-node": {"min_quality": 0.6, "max_noise": 0.20},
    "coverage-heavy": {"min_quality": 0.6, "max_noise": 0.20},
    "poor-hygiene": {"min_quality": 0.5, "max_noise": 0.25},
}
