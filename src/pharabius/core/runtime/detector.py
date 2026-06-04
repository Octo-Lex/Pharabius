"""Runtime version detection orchestrator.

This is the only module that talks to EvidenceBuilder.
Orchestrates: parsers → conflict detection → policy → evidence store.
"""

from __future__ import annotations

from pathlib import Path

from pharabius.core.constants import (
    COMPLETENESS_COMPLETE,
    COMPLETENESS_PARTIAL,
    EVIDENCE_RUNTIME_VERSION_SIGNAL,
    OBSERVATION_STRENGTH_DIRECT,
    OBSERVATION_STRENGTH_HEURISTIC,
    OBSERVATION_STRENGTH_LIMITATION,
    PARSER_FILESYSTEM,
    PARSER_MANIFEST,
    READ_MODE_SKIPPED,
    READ_MODE_TEXT,
    READ_MODE_YAML,
    RUNTIME_SIGNAL_CONFLICT,
    RUNTIME_SIGNAL_FROM_CI,
    RUNTIME_SIGNAL_FROM_CONTAINER,
    RUNTIME_SIGNAL_MISSING,
    RUNTIME_SIGNAL_PARTIAL,
    RUNTIME_SIGNAL_PINNED,
)
from pharabius.core.runtime.conflict import detect_conflicts
from pharabius.core.runtime.docker import detect_dockerfile_sources
from pharabius.core.runtime.dotnet import detect_dotnet_sources
from pharabius.core.runtime.ecosystems import (
    detect_java_sources,
    detect_node_sources,
    detect_python_sources,
    detect_ruby_sources,
)
from pharabius.core.runtime.github_actions import detect_ci_sources
from pharabius.core.runtime.go import detect_go_sources
from pharabius.core.runtime.models import (
    Confidence,
    RuntimeConstraintKind,
    RuntimeEvidence,
    RuntimeSourceType,
)
from pharabius.core.runtime.php import detect_php_sources
from pharabius.core.runtime.policy import is_runtime_pin
from pharabius.core.runtime.rust import detect_rust_sources
from pharabius.core.runtime.tool_versions import detect_tool_versions_sources
from pharabius.schemas.evidence import EvidenceBuilder

# ── Missing-pin triggers ─────────────────────────────────────────────

_MISSING_PIN_TRIGGERS: dict[str, list[str]] = {
    "Python": ["pyproject.toml", "requirements.txt", "setup.py", "Pipfile", "runtime.txt"],
    "Node.js": ["package.json"],
    "Ruby": ["Gemfile", ".gemspec"],
    "Java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "Go": ["go.mod"],
    "Rust": ["Cargo.toml", "rust-toolchain", "rust-toolchain.toml"],
    ".NET": ["global.json", "*.csproj", "*.sln"],
    "PHP": ["composer.json"],
}


# ── Public API ───────────────────────────────────────────────────────


def detect_runtime_version_pins(root: Path, builder: EvidenceBuilder) -> None:
    """Detect runtime version pinning and conflicts at repository level.

    This is the scanner-facing API. It orchestrates all parsing, conflict
    detection, and policy classification, then emits EvidenceItems.
    """
    # 1. Collect all runtime evidence from parsers
    all_evidence: list[RuntimeEvidence] = []
    all_evidence.extend(detect_python_sources(root))
    all_evidence.extend(detect_node_sources(root))
    all_evidence.extend(detect_ruby_sources(root))
    all_evidence.extend(detect_java_sources(root))
    all_evidence.extend(detect_go_sources(root))
    all_evidence.extend(detect_rust_sources(root))
    all_evidence.extend(detect_dotnet_sources(root))
    all_evidence.extend(detect_php_sources(root))
    all_evidence.extend(detect_tool_versions_sources(root))
    all_evidence.extend(detect_dockerfile_sources(root))
    all_evidence.extend(detect_ci_sources(root))

    # 2. Detect conflicts
    conflicts = detect_conflicts(all_evidence)

    # 3. Emit all evidence as EvidenceItems
    _emit_evidence(all_evidence, builder)

    # 4. Emit conflict evidence
    _emit_conflicts(conflicts, builder)

    # 5. Detect and emit missing runtime pins
    _emit_missing_pins(root, all_evidence, builder)


# ── Evidence emission ────────────────────────────────────────────────


def _emit_evidence(evidence: list[RuntimeEvidence], builder: EvidenceBuilder) -> None:
    """Convert RuntimeEvidence to EvidenceItems."""
    for ev in evidence:
        signal = _constraint_to_signal(ev.constraint.kind, ev.source_type)
        if signal is None:
            continue

        obs_strength = _confidence_to_observation(ev.confidence)
        completeness = (
            COMPLETENESS_COMPLETE
            if ev.constraint.kind == RuntimeConstraintKind.EXACT
            else COMPLETENESS_PARTIAL
        )
        parser = _source_type_to_parser(ev.source_type)
        read_mode = _source_type_to_read_mode(ev.source_type)

        meta: dict = {
            "signal": signal,
            "runtime": ev.runtime_name,
            "constraint_kind": ev.constraint.kind.value,
            "source_file": ev.source_path,
            "source_kind": ev.source_type.value,
            "observation_strength": obs_strength,
            "completeness": completeness,
            "parser": parser,
            "read_mode": read_mode,
        }
        if ev.raw_version:
            meta["version"] = ev.raw_version
        if ev.constraint.value:
            meta["normalized"] = ev.constraint.value
        if ev.source_detail:
            meta["source_detail"] = ev.source_detail

        builder.add(
            type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
            category="dependencies",
            summary=_build_summary(ev, signal),
            location_file=ev.source_path,
            subject=ev.runtime_name,
            raw_observation=f"{ev.runtime_name}:{ev.raw_version or '?'}:{ev.source_path}",
            confidence=ev.confidence.value,
            metadata=meta,
        )


