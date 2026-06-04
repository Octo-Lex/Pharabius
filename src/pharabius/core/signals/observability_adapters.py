"""Observability signal adapters.

Translate observability evidence into platform-level GovernedSignal
instances. Observability signals are deployment-derived indicators about
missing operational visibility.

v3.20.0: Adoption release — adapter matches existing behavior exactly.
Only missing-observability produces FINDING disposition.
No advisory or informational observability signals in v3.20.0.

Observability signals do NOT collect runtime telemetry, query monitoring
systems, evaluate SLOs, or certify operational maturity.
"""

from __future__ import annotations

from pharabius.core.signals.models import (
    GovernedSignal,
    SignalDisposition,
    SignalFamily,
    make_signal_id,
)


def observability_missing_to_signal(
    evidence_items: list[object],
) -> GovernedSignal:
    """Adapt missing-observability evidence into a GovernedSignal (FINDING).

    Triggered when deployment/infrastructure evidence exists but no
    observability keywords (logging, monitoring, tracing, alert, metrics)
    are found in risk_sensitive_keyword_detected evidence.
    Disposition matches existing _analyze_missing_observability behavior exactly.
    """
    ev_ids = [getattr(item, "evidence_id", str(i)) for i, item in enumerate(evidence_items)]

    signal_id = make_signal_id("observability", "missing_observability", ev_ids)

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.OBSERVABILITY,
        kind="missing_observability",
        disposition=SignalDisposition.FINDING,
        category="TD-OBS",
        severity="Medium",
        confidence="Low",
        evidence_ids=ev_ids,
        source_signal_ids=[],
        title="Deployment without observability evidence",
        summary=(
            "Deployment/infrastructure files detected but no logging, monitoring, "
            "tracing, or alerting keywords found. Operational visibility may be insufficient."
        ),
        explanation=(
            "Without observability, incidents are harder to detect, diagnose, and resolve. "
            "This is inferred from missing evidence, not confirmed absence."
        ),
        metadata={
            "spec_kind": "missing_observability",
            "evidence_count": len(evidence_items),
        },
    )
