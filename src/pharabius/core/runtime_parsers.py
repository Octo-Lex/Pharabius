"""Runtime version pin detection.

Extracted from scanner.py in v3.4.0. Detects Python and Node.js runtime
version pins from .python-version, .nvmrc, .node-version, .tool-versions,
and package.json engines field.
"""

from __future__ import annotations

from pathlib import Path

from pharabius.core.constants import (
    COMPLETENESS_COMPLETE,
    COMPLETENESS_PARTIAL,
    EVIDENCE_RUNTIME_VERSION_SIGNAL,
    OBSERVATION_STRENGTH_DIRECT,
    OBSERVATION_STRENGTH_LIMITATION,
    PARSER_FILESYSTEM,
    PARSER_MANIFEST,
    READ_MODE_JSON,
    READ_MODE_SKIPPED,
    READ_MODE_TEXT,
)
from pharabius.core.io_helpers import read_json, read_text
from pharabius.schemas.evidence import EvidenceBuilder


def detect_runtime_version_pins(root: Path, builder: EvidenceBuilder) -> None:
    """Detect runtime version pinning at repository level.

    v3.3.0: Python + Node.js only. Ruby/Java deferred.
    """

    _RUNTIME_FILES: list[tuple[str, str, str]] = [
        (".python-version", "Python", "python_version_file"),
        (".nvmrc", "Node.js", "nvmrc"),
        (".node-version", "Node.js", "node_version_file"),
        (".tool-versions", "multi", "tool_versions"),
    ]

    detected_runtimes: dict[str, str] = {}

    for filename, runtime, parser in _RUNTIME_FILES:
        fpath = root / filename
        if not fpath.exists():
            continue
        text = read_text(fpath)
        if not text:
            continue

        if parser == "tool_versions":
            _parse_tool_versions(text, detected_runtimes, builder, EVIDENCE_RUNTIME_VERSION_SIGNAL)
        else:
            version = text.strip().split("\n")[0].strip()
            if version:
                detected_runtimes[runtime] = version
                builder.add(
                    type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
                    category="dependencies",
                    summary=f"{runtime} runtime version pinned: {version}",
                    location_file=filename,
                    subject=runtime,
                    raw_observation=f"{runtime}:{version}",
                    confidence="High",
                    metadata={
                        "signal": "runtime_version_pinned",
                        "runtime": runtime,
                        "version": version,
                        "source_file": filename,
                        "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                        "completeness": COMPLETENESS_COMPLETE,
                        "parser": PARSER_FILESYSTEM,
                        "read_mode": READ_MODE_TEXT,
                    },
                )

    # Check package.json engines.node
    pkg_json = root / "package.json"
    if pkg_json.exists():
        data = read_json(pkg_json)
        engines = data.get("engines", {})
        node_engine = engines.get("node")
        if node_engine and "Node.js" not in detected_runtimes:
            detected_runtimes["Node.js"] = node_engine
            builder.add(
                type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
                category="dependencies",
                summary=f"Node.js runtime version pinned in package.json: {node_engine}",
                location_file="package.json",
                subject="Node.js",
                raw_observation=f"Node.js:{node_engine}:engines",
                confidence="High",
                metadata={
                    "signal": "runtime_version_pinned",
                    "runtime": "Node.js",
                    "version": node_engine,
                    "source_file": "package.json",
                    "source_field": "engines.node",
                    "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                    "completeness": COMPLETENESS_COMPLETE,
                    "parser": PARSER_MANIFEST,
                    "read_mode": READ_MODE_JSON,
                },
            )

    _check_missing_runtime_pins(root, detected_runtimes, builder, EVIDENCE_RUNTIME_VERSION_SIGNAL)


def _parse_tool_versions(
    text: str, detected: dict[str, str], builder: EvidenceBuilder, ev_type: str,
) -> None:
    """Parse .tool-versions for runtime pins.

    v3.3.0: Python + Node.js only. Ruby/Java entries are ignored.
    """
    runtime_map = {"python": "Python", "nodejs": "Node.js"}
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        tool, version = parts
        runtime = runtime_map.get(tool.lower())
        if runtime:
            detected[runtime] = version
            builder.add(
                type_=ev_type,
                category="dependencies",
                summary=f"{runtime} runtime version pinned via .tool-versions: {version}",
                location_file=".tool-versions",
                subject=runtime,
                raw_observation=f"{runtime}:{version}:tool-versions",
                confidence="High",
                metadata={
                    "signal": "runtime_version_pinned",
                    "runtime": runtime,
                    "version": version,
                    "source_file": ".tool-versions",
                    "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                    "completeness": COMPLETENESS_COMPLETE,
                    "parser": PARSER_FILESYSTEM,
                    "read_mode": READ_MODE_TEXT,
                },
            )


def _check_missing_runtime_pins(
    root: Path, detected: dict[str, str], builder: EvidenceBuilder, ev_type: str,
) -> None:
    """Emit evidence when manifests exist but runtime pins are missing."""
    python_manifests = [root / "pyproject.toml", root / "requirements.txt", root / "Pipfile"]
    has_python_manifest = any(p.exists() for p in python_manifests)
    if has_python_manifest and "Python" not in detected:
        builder.add(
            type_=ev_type,
            category="dependencies",
            summary="Python manifest detected without runtime version pin",
            location_file=".",
            subject="Python",
            raw_observation="runtime_version_missing:Python",
            confidence="Medium",
            metadata={
                "signal": "runtime_version_missing",
                "runtime": "Python",
                "observation_strength": OBSERVATION_STRENGTH_LIMITATION,
                "completeness": COMPLETENESS_PARTIAL,
                "parser": PARSER_FILESYSTEM,
                "read_mode": READ_MODE_SKIPPED,
            },
        )

    if (root / "package.json").exists() and "Node.js" not in detected:
        builder.add(
            type_=ev_type,
            category="dependencies",
            summary="Node.js manifest detected without runtime version pin",
            location_file=".",
            subject="Node.js",
            raw_observation="runtime_version_missing:Node.js",
            confidence="Medium",
            metadata={
                "signal": "runtime_version_missing",
                "runtime": "Node.js",
                "observation_strength": OBSERVATION_STRENGTH_LIMITATION,
                "completeness": COMPLETENESS_PARTIAL,
                "parser": PARSER_FILESYSTEM,
                "read_mode": READ_MODE_SKIPPED,
            },
        )
