"""Python runtime evidence parsers."""

from __future__ import annotations

import re
from pathlib import Path

from pharabius.core.io_helpers import read_json, read_text
from pharabius.core.runtime.constraints import parse_constraint
from pharabius.core.runtime.models import (
    Confidence,
    RuntimeConstraintKind,
    RuntimeEcosystem,
    RuntimeEvidence,
    RuntimeSourceType,
)


def _make_id(ecosystem: str, source_path: str, source_detail: str | None, raw: str) -> str:
    """Deterministic runtime evidence ID."""
    parts = [ecosystem, source_path, source_detail or "", raw]
    return ":".join(parts)


def detect_python_sources(root: Path) -> list[RuntimeEvidence]:
    """Detect Python runtime version sources."""
    evidence: list[RuntimeEvidence] = []

    # .python-version
    fpath = root / ".python-version"
    if fpath.exists():
        text = read_text(fpath)
        if text:
            version = text.strip().split("\n")[0].strip()
            if version:
                constraint = parse_constraint("Python", version)
                evidence.append(RuntimeEvidence(
                    runtime_evidence_id=_make_id("Python", ".python-version", None, version),
                    ecosystem=RuntimeEcosystem.PYTHON,
                    runtime_name="Python",
                    constraint=constraint,
                    source_type=RuntimeSourceType.VERSION_FILE,
                    source_path=".python-version",
                    confidence=Confidence.HIGH,
                    raw_version=version,
                ))

    # runtime.txt (Heroku)
    fpath = root / "runtime.txt"
    if fpath.exists():
        text = read_text(fpath)
        if text:
            version = text.strip().split("\n")[0].strip()
            if version:
                version_clean = re.sub(r"^python-", "", version, flags=re.IGNORECASE)
                constraint = parse_constraint("Python", version_clean)
                evidence.append(RuntimeEvidence(
                    runtime_evidence_id=_make_id("Python", "runtime.txt", None, version_clean),
                    ecosystem=RuntimeEcosystem.PYTHON,
                    runtime_name="Python",
                    constraint=constraint,
                    source_type=RuntimeSourceType.VERSION_FILE,
                    source_path="runtime.txt",
                    confidence=Confidence.HIGH,
                    raw_version=version_clean,
                ))

    # pyproject.toml requires-python
    fpath = root / "pyproject.toml"
    if fpath.exists():
        text = read_text(fpath)
        if text:
            m = re.search(r'requires-python\s*=\s*["\']([^"\']+)["\']', text)
            if m:
                version_spec = m.group(1)
                constraint = parse_constraint("Python", version_spec)
                evidence.append(RuntimeEvidence(
                    runtime_evidence_id=_make_id("Python", "pyproject.toml", "requires-python", version_spec),
                    ecosystem=RuntimeEcosystem.PYTHON,
                    runtime_name="Python",
                    constraint=constraint,
                    source_type=RuntimeSourceType.MANIFEST,
                    source_path="pyproject.toml",
                    source_detail="requires-python",
                    confidence=Confidence.HIGH,
                    raw_version=version_spec,
                ))

    return evidence


def detect_node_sources(root: Path) -> list[RuntimeEvidence]:
    """Detect Node.js runtime version sources."""
    evidence: list[RuntimeEvidence] = []

    for filename in (".nvmrc", ".node-version"):
        fpath = root / filename
        if fpath.exists():
            text = read_text(fpath)
            if text:
                version = text.strip().split("\n")[0].strip()
                if version:
                    constraint = parse_constraint("Node.js", version)
                    evidence.append(RuntimeEvidence(
                        runtime_evidence_id=_make_id("Node.js", filename, None, version),
                        ecosystem=RuntimeEcosystem.NODE,
                        runtime_name="Node.js",
                        constraint=constraint,
                        source_type=RuntimeSourceType.VERSION_FILE,
                        source_path=filename,
                        confidence=Confidence.HIGH,
                        raw_version=version,
                    ))

    # package.json engines.node
    pkg_json = root / "package.json"
    if pkg_json.exists():
        data = read_json(pkg_json)
        engines = data.get("engines", {})
        node_engine = engines.get("node")
        if node_engine:
            constraint = parse_constraint("Node.js", node_engine)
            evidence.append(RuntimeEvidence(
                runtime_evidence_id=_make_id("Node.js", "package.json", "engines.node", node_engine),
                ecosystem=RuntimeEcosystem.NODE,
                runtime_name="Node.js",
                constraint=constraint,
                source_type=RuntimeSourceType.MANIFEST,
                source_path="package.json",
                source_detail="engines.node",
                confidence=Confidence.HIGH,
                raw_version=node_engine,
            ))

    return evidence


