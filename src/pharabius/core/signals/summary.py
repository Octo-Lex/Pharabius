"""Signal governance summary.

Builds summary statistics from governed signals for run-history and reporting.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from pharabius.core.signals.models import GovernedSignal


@dataclass(frozen=True)
class SignalSummary:
    """Prepared summary of governed signals — rendering only, no re-analysis."""

    total: int
    by_family: dict[str, int]
    by_disposition: dict[str, int]
    by_severity: dict[str, int]
    by_confidence: dict[str, int]


def build_signal_summary(
    signals: list[GovernedSignal],
    include_diagnostics: bool = False,
) -> SignalSummary:
    """Build summary statistics from a list of governed signals.

    By default, SUPPRESSED signals are excluded from counts.
    Pass include_diagnostics=True to include them.
    """
    family_counts: Counter[str] = Counter()
    disposition_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()

    from pharabius.core.signals.models import SignalDisposition

    for signal in signals:
        # SUPPRESSED signals excluded from normal summary counts
        if signal.disposition == SignalDisposition.SUPPRESSED and not include_diagnostics:
            continue

        family_counts[signal.family.value] += 1
        disposition_counts[signal.disposition.value] += 1
        severity_counts[signal.severity] += 1
        confidence_counts[signal.confidence] += 1

    return SignalSummary(
        total=sum(family_counts.values()),
        by_family=dict(family_counts),
        by_disposition=dict(disposition_counts),
        by_severity=dict(severity_counts),
        by_confidence=dict(confidence_counts),
    )


def signal_summary_to_dict(summary: SignalSummary) -> dict:
    """Convert SignalSummary to a JSON-serializable dict."""
    return {
        "total": summary.total,
        "by_family": summary.by_family,
        "by_disposition": summary.by_disposition,
        "by_severity": summary.by_severity,
        "by_confidence": summary.by_confidence,
    }
