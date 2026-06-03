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

from pharabius.core.signals.models import GovernedSignal, SignalDisposition


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
