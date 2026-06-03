"""Signal governance invariants.

Named, documented platform rules that govern signal behavior.
These are hard rules, not runtime-configurable.
"""

from __future__ import annotations

from dataclasses import dataclass


class SignalValidationSeverity:
    """Severity levels for invariant violations and diagnostics."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class SignalInvariant:
    """A named governance invariant."""
    code: str
    title: str
    description: str
    severity: str  # SignalValidationSeverity value


INV_001_FINDING_ONLY_CREATES_FINDING = SignalInvariant(
    code="INV_001",
    title="FINDING disposition is the only source of technical debt findings",
    description=(
        "Only signals with SignalDisposition.FINDING may create entries "
        "in the technical debt register. ADVISORY, INFORMATIONAL, and "
        "SUPPRESSED signals must never produce findings."
    ),
    severity=SignalValidationSeverity.CRITICAL,
)

INV_002_ADVISORY_NEVER_CREATES_WORK_PACKAGE = SignalInvariant(
    code="INV_002",
    title="ADVISORY disposition never creates work packages",
    description=(
        "Advisory signals are reportable but not actionable through "
        "work packages. Only FINDING disposition is work-package-eligible."
    ),
    severity=SignalValidationSeverity.CRITICAL,
)

INV_003_INFORMATIONAL_NON_ACTIONABLE = SignalInvariant(
    code="INV_003",
    title="INFORMATIONAL signals are non-actionable",
    description=(
        "Informational signals provide context and coverage visibility. "
        "They do not create findings, advisories, or work packages. "
        "They appear in summaries but not in detailed report sections."
    ),
    severity=SignalValidationSeverity.CRITICAL,
)

INV_004_SUPPRESSED_DIAGNOSTIC_ONLY = SignalInvariant(
    code="INV_004",
    title="SUPPRESSED signals are diagnostics-only",
    description=(
        "Suppressed signals do not appear in normal report details or "
        "summaries. They are available only through diagnostic/diagnostics-enabled "
        "paths. They never create findings, advisories, or work packages."
    ),
    severity=SignalValidationSeverity.CRITICAL,
)

INV_005_SIGNAL_ID_DETERMINISTIC = SignalInvariant(
    code="INV_005",
    title="Signal IDs are deterministic",
    description=(
        "Signal IDs are produced by make_signal_id() and follow the format "
        "SIG-{FAMILY}-{hex12}. Same input always produces the same ID."
    ),
    severity=SignalValidationSeverity.WARNING,
)

INV_006_PROMOTED_FINDING_HAS_EVIDENCE = SignalInvariant(
    code="INV_006",
    title="FINDING signals must include evidence IDs",
    description=(
        "Every FINDING signal must carry at least one evidence_id. "
        "Findings without evidence are unverifiable and should not be promoted."
    ),
    severity=SignalValidationSeverity.CRITICAL,
)

INV_007_MIGRATED_ANALYZER_USES_POLICY = SignalInvariant(
    code="INV_007",
    title="Migrated analyzers use signal policy helpers",
    description=(
        "Analyzer functions that produce governed signals must use "
        "should_create_finding(), should_create_advisory(), or output_behavior() "
        "for promotion decisions. They must not branch directly on "
        "issue_type strings or use should_create_work_package() as an advisory proxy."
    ),
    severity=SignalValidationSeverity.CRITICAL,
)

INV_008_SUMMARY_COUNTS_GOVERNED_SIGNALS = SignalInvariant(
    code="INV_008",
    title="Signal summaries count governed signal instances",
    description=(
        "Run-history and report signal summaries are built from "
        "GovernedSignal instances via build_signal_summary(), not from "
        "raw evidence type heuristics."
    ),
    severity=SignalValidationSeverity.WARNING,
)


ALL_INVARIANTS: list[SignalInvariant] = [
    INV_001_FINDING_ONLY_CREATES_FINDING,
    INV_002_ADVISORY_NEVER_CREATES_WORK_PACKAGE,
    INV_003_INFORMATIONAL_NON_ACTIONABLE,
    INV_004_SUPPRESSED_DIAGNOSTIC_ONLY,
    INV_005_SIGNAL_ID_DETERMINISTIC,
    INV_006_PROMOTED_FINDING_HAS_EVIDENCE,
    INV_007_MIGRATED_ANALYZER_USES_POLICY,
    INV_008_SUMMARY_COUNTS_GOVERNED_SIGNALS,
]
