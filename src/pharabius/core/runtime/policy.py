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
    RuntimeSourceGrade,
    RuntimeSourceType,
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


def is_deterministic_project_pin(evidence: RuntimeEvidence) -> bool:
    """Is this evidence a deterministic reproducibility pin?"""
    return evidence.constraint.kind == RuntimeConstraintKind.EXACT and evidence.source_grade in {
        RuntimeSourceGrade.LOCKFILE,
        RuntimeSourceGrade.TOOL_PIN,
        RuntimeSourceGrade.VERSION_FILE,
        RuntimeSourceGrade.MANIFEST_PIN,
    }


def is_manifest_compatibility_range(evidence: RuntimeEvidence) -> bool:
    """Is this evidence a manifest compatibility range?"""
    return evidence.source_grade == RuntimeSourceGrade.MANIFEST_RANGE


# ── Pin-quality predicate ────────────────────────────────────────────

# Non-pin source details: compatibility baselines, minimum versions, targets
_NON_PIN_SOURCE_DETAILS: set[str] = {
    "go-directive",  # go.mod go directive: compatibility baseline
    "target-framework",  # .csproj TargetFramework: compatibility target
    "rust-version",  # Cargo.toml rust-version: minimum, not pin
}


def is_runtime_pin(evidence: RuntimeEvidence) -> bool:
    """Determine whether evidence counts as a runtime reproducibility pin.

    Compatibility baselines and minimum versions are NOT pins.
    Only exact versions from pin-grade sources count.

    Pin-quality rules:
    - EXACT from version_file, tool_versions, or manifest → pin (with exceptions)
    - RANGE → never a pin
    - UNKNOWN → never a pin
    - Source-specific exceptions: go-directive, target-framework, rust-version
    """
    # UNKNOWN evidence is detected but not pinned
    if evidence.constraint.kind == RuntimeConstraintKind.UNKNOWN:
        return False

    # RANGE evidence is never a full pin
    if evidence.constraint.kind == RuntimeConstraintKind.RANGE:
        return False

    # EXACT evidence — check source-specific exceptions
    if evidence.constraint.kind == RuntimeConstraintKind.EXACT:
        # Non-pin source details override EXACT status
        if evidence.source_detail and evidence.source_detail in _NON_PIN_SOURCE_DETAILS:
            return False
        # Container and CI pins are scoped pins, not project-level pins
        if evidence.source_type in (RuntimeSourceType.CONTAINER, RuntimeSourceType.CI):
            return False
        return True

    # MISSING, UNPINNED → not pins
    return False
