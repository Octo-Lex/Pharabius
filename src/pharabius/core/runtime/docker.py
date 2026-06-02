"""Dockerfile runtime evidence parser."""

from __future__ import annotations

import re
from pathlib import Path

from pharabius.core.io_helpers import read_text
from pharabius.core.runtime.constraints import parse_constraint
from pharabius.core.runtime.models import (
    Confidence,
    RuntimeConstraint,
    RuntimeConstraintKind,
    RuntimeEcosystem,
    RuntimeEvidence,
    RuntimeSourceType,
)
from pharabius.core.runtime.ecosystems import _make_id


_FROM_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"FROM\s+python:(\d+(?:\.\d+)?)"), "Python"),
    (re.compile(r"FROM\s+node:(\d+(?:\.\d+)?)"), "Node.js"),
    (re.compile(r"FROM\s+ruby:(\d+(?:\.\d+)?)"), "Ruby"),
    (re.compile(r"FROM\s+eclipse-temurin[\-\:]?[\w]*?(\d+)"), "Java"),
    (re.compile(r"FROM\s+openjdk[\-\:]?[\w]*?(\d+)"), "Java"),
    (re.compile(r"FROM\s+maven:\S*?[\-_](\d+)"), "Java"),
    (re.compile(r"FROM\s+gradle:\S*?[\-_]jdk(\d+)"), "Java"),
]

_RUNTIME_NAME_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"FROM\s+python[:\s]"), "Python"),
    (re.compile(r"FROM\s+node[:\s]"), "Node.js"),
    (re.compile(r"FROM\s+ruby[:\s]"), "Ruby"),
    (re.compile(r"FROM\s+(eclipse-temurin|openjdk|maven|gradle)[:\-_]"), "Java"),
]


def detect_dockerfile_sources(root: Path) -> list[RuntimeEvidence]:
    """Detect runtime versions from Dockerfile FROM lines."""
    evidence: list[RuntimeEvidence] = []

    dockerfiles: list[Path] = []
    for d in ["", "docker/"]:
        base = root / d
        if not base.exists():
            continue
        if (base / "Dockerfile").exists():
            dockerfiles.append(base / "Dockerfile")
        for df in sorted(base.glob("Dockerfile.*")):
            dockerfiles.append(df)

    for df_path in dockerfiles:
        text = read_text(df_path)
        if not text:
            continue
        rel_path = str(df_path.relative_to(root)).replace("\\", "/")

        for line in text.split("\n"):
            line = line.strip()
            if not line.upper().startswith("FROM"):
                continue

            # ARG-based FROM → unknown
            if "${" in line:
                for name_pat, runtime in _RUNTIME_NAME_PATTERNS:
                    if name_pat.search(line):
                        evidence.append(RuntimeEvidence(
                            runtime_evidence_id=_make_id(runtime, rel_path, "FROM-ARG", "unknown"),
                            ecosystem=_runtime_to_ecosystem(runtime),
                            runtime_name=runtime,
                            constraint=RuntimeConstraint(kind=RuntimeConstraintKind.UNKNOWN, raw="ARG"),
                            source_type=RuntimeSourceType.CONTAINER,
                            source_path=rel_path,
                            confidence=Confidence.LOW,
                        ))
                continue

            # Specific version FROM
            for pattern, runtime in _FROM_PATTERNS:
                m = pattern.search(line)
                if m:
                    version = m.group(1)
                    constraint = parse_constraint(runtime, version)
                    evidence.append(RuntimeEvidence(
                        runtime_evidence_id=_make_id(runtime, rel_path, "FROM", version),
                        ecosystem=_runtime_to_ecosystem(runtime),
                        runtime_name=runtime,
                        constraint=constraint,
                        source_type=RuntimeSourceType.CONTAINER,
                        source_path=rel_path,
                        confidence=Confidence.MEDIUM,
                        raw_version=version,
                    ))

    return evidence


def _runtime_to_ecosystem(runtime: str):
    from pharabius.core.runtime.models import RuntimeEcosystem
    mapping = {"Python": RuntimeEcosystem.PYTHON, "Node.js": RuntimeEcosystem.NODE,
               "Ruby": RuntimeEcosystem.RUBY, "Java": RuntimeEcosystem.JAVA}
    return mapping.get(runtime, RuntimeEcosystem.PYTHON)
