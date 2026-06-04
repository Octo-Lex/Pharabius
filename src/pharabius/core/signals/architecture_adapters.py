"""Architecture signal adapters.

Translate architecture-risk evidence into platform-level GovernedSignal
instances. Architecture signals are graph-derived repository-local indicators.

v3.18.0: Adoption release — adapters match existing behavior exactly.
Only cycles and boundary violations produce FINDING disposition.
No informational architecture signals in v3.18.0.
"""

from __future__ import annotations

from pharabius.core.signals.models import (
    GovernedSignal,
    SignalDisposition,
    SignalFamily,
    make_signal_id,
)


def architecture_cycle_to_signal(
    spec: object,
) -> GovernedSignal:
    """Adapt a cycle ArchFindingSpec into a GovernedSignal (FINDING).

    Cycle findings represent confirmed circular dependencies with evidence.
    Disposition matches existing _analyze_cycles behavior exactly.
    """
    ev_ids = getattr(spec, "evidence_ids", [])
    category = getattr(spec, "category", "TD-ARCH")
    severity = getattr(spec, "severity", "Medium")
    confidence = getattr(spec, "confidence", "High")

    signal_id = make_signal_id("architecture", "cycle", ev_ids)

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.ARCHITECTURE,
        kind="cycle",
        disposition=SignalDisposition.FINDING,
        category=category,
        severity=severity,
        confidence=confidence,
        evidence_ids=ev_ids,
        source_signal_ids=[],
        title=getattr(spec, "title", ""),
        summary=getattr(spec, "description", ""),
        explanation=getattr(spec, "technical_impact", ""),
        metadata={
            "spec_kind": "cycle",
            "analysis_unit_ids": getattr(spec, "analysis_unit_ids", []),
        },
    )


def architecture_boundary_violation_to_signal(
    spec: object,
) -> GovernedSignal:
    """Adapt a boundary violation ArchFindingSpec into a GovernedSignal (FINDING).

    Boundary violations represent confirmed layer policy violations with evidence.
    Disposition matches existing _analyze_violations behavior exactly.
    """
    ev_ids = getattr(spec, "evidence_ids", [])
    category = getattr(spec, "category", "TD-ARCH")
    severity = getattr(spec, "severity", "Medium")
    confidence = getattr(spec, "confidence", "High")

    signal_id = make_signal_id("architecture", "boundary_violation", ev_ids)

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.ARCHITECTURE,
        kind="boundary_violation",
        disposition=SignalDisposition.FINDING,
        category=category,
        severity=severity,
        confidence=confidence,
        evidence_ids=ev_ids,
        source_signal_ids=[],
        title=getattr(spec, "title", ""),
        summary=getattr(spec, "description", ""),
        explanation=getattr(spec, "technical_impact", ""),
        metadata={
            "spec_kind": "boundary_violation",
            "analysis_unit_ids": getattr(spec, "analysis_unit_ids", []),
        },
    )
