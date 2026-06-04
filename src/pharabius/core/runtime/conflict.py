"""Runtime conflict detection.

Consumes list[RuntimeEvidence] and produces list[RuntimeConflictGroup].
Does NOT know about file formats or parsing.
"""

from __future__ import annotations

from pharabius.core.runtime.constraints import range_excludes_exact, ranges_are_disjoint
from pharabius.core.runtime.models import (
    RuntimeConflictGroup,
    RuntimeConflictKind,
    RuntimeConstraintKind,
    RuntimeEvidence,
    RuntimeSourceType,
)
from pharabius.core.runtime.policy import (
    is_deterministic_project_pin,
    is_manifest_compatibility_range,
)

# Conflict kind precedence: source-specific first, generic second
_CONFLICT_PRECEDENCE = [
    RuntimeConflictKind.CI_DIFFERS,
    RuntimeConflictKind.DOCKERFILE_DIFFERS,
    RuntimeConflictKind.PIN_VIOLATES_MANIFEST_RANGE,
    RuntimeConflictKind.EXACT_EXACT_MISMATCH,
    RuntimeConflictKind.RANGE_EXCLUDES_EXACT,
    RuntimeConflictKind.INCOMPATIBLE_RANGES,
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
            source_type = (
                RuntimeSourceType.CI
                if kind == RuntimeConflictKind.CI_DIFFERS
                else RuntimeSourceType.CONTAINER
            )
            group = _check_source_vs_pin(runtime_name, exacts, source_type, kind)
            if group:
                conflicts.append(group)
                break  # Deduplicate: one conflict per runtime from source-specific

        else:
            # 2. Pin violates manifest range
            group = _check_pin_vs_manifest_range(runtime_name, exacts, ranges)
            if group:
                conflicts.append(group)
                continue

            # 3. Exact vs exact
            group = _check_exact_exact(runtime_name, exacts)
            if group:
                conflicts.append(group)
                continue

            # 4. Range excludes exact (remaining cases)
            group = _check_range_exact(runtime_name, exacts, ranges)
            if group:
                conflicts.append(group)
                continue

            # 5. Range vs range (conservative)
            group = _check_range_vs_range(runtime_name, ranges)
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
    pin_evs = [
        e
        for e in exacts
        if e.source_type
        in (
            RuntimeSourceType.VERSION_FILE,
            RuntimeSourceType.TOOL_VERSIONS,
            RuntimeSourceType.MANIFEST,
        )
    ]
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


def _check_pin_vs_manifest_range(
    runtime_name: str,
    exacts: list[RuntimeEvidence],
    ranges: list[RuntimeEvidence],
) -> RuntimeConflictGroup | None:
    """Check if a deterministic project pin violates a manifest compatibility range."""
    det_pins = [e for e in exacts if is_deterministic_project_pin(e)]
    manifest_ranges = [e for e in ranges if is_manifest_compatibility_range(e)]
    if not det_pins or not manifest_ranges:
        return None

    for pin_ev in det_pins:
        for rng_ev in manifest_ranges:
            if range_excludes_exact(rng_ev.constraint, pin_ev.constraint.value or ""):
                return RuntimeConflictGroup(
                    ecosystem=pin_ev.ecosystem,
                    runtime_name=runtime_name,
                    conflict_kind=RuntimeConflictKind.PIN_VIOLATES_MANIFEST_RANGE,
                    evidence=[pin_ev, rng_ev],
                    explanation=(
                        f"{pin_ev.source_path} ({pin_ev.source_grade.value}) "
                        f"{pin_ev.constraint.value} violates "
                        f"{rng_ev.source_path} ({rng_ev.source_grade.value}) "
                        f"{rng_ev.constraint.raw}"
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


def _check_range_vs_range(
    runtime_name: str,
    ranges: list[RuntimeEvidence],
) -> RuntimeConflictGroup | None:
    """Check for definitely disjoint ranges (conservative)."""
    if len(ranges) < 2:
        return None
    for i in range(len(ranges)):
        for j in range(i + 1, len(ranges)):
            a, b = ranges[i], ranges[j]
            if ranges_are_disjoint(a.constraint, b.constraint):
                return RuntimeConflictGroup(
                    ecosystem=a.ecosystem,
                    runtime_name=runtime_name,
                    conflict_kind=RuntimeConflictKind.INCOMPATIBLE_RANGES,
                    evidence=[a, b],
                    explanation=(
                        f"{a.source_path} ({a.source_grade.value}) "
                        f"{a.constraint.raw} incompatible with "
                        f"{b.source_path} ({b.source_grade.value}) "
                        f"{b.constraint.raw}"
                    ),
                )
    return None
