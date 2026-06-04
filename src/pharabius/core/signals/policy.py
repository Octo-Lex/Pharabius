"""Signal promotion policy.

Centralizes how dispositions behave. These predicates are the ONLY
way the analyzer should decide what to create from a governed signal.

Important:
    - should_create_finding() controls debt-register entry creation.
    - should_create_advisory() controls advisory creation.
    - should_create_work_package() controls work-package eligibility.
    - is_reportable() controls detailed report rendering.
    - No catch-all fallback logic. Explicit disposition branching only.
"""

from __future__ import annotations

from dataclasses import dataclass

from pharabius.core.signals.models import GovernedSignal, SignalDisposition


@dataclass(frozen=True)
class SignalOutputBehavior:
    """Complete output behavior for a governed signal.

    Derived from the canonical predicate functions. Use this to avoid
    repeated branching in analyzers and tests.
    """

    creates_finding: bool
    creates_advisory: bool
    creates_work_package: bool
    appears_in_report_detail: bool
    appears_in_summary: bool
    diagnostics_only: bool


def output_behavior(signal: GovernedSignal) -> SignalOutputBehavior:
    """Derive complete output behavior from a signal's disposition.

    Mapping:
        FINDING       → finding + work_package + detail + summary
        ADVISORY      → advisory + detail + summary
        INFORMATIONAL → summary only
        SUPPRESSED    → diagnostics only (no summary, no detail)
    """
    if signal.disposition == SignalDisposition.FINDING:
        return SignalOutputBehavior(
            creates_finding=True,
            creates_advisory=False,
            creates_work_package=True,
            appears_in_report_detail=True,
            appears_in_summary=True,
            diagnostics_only=False,
        )
    elif signal.disposition == SignalDisposition.ADVISORY:
        return SignalOutputBehavior(
            creates_finding=False,
            creates_advisory=True,
            creates_work_package=False,
            appears_in_report_detail=True,
            appears_in_summary=True,
            diagnostics_only=False,
        )
    elif signal.disposition == SignalDisposition.INFORMATIONAL:
        return SignalOutputBehavior(
            creates_finding=False,
            creates_advisory=False,
            creates_work_package=False,
            appears_in_report_detail=False,
            appears_in_summary=True,
            diagnostics_only=False,
        )
    elif signal.disposition == SignalDisposition.SUPPRESSED:
        return SignalOutputBehavior(
            creates_finding=False,
            creates_advisory=False,
            creates_work_package=False,
            appears_in_report_detail=False,
            appears_in_summary=False,
            diagnostics_only=True,
        )
    else:
        # Unknown disposition — safe defaults
        return SignalOutputBehavior(
            creates_finding=False,
            creates_advisory=False,
            creates_work_package=False,
            appears_in_report_detail=False,
            appears_in_summary=False,
            diagnostics_only=True,
        )


def should_create_finding(signal: GovernedSignal) -> bool:
    """Only FINDING disposition creates a debt-register entry."""
    return signal.disposition == SignalDisposition.FINDING


def should_create_work_package(signal: GovernedSignal) -> bool:
    """Only FINDING disposition is eligible for work packages."""
    return signal.disposition == SignalDisposition.FINDING


def should_create_advisory(signal: GovernedSignal) -> bool:
    """Only ADVISORY disposition creates an advisory entry."""
    return signal.disposition == SignalDisposition.ADVISORY


def is_reportable(signal: GovernedSignal) -> bool:
    """Actionable/advisory reportability — not summary visibility.

    INFORMATIONAL signals appear in summaries but are not rendered
    as detailed report items by default.
    """
    return signal.disposition in (SignalDisposition.FINDING, SignalDisposition.ADVISORY)


def is_informational(signal: GovernedSignal) -> bool:
    """INFORMATIONAL disposition — context and coverage visibility only."""
    return signal.disposition == SignalDisposition.INFORMATIONAL
