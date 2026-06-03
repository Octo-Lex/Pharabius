"""Runtime signal adapters.

Translate runtime domain IR into platform-level GovernedSignal instances.
Runtime keeps its internal IR (RuntimeEvidence, RuntimeConflictGroup,
RuntimeSourceGrade). These adapters are thin translation layers.
"""

from __future__ import annotations

from pharabius.core.runtime.models import (
    Confidence,
    RuntimeConflictGroup,
    RuntimeEcosystem,
    RuntimeEvidence,
    RuntimeSignalAction,
    RuntimeSignalClassification,
)
from pharabius.core.signals.models import (
    GovernedSignal,
    SignalDisposition,
    SignalFamily,
    make_signal_id,
)


def runtime_conflict_to_signal(conflict: RuntimeConflictGroup) -> GovernedSignal:
    """Adapt a RuntimeConflictGroup into a GovernedSignal (FINDING).

    Runtime conflicts are always findings — they represent definite
    contradictions in runtime declarations.
    """
    evidence_ids = [e.runtime_evidence_id for e in conflict.evidence]
    signal_id = make_signal_id("runtime", conflict.conflict_kind.value, evidence_ids)

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.RUNTIME,
        kind=conflict.conflict_kind.value,
        disposition=SignalDisposition.FINDING,
        category="TD-DEP",
        severity="Medium",
        confidence="High",
        evidence_ids=evidence_ids,
        source_signal_ids=[],
        title=f"{conflict.runtime_name} runtime version declarations conflict",
        summary=f"Multiple {conflict.runtime_name} runtime version declarations disagree.",
        explanation=conflict.explanation,
        metadata={
            "runtime_name": conflict.runtime_name,
            "ecosystem": conflict.ecosystem.value,
            "conflict_kind": conflict.conflict_kind.value,
        },
    )


def runtime_missing_pin_to_signal(
    runtime_name: str,
    ecosystem: RuntimeEcosystem,
    trigger_files: list[str],
    evidence_ids: list[str],
) -> GovernedSignal:
    """Adapt a missing runtime pin into a GovernedSignal (ADVISORY).

    Missing pins are advisories — hygiene observations, not actionable debt.
    They do not generate work packages.
    """
    signal_id = make_signal_id("runtime", "missing_runtime_pin", [runtime_name])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.RUNTIME,
        kind="missing_runtime_pin",
        disposition=SignalDisposition.ADVISORY,
        category="TD-DEP",
        severity="Low",
        confidence="Low",
        evidence_ids=evidence_ids,
        source_signal_ids=[],
        title=f"Missing runtime version pins for: {runtime_name}",
        summary=(
            f"Dependency manifests exist for {runtime_name} but no runtime "
            "version pinning file detected."
        ),
        explanation=(
            f"{runtime_name} manifests ({', '.join(trigger_files)}) detected "
            f"but no reproducibility pin found. Runtime drift affects builds."
        ),
        metadata={
            "runtime_name": runtime_name,
            "ecosystem": ecosystem.value,
            "trigger_files": trigger_files,
        },
    )


def runtime_evidence_to_signal(evidence: RuntimeEvidence) -> GovernedSignal:
    """Adapt a RuntimeEvidence item into a GovernedSignal (INFORMATIONAL).

    Individual evidence items that are neither conflicts nor missing pins
    are informational — they provide context and coverage visibility.
    """
    signal_id = make_signal_id(
        "runtime",
        "evidence",
        [evidence.runtime_evidence_id],
    )

    version = evidence.raw_version or evidence.constraint.value or "?"

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.RUNTIME,
        kind=f"runtime_evidence_{evidence.constraint.kind.value}",
        disposition=SignalDisposition.INFORMATIONAL,
        category="TD-DEP",
        severity="Low",
        confidence=evidence.confidence.value,
        evidence_ids=[evidence.runtime_evidence_id],
        source_signal_ids=[],
        title=f"{evidence.runtime_name} runtime evidence: {version}",
        summary=(
            f"{evidence.runtime_name} runtime version {evidence.constraint.kind.value} "
            f"from {evidence.source_path}"
        ),
        explanation=(
            f"{evidence.runtime_name} {version} detected in {evidence.source_path} "
            f"(grade={evidence.source_grade.value}, "
            f"constraint={evidence.constraint.kind.value})."
        ),
        metadata={
            "runtime_name": evidence.runtime_name,
            "ecosystem": evidence.ecosystem.value,
            "source_grade": evidence.source_grade.value,
            "constraint_kind": evidence.constraint.kind.value,
            "source_path": evidence.source_path,
            "source_detail": evidence.source_detail,
        },
    )


# ── Evidence-based adapters (for analyzer consumption) ────────────────


def runtime_conflict_to_signal_from_evidence(evidence_item: object) -> GovernedSignal:
    """Adapt a conflict EvidenceItem into a GovernedSignal (FINDING).

    Used by the analyzer which consumes EvidenceItems, not RuntimeConflictGroup.
    """
    # EvidenceItem is a Pydantic model — access via attributes
    ev_id = getattr(evidence_item, "evidence_id", "unknown")
    meta = getattr(evidence_item, "metadata", {}) or {}
    runtime = meta.get("runtime", "unknown")
    conflict_kind = meta.get("conflict_reason", "unknown")

    signal_id = make_signal_id("runtime", conflict_kind, [ev_id])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.RUNTIME,
        kind=conflict_kind,
        disposition=SignalDisposition.FINDING,
        category="TD-DEP",
        severity="Medium",
        confidence="High",
        evidence_ids=[ev_id],
        source_signal_ids=[],
        title=f"{runtime} runtime version declarations conflict",
        summary=f"Multiple {runtime} runtime version declarations disagree.",
        explanation=getattr(evidence_item, "summary", ""),
        metadata={
            "runtime_name": runtime,
            "conflict_kind": conflict_kind,
        },
    )


def runtime_missing_pin_to_signal_from_evidence(
    evidence_items: list[object],
) -> GovernedSignal:
    """Adapt missing-pin EvidenceItems into a GovernedSignal (ADVISORY).

    Used by the analyzer which consumes EvidenceItems.
    """
    ev_ids = [getattr(e, "evidence_id", "unknown") for e in evidence_items]
    runtimes = []
    for e in evidence_items:
        meta = getattr(e, "metadata", {}) or {}
        rt = meta.get("runtime", "unknown")
        if rt not in runtimes:
            runtimes.append(rt)

    signal_id = make_signal_id("runtime", "missing_runtime_pin", runtimes)

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.RUNTIME,
        kind="missing_runtime_pin",
        disposition=SignalDisposition.ADVISORY,
        category="TD-DEP",
        severity="Low",
        confidence="Low",
        evidence_ids=ev_ids,
        source_signal_ids=[],
        title=f"Missing runtime version pins for: {', '.join(runtimes)}",
        summary=(
            f"Dependency manifests exist for {', '.join(runtimes)} but no runtime "
            "version pinning file detected."
        ),
        explanation=(
            f"{', '.join(runtimes)} manifests detected but no reproducibility pin found."
        ),
        metadata={
            "runtimes": runtimes,
        },
    )
