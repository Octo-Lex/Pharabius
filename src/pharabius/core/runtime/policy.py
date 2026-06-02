"""Runtime signal promotion policy.

Centralizes the decision of what becomes a finding, advisory, or informational signal.
Consumes RuntimeEvidence and RuntimeConflictGroup; produces RuntimeSignalAction.
"""

from __future__ import annotations

from pharabius.core.runtime.models import (
    Confidence,
    RuntimeConflictGroup,
    RuntimeConstraintKind,
    RuntimeEvidence,
    RuntimeSignalAction,
    RuntimeSignalClassification,
    Severity,
)


def classify_conflict(conflict: RuntimeConflictGroup) -> RuntimeSignalAction:
    """Classify a runtime conflict as a finding."""
    return RuntimeSignalAction(
        classification=RuntimeSignalClassification.FINDING,
        issue_type="technical_debt",
        severity=Severity.MEDIUM,
        confidence=Confidence.HIGH,
        category="TD-DEP",
    )


def classify_missing_pin(evidence: list[RuntimeEvidence]) -> RuntimeSignalAction:
    """Classify a missing runtime pin as an advisory."""
    return RuntimeSignalAction(
        classification=RuntimeSignalClassification.ADVISORY,
        issue_type="advisory",
        severity=Severity.LOW,
        confidence=Confidence.LOW,
        category="TD-DEP",
    )


def classify_evidence(evidence: RuntimeEvidence) -> RuntimeSignalClassification:
    """Classify a single runtime evidence item (pinned, container, CI, etc.).

    Informational unless it triggers a conflict or missing-pin advisory.
    """
    if evidence.constraint.kind == RuntimeConstraintKind.MISSING:
        return RuntimeSignalClassification.ADVISORY
    if evidence.constraint.kind == RuntimeConstraintKind.UNPINNED:
        return RuntimeSignalClassification.ADVISORY
    return RuntimeSignalClassification.INFORMATIONAL
