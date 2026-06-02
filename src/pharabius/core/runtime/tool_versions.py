"""Tool-versions file parser (shared across ecosystems)."""

from __future__ import annotations

from pathlib import Path

from pharabius.core.io_helpers import read_text
from pharabius.core.runtime.constraints import parse_constraint
from pharabius.core.runtime.models import (
    Confidence,
    RuntimeEcosystem,
    RuntimeEvidence,
    RuntimeSourceType,
)
from pharabius.core.runtime.ecosystems import _make_id


_TOOL_VERSIONS_RUNTIME_MAP: dict[str, tuple[str, RuntimeEcosystem]] = {
    "python": ("Python", RuntimeEcosystem.PYTHON),
    "nodejs": ("Node.js", RuntimeEcosystem.NODE),
    "ruby": ("Ruby", RuntimeEcosystem.RUBY),
    "java": ("Java", RuntimeEcosystem.JAVA),
}


def detect_tool_versions_sources(root: Path) -> list[RuntimeEvidence]:
    """Detect runtime versions from .tool-versions file."""
    fpath = root / ".tool-versions"
    if not fpath.exists():
        return []

    text = read_text(fpath)
    if not text:
        return []

    evidence: list[RuntimeEvidence] = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        tool, version = parts
        info = _TOOL_VERSIONS_RUNTIME_MAP.get(tool.lower())
        if not info:
            continue
        runtime_name, ecosystem = info
        constraint = parse_constraint(runtime_name, version)
        evidence.append(RuntimeEvidence(
            runtime_evidence_id=_make_id(runtime_name, ".tool-versions", tool, version),
            ecosystem=ecosystem,
            runtime_name=runtime_name,
            constraint=constraint,
            source_type=RuntimeSourceType.TOOL_VERSIONS,
            source_path=".tool-versions",
            source_detail=tool,
            confidence=Confidence.HIGH,
            raw_version=version,
        ))

    return evidence
