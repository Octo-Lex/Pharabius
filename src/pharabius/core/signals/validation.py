"""Signal governance validation and diagnostics.

Validates GovernedSignal completeness, traceability, and invariant compliance.
Internal and test-facing only in v3.15.0.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pharabius.core.signals.invariants import (
    SignalValidationSeverity,
    INV_004_SUPPRESSED_DIAGNOSTIC_ONLY,
    INV_005_SIGNAL_ID_DETERMINISTIC,
    INV_006_PROMOTED_FINDING_HAS_EVIDENCE,
)
from pharabius.core.signals.models import (
    GovernedSignal,
    SignalDisposition,
    SignalFamily,
)


# ── Validation ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SignalValidationViolation:
    """A single validation violation against a governed signal."""
    invariant_code: str
    severity: str  # SignalValidationSeverity value
    message: str


@dataclass(frozen=True)
class SignalValidationResult:
    """Result of validating a governed signal."""
    valid: bool
    violations: list[SignalValidationViolation]


_SIGNAL_ID_PATTERN = re.compile(r"^SIG-[A-Z]+-[0-9a-f]{12}$")
_VALID_SEVERITIES = {"Low", "Medium", "High"}
_VALID_CONFIDENCES = {"Low", "Medium", "High"}
_VALID_DISPOSITIONS = {d.value for d in SignalDisposition}
_VALID_FAMILIES = {f.value for f in SignalFamily}


def validate_governed_signal(signal: GovernedSignal) -> SignalValidationResult:
    """Validate a GovernedSignal for completeness and traceability.

    Returns a SignalValidationResult with any violations found.
    Does not raise — callers decide what to do with violations.
    """
    violations: list[SignalValidationViolation] = []

    def _add(code: str, severity: str, message: str) -> None:
        violations.append(SignalValidationViolation(
            invariant_code=code, severity=severity, message=message,
        ))

    # Signal ID
    if not signal.signal_id:
        _add(INV_005_SIGNAL_ID_DETERMINISTIC.code, SignalValidationSeverity.CRITICAL,
             "Signal ID is empty")
    elif not _SIGNAL_ID_PATTERN.match(signal.signal_id):
        _add(INV_005_SIGNAL_ID_DETERMINISTIC.code, SignalValidationSeverity.WARNING,
             f"Signal ID '{signal.signal_id}' does not match SIG-{{FAMILY}}-{{hex12}} format")

    # Family
    if signal.family.value not in _VALID_FAMILIES:
        _add("SIG-FAMILY", SignalValidationSeverity.CRITICAL,
             f"Invalid family: {signal.family}")

    # Kind
    if not signal.kind:
        _add("SIG-KIND", SignalValidationSeverity.CRITICAL,
             "Signal kind is empty")

    # Disposition
    if signal.disposition.value not in _VALID_DISPOSITIONS:
        _add("SIG-DISPOSITION", SignalValidationSeverity.CRITICAL,
             f"Invalid disposition: {signal.disposition}")

    # Category
    if not signal.category:
        _add("SIG-CATEGORY", SignalValidationSeverity.WARNING,
             "Signal category is empty")

    # Severity
    if not signal.severity:
        _add("SIG-SEVERITY", SignalValidationSeverity.WARNING,
             "Signal severity is empty")
    elif signal.severity not in _VALID_SEVERITIES:
        _add("SIG-SEVERITY", SignalValidationSeverity.WARNING,
             f"Non-standard severity: {signal.severity}")

    # Confidence
    if not signal.confidence:
        _add("SIG-CONFIDENCE", SignalValidationSeverity.WARNING,
             "Signal confidence is empty")
    elif signal.confidence not in _VALID_CONFIDENCES:
        _add("SIG-CONFIDENCE", SignalValidationSeverity.WARNING,
             f"Non-standard confidence: {signal.confidence}")

    # Title
    if not signal.title:
        _add("SIG-TITLE", SignalValidationSeverity.CRITICAL,
             "Signal title is empty")

    # Summary
    if not signal.summary:
        _add("SIG-SUMMARY", SignalValidationSeverity.WARNING,
             "Signal summary is empty")

    # Explanation
    if not signal.explanation:
        _add("SIG-EXPLANATION", SignalValidationSeverity.INFO,
             "Signal explanation is empty")

    # FINDING must have evidence (INV_006)
    if signal.disposition == SignalDisposition.FINDING and not signal.evidence_ids:
        _add(INV_006_PROMOTED_FINDING_HAS_EVIDENCE.code, SignalValidationSeverity.CRITICAL,
             "FINDING signal must include at least one evidence_id")

    # ADVISORY should have evidence or explicit metadata basis
    if signal.disposition == SignalDisposition.ADVISORY and not signal.evidence_ids:
        if not signal.metadata:
            _add("SIG-ADVISORY-EVIDENCE", SignalValidationSeverity.WARNING,
                 "ADVISORY signal has no evidence_ids and no metadata basis")

    # INFORMATIONAL derived from evidence should carry evidence_ids
    if signal.disposition == SignalDisposition.INFORMATIONAL:
        if not signal.evidence_ids and signal.kind.endswith("_evidence"):
            _add("SIG-INFO-EVIDENCE", SignalValidationSeverity.INFO,
                 "INFORMATIONAL evidence-derived signal has no evidence_ids")

    # SUPPRESSED should be diagnostic-only
    if signal.disposition == SignalDisposition.SUPPRESSED:
        _add(INV_004_SUPPRESSED_DIAGNOSTIC_ONLY.code, SignalValidationSeverity.INFO,
             "SUPPRESSED signal detected — diagnostic-only path")

    has_critical = any(v.severity == SignalValidationSeverity.CRITICAL for v in violations)
    return SignalValidationResult(valid=not has_critical, violations=violations)


# ── Diagnostics ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class SignalDiagnostic:
    """A diagnostic finding from signal governance analysis."""
    signal_id: str | None
    invariant_code: str
    severity: str  # SignalValidationSeverity value
    message: str
    family: str | None = None
    disposition: str | None = None


def diagnose_signal(signal: GovernedSignal) -> list[SignalDiagnostic]:
    """Run all invariant checks and return diagnostics.

    Internal and test-facing only in v3.15.0.
    """
    result = validate_governed_signal(signal)
    diagnostics: list[SignalDiagnostic] = []

    for v in result.violations:
        diagnostics.append(SignalDiagnostic(
            signal_id=signal.signal_id,
            invariant_code=v.invariant_code,
            severity=v.severity,
            message=v.message,
            family=signal.family.value,
            disposition=signal.disposition.value,
        ))

    # Additional diagnostic checks beyond basic validation

    # INV_001 check: non-FINDING that has output behavior creating a finding
    from pharabius.core.signals.policy import output_behavior
    behav = output_behavior(signal)
    if signal.disposition != SignalDisposition.FINDING and behav.creates_finding:
        diagnostics.append(SignalDiagnostic(
            signal_id=signal.signal_id,
            invariant_code="INV_001",
            severity=SignalValidationSeverity.CRITICAL,
            message="Non-FINDING signal has output behavior that would create a finding",
            family=signal.family.value,
            disposition=signal.disposition.value,
        ))

    return diagnostics
