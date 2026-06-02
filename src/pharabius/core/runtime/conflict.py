"""Runtime conflict detection.

Consumes list[RuntimeEvidence] and produces list[RuntimeConflictGroup].
Does NOT know about file formats or parsing.
"""

from __future__ import annotations

from pharabius.core.runtime.constraints import range_excludes_exact
from pharabius.core.runtime.models import (
    RuntimeConflictGroup,
    RuntimeConflictKind,
    RuntimeConstraintKind,
    RuntimeEvidence,
    RuntimeSourceType,
)


# Conflict kind precedence: source-specific first, generic second
_CONFLICT_PRECEDENCE = [
    RuntimeConflictKind.CI_DIFFERS,
    RuntimeConflictKind.DOCKERFILE_DIFFERS,
    RuntimeConflictKind.EXACT_EXACT_MISMATCH,
    RuntimeConflictKind.RANGE_EXCLUDES_EXACT,
]


def detect_conflicts(evidence: list[RuntimeEvidence]) -> list[RuntimeConflictGroup]:
    """Detect runtime conflicts from normalized evidence.

    One conflict group per runtime per conflict.
    Deduplicates: same evidence pair only produces the highest-precedence conflict.
    """
    by_runtime: dict[str, list[RuntimeEvidence]] = {}
    for ev in evidence:
        if ev.constraint.kind not in (RuntimeConstraintKind.EXACT, RuntimeConstraintKind.RANGE):
            continue
        by_runtime.setdefault(ev.runtime_name, []).append(ev)

    conflicts: list[RuntimeConflictGroup] = []

    for runtime_name, rt_sources in by_runtime.items():
        exacts = [e for e in rt_sources if e.constraint.kind == RuntimeConstraintKind.EXACT]
        ranges = [e for e in rt_sources if e.constraint.kind == RuntimeConstraintKind.RANGE]

        # 1. Source-specific conflicts: CI vs pin, Dockerfile vs pin
        for kind in [RuntimeConflictKind.CI_DIFFERS, RuntimeConflictKind.DOCKERFILE_DIFFERS]:
            source_type = RuntimeSourceType.CI if kind == RuntimeConflictKind.CI_DIFFERS else RuntimeSourceType.CONTAINER
            group = _check_source_vs_pin(runtime_name, exacts, source_type, kind)
            if group:
                conflicts.append(group)
                break  # Deduplicate: one conflict per runtime from source-specific

        else:
            # 2. Exact vs exact
            group = _check_exact_exact(runtime_name, exacts)
            if group:
                conflicts.append(group)
                continue

            # 3. Range excludes exact
            group = _check_range_exact(runtime_name, exacts, ranges)
            if group:
                conflicts.append(group)

    return conflicts


def _check_source_vs_pin(
    runtime_name: str,
    exacts: list[RuntimeEvidence],
    source_type: RuntimeSourceType,
    kind: RuntimeConflictKind,
) -> RuntimeConflictGroup | None:
    """Check CI/Dockerfile exact version against pin-file exact versions."""
    source_evs = [e for e in exacts if e.source_type == source_type]
    pin_evs = [e for e in exacts if e.source_type in (
        RuntimeSourceType.VERSION_FILE,
        RuntimeSourceType.TOOL_VERSIONS,
        RuntimeSourceType.MANIFEST,
    )]
    if not source_evs or not pin_evs:
        return None

    for src_ev in source_evs:
        for pin_ev in pin_evs:
            if src_ev.constraint.value != pin_ev.constraint.value:
                return RuntimeConflictGroup(
                    ecosystem=src_ev.ecosystem,
                    runtime_name=runtime_name,
                    conflict_kind=kind,
                    evidence=[pin_ev, src_ev],
                    explanation=(
                        f"{pin_ev.source_path}={pin_ev.constraint.value} "
                        f"conflicts with {src_ev.source_path}={src_ev.constraint.value}"
                    ),
                )
    return None


def _check_exact_exact(
    runtime_name: str,
    exacts: list[RuntimeEvidence],
) -> RuntimeConflictGroup | None:
    """Check for exact-vs-exact version mismatches."""
    if len(exacts) < 2:
        return None
    unique_values = set(e.constraint.value for e in exacts if e.constraint.value)
    if len(unique_values) <= 1:
        return None
    return RuntimeConflictGroup(
        ecosystem=exacts[0].ecosystem,
        runtime_name=runtime_name,
        conflict_kind=RuntimeConflictKind.EXACT_EXACT_MISMATCH,
        evidence=exacts,
        explanation=(
            f"Multiple {runtime_name} runtime declarations disagree: "
            + ", ".join(f"{e.source_path}={e.constraint.value}" for e in exacts)
        ),
    )


def _check_range_exact(
    runtime_name: str,
    exacts: list[RuntimeEvidence],
    ranges: list[RuntimeEvidence],
) -> RuntimeConflictGroup | None:
    """Check if a range constraint excludes an exact pin."""
    if not exacts or not ranges:
        return None
    exact_ev = exacts[0]
    for rng_ev in ranges:
        if rng_ev.constraint.lower_bound and exact_ev.constraint.value:
            if range_excludes_exact(rng_ev.constraint, exact_ev.constraint.value):
                return RuntimeConflictGroup(
                    ecosystem=exact_ev.ecosystem,
                    runtime_name=runtime_name,
                    conflict_kind=RuntimeConflictKind.RANGE_EXCLUDES_EXACT,
                    evidence=[exact_ev, rng_ev],
                    explanation=(
                        f"{rng_ev.source_path}={rng_ev.constraint.raw} "
                        f"excludes {exact_ev.source_path}={exact_ev.constraint.value}"
                    ),
                )
    return None