def _emit_conflicts(conflicts: list, builder: EvidenceBuilder) -> None:
    """Emit conflict evidence items."""

    for group in conflicts:
        sources_meta = [
            {
                "source_file": e.source_path,
                "source_kind": e.source_type.value,
                "version": e.raw_version or e.constraint.value or "?",
                "normalized": e.constraint.value,
                "constraint_kind": e.constraint.kind.value,
            }
            for e in group.evidence
        ]

        builder.add(
            type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
            category="dependencies",
            summary=f"{group.runtime_name} runtime version declarations conflict",
            location_file=".",
            subject=group.runtime_name,
            raw_observation=f"{group.runtime_name}:conflict:{group.conflict_kind.value}",
            confidence="High",
            metadata={
                "signal": RUNTIME_SIGNAL_CONFLICT,
                "runtime": group.runtime_name,
                "sources": sources_meta,
                "conflict_reason": group.conflict_kind.value,
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_FILESYSTEM,
                "read_mode": READ_MODE_TEXT,
            },
        )


def _emit_missing_pins(
    root: Path,
    evidence: list[RuntimeEvidence],
    builder: EvidenceBuilder,
) -> None:
    """Emit advisory evidence for missing runtime pins."""
    # Use is_runtime_pin() to determine which ecosystems have actual pins
    pinned_runtimes = {ev.runtime_name for ev in evidence if is_runtime_pin(ev)}
    # Also consider any detected ecosystem (even non-pin evidence) as "detected"
    detected_runtimes = {ev.runtime_name for ev in evidence}

    for runtime_name, trigger_files in _MISSING_PIN_TRIGGERS.items():
        if runtime_name in pinned_runtimes:
            continue  # Has a real pin — skip
        if runtime_name not in detected_runtimes:
            # Check if ecosystem manifest exists even without any evidence
            has_trigger = any((root / f).exists() for f in trigger_files)
            if not has_trigger:
                continue
        # Ecosystem detected but no pin found → advisory
        builder.add(
            type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
            category="dependencies",
            summary=f"{runtime_name} manifest detected without runtime version pin",
            location_file=".",
            subject=runtime_name,
            raw_observation=f"runtime_version_missing:{runtime_name}",
            confidence="Medium",
            metadata={
                "signal": RUNTIME_SIGNAL_MISSING,
                "runtime": runtime_name,
                "observation_strength": OBSERVATION_STRENGTH_LIMITATION,
                "completeness": COMPLETENESS_PARTIAL,
                "parser": PARSER_FILESYSTEM,
                "read_mode": READ_MODE_SKIPPED,
            },
        )


# ── Helpers ──────────────────────────────────────────────────────────


def _constraint_to_signal(
    kind: RuntimeConstraintKind, source_type: RuntimeSourceType
) -> str | None:
    """Map constraint kind + source type to signal constant."""
    if kind == RuntimeConstraintKind.EXACT:
        if source_type == RuntimeSourceType.CONTAINER:
            return RUNTIME_SIGNAL_FROM_CONTAINER
        if source_type == RuntimeSourceType.CI:
            return RUNTIME_SIGNAL_FROM_CI
        return RUNTIME_SIGNAL_PINNED
    if kind == RuntimeConstraintKind.RANGE:
        return RUNTIME_SIGNAL_PINNED
    if kind == RuntimeConstraintKind.UNKNOWN:
        return RUNTIME_SIGNAL_PARTIAL
    return None


def _confidence_to_observation(confidence: Confidence) -> str:
    mapping = {
        Confidence.HIGH: OBSERVATION_STRENGTH_DIRECT,
        Confidence.MEDIUM: OBSERVATION_STRENGTH_HEURISTIC,
        Confidence.LOW: OBSERVATION_STRENGTH_LIMITATION,
    }
    return mapping.get(confidence, OBSERVATION_STRENGTH_HEURISTIC)


def _source_type_to_parser(source_type: RuntimeSourceType) -> str:
    if source_type in (
        RuntimeSourceType.VERSION_FILE,
        RuntimeSourceType.TOOL_VERSIONS,
        RuntimeSourceType.CONTAINER,
    ):
        return PARSER_FILESYSTEM
    if source_type == RuntimeSourceType.CI:
        return PARSER_FILESYSTEM
    return PARSER_MANIFEST


def _source_type_to_read_mode(source_type: RuntimeSourceType) -> str:
    if source_type == RuntimeSourceType.CI:
        return READ_MODE_YAML
    return READ_MODE_TEXT


def _build_summary(ev: RuntimeEvidence, signal: str) -> str:
    """Build a human-readable summary for an evidence item."""
    version = ev.raw_version or "?"
    if signal == RUNTIME_SIGNAL_FROM_CONTAINER:
        return f"{ev.runtime_name} runtime from Dockerfile: {version}"
    if signal == RUNTIME_SIGNAL_FROM_CI:
        return f"{ev.runtime_name} runtime from CI: {version}"
    if signal == RUNTIME_SIGNAL_PARTIAL:
        return f"{ev.runtime_name} runtime evidence (partial/unknown version)"
    return f"{ev.runtime_name} runtime version pinned: {version}"