def detect_ruby_sources(root: Path) -> list[RuntimeEvidence]:
    """Detect Ruby runtime version sources."""
    evidence: list[RuntimeEvidence] = []

    # .ruby-version
    fpath = root / ".ruby-version"
    if fpath.exists():
        text = read_text(fpath)
        if text:
            version = text.strip().split("\n")[0].strip()
            if version:
                constraint = parse_constraint("Ruby", version)
                evidence.append(RuntimeEvidence(
                    runtime_evidence_id=_make_id("Ruby", ".ruby-version", None, version),
                    ecosystem=RuntimeEcosystem.RUBY,
                    runtime_name="Ruby",
                    constraint=constraint,
                    source_type=RuntimeSourceType.VERSION_FILE,
                    source_path=".ruby-version",
                    confidence=Confidence.HIGH,
                    raw_version=version,
                ))

    # Gemfile ruby declaration
    fpath = root / "Gemfile"
    if fpath.exists():
        text = read_text(fpath)
        if text:
            m = re.search(r'^\s*ruby\s+["\']([^"\']+)["\']', text, re.MULTILINE)
            if m:
                version = m.group(1)
                constraint = parse_constraint("Ruby", version)
                evidence.append(RuntimeEvidence(
                    runtime_evidence_id=_make_id("Ruby", "Gemfile", "ruby", version),
                    ecosystem=RuntimeEcosystem.RUBY,
                    runtime_name="Ruby",
                    constraint=constraint,
                    source_type=RuntimeSourceType.MANIFEST,
                    source_path="Gemfile",
                    source_detail="ruby",
                    confidence=Confidence.HIGH,
                    raw_version=version,
                ))

    return evidence


def detect_java_sources(root: Path) -> list[RuntimeEvidence]:
    """Detect Java runtime version sources."""
    evidence: list[RuntimeEvidence] = []

    # .java-version
    fpath = root / ".java-version"
    if fpath.exists():
        text = read_text(fpath)
        if text:
            version = text.strip().split("\n")[0].strip()
            if version:
                constraint = parse_constraint("Java", version)
                evidence.append(RuntimeEvidence(
                    runtime_evidence_id=_make_id("Java", ".java-version", None, version),
                    ecosystem=RuntimeEcosystem.JAVA,
                    runtime_name="Java",
                    constraint=constraint,
                    source_type=RuntimeSourceType.VERSION_FILE,
                    source_path=".java-version",
                    confidence=Confidence.HIGH,
                    raw_version=version,
                ))

    # pom.xml maven.compiler.release/source
    fpath = root / "pom.xml"
    if fpath.exists():
        text = read_text(fpath)
        if text:
            m = (re.search(r"<maven\.compiler\.release>\s*(\d+)\s*</maven\.compiler\.release>", text)
                 or re.search(r"<maven\.compiler\.source>\s*(\d+)\s*</maven\.compiler\.source>", text))
            if m:
                version = m.group(1)
                constraint = parse_constraint("Java", version)
                evidence.append(RuntimeEvidence(
                    runtime_evidence_id=_make_id("Java", "pom.xml", "maven.compiler", version),
                    ecosystem=RuntimeEcosystem.JAVA,
                    runtime_name="Java",
                    constraint=constraint,
                    source_type=RuntimeSourceType.MANIFEST,
                    source_path="pom.xml",
                    source_detail="maven.compiler",
                    confidence=Confidence.HIGH,
                    raw_version=version,
                ))

    # build.gradle / build.gradle.kts
    for gradle_file in ("build.gradle", "build.gradle.kts"):
        fpath = root / gradle_file
        if fpath.exists():
            text = read_text(fpath)
            if text:
                m = (re.search(r"languageVersion\s*=\s*JavaLanguageVersion\.of\((\d+)\)", text)
                     or re.search(r"sourceCompatibility\s*=\s*JavaVersion\.VERSION_(\d+)", text))
                if m:
                    version = m.group(1)
                    constraint = parse_constraint("Java", version)
                    evidence.append(RuntimeEvidence(
                        runtime_evidence_id=_make_id("Java", gradle_file, "java-version", version),
                        ecosystem=RuntimeEcosystem.JAVA,
                        runtime_name="Java",
                        constraint=constraint,
                        source_type=RuntimeSourceType.MANIFEST,
                        source_path=gradle_file,
                        confidence=Confidence.HIGH,
                        raw_version=version,
                    ))
                break

    return evidence
