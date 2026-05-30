"""Runtime version pin detection and conflict analysis.

v3.3.0: Initial Python + Node.js detection.
v3.4.0: Extracted from scanner.py.
v3.8.0: Conflict detection, Ruby, Java, Dockerfile, GitHub Actions,
        constraint kind model, per-ecosystem normalization.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from pharabius.core.constants import (
    COMPLETENESS_COMPLETE,
    COMPLETENESS_PARTIAL,
    EVIDENCE_RUNTIME_VERSION_SIGNAL,
    OBSERVATION_STRENGTH_DIRECT,
    OBSERVATION_STRENGTH_HEURISTIC,
    OBSERVATION_STRENGTH_LIMITATION,
    PARSER_FILESYSTEM,
    PARSER_MANIFEST,
    RUNTIME_SIGNAL_CONFLICT,
    RUNTIME_SIGNAL_FROM_CI,
    RUNTIME_SIGNAL_FROM_CONTAINER,
    RUNTIME_SIGNAL_MISSING,
    RUNTIME_SIGNAL_PARTIAL,
    RUNTIME_SIGNAL_PINNED,
    READ_MODE_JSON,
    READ_MODE_SKIPPED,
    READ_MODE_TEXT,
    READ_MODE_YAML,
)
from pharabius.core.io_helpers import read_json, read_text
from pharabius.schemas.evidence import EvidenceBuilder


# ── Version normalization ────────────────────────────────────────────


def normalize_runtime_version(runtime: str, raw: str) -> tuple[str | None, str]:
    """Normalize a runtime version string.

    Returns (normalized_version, constraint_kind).
    normalized_version is None if the version is ambiguous/unparseable.
    constraint_kind is one of: "exact", "range", "partial", "unknown".
    """

    # Detect ranges first
    raw = raw.strip()
    if not raw or raw in ("*", "latest"):
        return None, "range"

    # Range patterns: >=X.Y, ~> X.Y, ^X.Y, X.Y.x, >=X
    if re.match(r'^[><~^]', raw) or '.x' in raw.lower():
        return _normalize_range(runtime, raw)

    # Strip common prefixes
    cleaned = re.sub(r'^(python-|ruby-|v|temurin-|adoptopenjdk-|corretto-)', '', raw, flags=re.IGNORECASE)

    # Extract version number
    match = re.match(r'(\d+)(?:\.(\d+))?', cleaned)
    if not match:
        return None, "unknown"

    major = match.group(1)
    minor = match.group(2)

    # Runtime-specific normalization
    if runtime == "Node.js":
        return major, "exact"  # Node: major only
    elif runtime == "Java":
        return major, "exact"  # Java: major only
    elif runtime in ("Python", "Ruby"):
        if minor is not None:
            return f"{major}.{minor}", "exact"
        return major, "exact"  # Single number like "3" → "3"
    else:
        if minor is not None:
            return f"{major}.{minor}", "exact"
        return major, "exact"


def _normalize_range(runtime: str, raw: str) -> tuple[str | None, str]:
    """Normalize a range constraint. Returns (lower_bound_or_None, "range")."""
    # >=X.Y or >=X
    m = re.match(r'>=?\s*(\d+)(?:\.(\d+))?', raw)
    if m:
        major = m.group(1)
        minor = m.group(2)
        if minor is not None:
            return f"{major}.{minor}", "range"
        return major, "range"

    # ~> X.Y (Ruby pessimistic constraint)
    m = re.match(r'~>\s*(\d+)\.(\d+)', raw)
    if m:
        return f"{m.group(1)}.{m.group(2)}", "range"

    # ^X.Y
    m = re.match(r'\^\s*(\d+)(?:\.(\d+))?', raw)
    if m:
        major = m.group(1)
        minor = m.group(2)
        if minor is not None:
            return f"{major}.{minor}", "range"
        return major, "range"

    # X.Y.x
    m = re.match(r'(\d+)\.(\d+)\.x', raw, re.IGNORECASE)
    if m:
        return f"{m.group(1)}.{m.group(2)}", "range"

    return None, "range"


def _range_excludes_exact(range_spec: str, range_lower: str | None,
                          exact_version: str, exact_normalized: str) -> bool:
    """Check if a range clearly excludes an exact version.

    Only handles simple cases. Returns True if conflict is definite.
    """
    if range_lower is None:
        return False  # Cannot determine

    # Compare major versions first
    range_major = int(re.match(r'(\d+)', range_lower).group(1))
    exact_major = int(re.match(r'(\d+)', exact_normalized).group(1))

    # If range requires >=X and exact is < X, it's a conflict
    if exact_major < range_major:
        return True

    # Same major: compare minor if available
    if exact_major == range_major:
        range_m = re.match(r'\d+\.(\d+)', range_lower)
        exact_m = re.match(r'\d+\.(\d+)', exact_normalized)
        if range_m and exact_m:
            if int(exact_m.group(1)) < int(range_m.group(1)):
                return True

    return False


# ── Source tracking ──────────────────────────────────────────────────


class _RuntimeSource:
    """Tracks a single runtime version declaration."""

    __slots__ = ("runtime", "source_file", "source_kind",
                 "raw_version", "normalized", "constraint_kind")

    def __init__(
        self,
        runtime: str,
        source_file: str,
        source_kind: str,
        raw_version: str,
    ) -> None:
        self.runtime = runtime
        self.source_file = source_file
        self.source_kind = source_kind
        self.raw_version = raw_version
        self.normalized, self.constraint_kind = normalize_runtime_version(runtime, raw_version)


# ── Main detection entry point ───────────────────────────────────────


def detect_runtime_version_pins(root: Path, builder: EvidenceBuilder) -> None:
    """Detect runtime version pinning and conflicts at repository level.

    v3.3.0: Python + Node.js only.
    v3.8.0: Python, Node.js, Ruby, Java + conflict detection + Dockerfile + CI.
    """
    sources: list[_RuntimeSource] = []

    # ── Version files ────────────────────────────────────────────────
    _detect_version_files(root, sources, builder)
    _detect_tool_versions(root, sources, builder)
    _detect_manifest_runtimes(root, sources, builder)
    _detect_runtime_txt(root, sources, builder)
    _detect_pyproject_requires_python(root, sources, builder)
    _detect_gemfile_ruby(root, sources, builder)
    _detect_maven_java(root, sources, builder)
    _detect_gradle_java(root, sources, builder)

    # ── Container / CI evidence ──────────────────────────────────────
    _detect_dockerfile_runtimes(root, sources, builder)
    _detect_ci_runtimes(root, sources, builder)

    # ── Conflict detection ──────────────────────────────────────────
    _detect_runtime_conflicts(sources, builder)

    # ── Missing runtime pins ────────────────────────────────────────
    _detect_missing_runtime_pins(root, sources, builder)


# ── Version file detection ───────────────────────────────────────────


_VERSION_FILES: list[tuple[str, str]] = [
    (".python-version", "Python"),
    (".nvmrc", "Node.js"),
    (".node-version", "Node.js"),
    (".ruby-version", "Ruby"),
    (".java-version", "Java"),
]


def _detect_version_files(
    root: Path, sources: list[_RuntimeSource], builder: EvidenceBuilder,
) -> None:
    for filename, runtime in _VERSION_FILES:
        fpath = root / filename
        if not fpath.exists():
            continue
        text = read_text(fpath)
        if not text:
            continue
        version = text.strip().split("\n")[0].strip()
        if not version:
            continue
        src = _RuntimeSource(runtime, filename, "version_file", version)
        sources.append(src)
        builder.add(
            type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
            category="dependencies",
            summary=f"{runtime} runtime version pinned: {version}",
            location_file=filename,
            subject=runtime,
            raw_observation=f"{runtime}:{version}",
            confidence="High",
            metadata={
                "signal": RUNTIME_SIGNAL_PINNED,
                "runtime": runtime,
                "version": version,
                "constraint_kind": src.constraint_kind,
                "source_file": filename,
                "source_kind": "version_file",
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_FILESYSTEM,
                "read_mode": READ_MODE_TEXT,
            },
        )


# ── .tool-versions ───────────────────────────────────────────────────

_TOOL_VERSIONS_RUNTIME_MAP = {
    "python": "Python",
    "nodejs": "Node.js",
    "ruby": "Ruby",
    "java": "Java",
}


def _detect_tool_versions(
    root: Path, sources: list[_RuntimeSource], builder: EvidenceBuilder,
) -> None:
    fpath = root / ".tool-versions"
    if not fpath.exists():
        return
    text = read_text(fpath)
    if not text:
        return

    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        tool, version = parts
        runtime = _TOOL_VERSIONS_RUNTIME_MAP.get(tool.lower())
        if not runtime:
            continue
        src = _RuntimeSource(runtime, ".tool-versions", "tool_versions", version)
        sources.append(src)
        builder.add(
            type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
            category="dependencies",
            summary=f"{runtime} runtime version pinned via .tool-versions: {version}",
            location_file=".tool-versions",
            subject=runtime,
            raw_observation=f"{runtime}:{version}:tool-versions",
            confidence="High",
            metadata={
                "signal": RUNTIME_SIGNAL_PINNED,
                "runtime": runtime,
                "version": version,
                "constraint_kind": src.constraint_kind,
                "source_file": ".tool-versions",
                "source_kind": "tool_versions",
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_FILESYSTEM,
                "read_mode": READ_MODE_TEXT,
            },
        )


# ── Manifest runtimes (package.json engines) ─────────────────────────


def _detect_manifest_runtimes(
    root: Path, sources: list[_RuntimeSource], builder: EvidenceBuilder,
) -> None:
    # package.json engines.node
    pkg_json = root / "package.json"
    if pkg_json.exists():
        data = read_json(pkg_json)
        engines = data.get("engines", {})
        node_engine = engines.get("node")
        if node_engine:
            src = _RuntimeSource("Node.js", "package.json", "manifest", node_engine)
            sources.append(src)
            builder.add(
                type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
                category="dependencies",
                summary=f"Node.js runtime version in package.json: {node_engine}",
                location_file="package.json",
                subject="Node.js",
                raw_observation=f"Node.js:{node_engine}:engines",
                confidence="High",
                metadata={
                    "signal": RUNTIME_SIGNAL_PINNED,
                    "runtime": "Node.js",
                    "version": node_engine,
                    "constraint_kind": src.constraint_kind,
                    "source_file": "package.json",
                    "source_kind": "manifest",
                    "source_field": "engines.node",
                    "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                    "completeness": COMPLETENESS_COMPLETE,
                    "parser": PARSER_MANIFEST,
                    "read_mode": READ_MODE_JSON,
                },
            )


# ── runtime.txt (Heroku/Flask) ───────────────────────────────────────


def _detect_runtime_txt(
    root: Path, sources: list[_RuntimeSource], builder: EvidenceBuilder,
) -> None:
    fpath = root / "runtime.txt"
    if not fpath.exists():
        return
    text = read_text(fpath)
    if not text:
        return
    version = text.strip().split("\n")[0].strip()
    if not version:
        return
    # Strip "python-" prefix common in Heroku runtime.txt
    version_clean = re.sub(r'^python-', '', version, flags=re.IGNORECASE)
    src = _RuntimeSource("Python", "runtime.txt", "version_file", version_clean)
    sources.append(src)
    builder.add(
        type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
        category="dependencies",
        summary=f"Python runtime version from runtime.txt: {version_clean}",
        location_file="runtime.txt",
        subject="Python",
        raw_observation=f"Python:{version_clean}:runtime.txt",
        confidence="High",
        metadata={
            "signal": RUNTIME_SIGNAL_PINNED,
            "runtime": "Python",
            "version": version_clean,
            "constraint_kind": src.constraint_kind,
            "source_file": "runtime.txt",
            "source_kind": "version_file",
            "observation_strength": OBSERVATION_STRENGTH_DIRECT,
            "completeness": COMPLETENESS_COMPLETE,
            "parser": PARSER_FILESYSTEM,
            "read_mode": READ_MODE_TEXT,
        },
    )


# ── pyproject.toml requires-python ────────────────────────────────────


def _detect_pyproject_requires_python(
    root: Path, sources: list[_RuntimeSource], builder: EvidenceBuilder,
) -> None:
    fpath = root / "pyproject.toml"
    if not fpath.exists():
        return
    text = read_text(fpath)
    if not text:
        return
    # Conservative regex extraction — no TOML parser dependency
    m = re.search(r'requires-python\s*=\s*["\']([^"\']+)["\']', text)
    if not m:
        return
    version_spec = m.group(1)
    src = _RuntimeSource("Python", "pyproject.toml", "manifest", version_spec)
    sources.append(src)
    builder.add(
        type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
        category="dependencies",
        summary=f"Python requires-python from pyproject.toml: {version_spec}",
        location_file="pyproject.toml",
        subject="Python",
        raw_observation=f"Python:{version_spec}:requires-python",
        confidence="High",
        metadata={
            "signal": RUNTIME_SIGNAL_PINNED,
            "runtime": "Python",
            "version": version_spec,
            "constraint_kind": src.constraint_kind,
            "source_file": "pyproject.toml",
            "source_kind": "manifest",
            "source_field": "requires-python",
            "observation_strength": OBSERVATION_STRENGTH_DIRECT,
            "completeness": COMPLETENESS_COMPLETE,
            "parser": PARSER_FILESYSTEM,
            "read_mode": READ_MODE_TEXT,
        },
    )


# ── Gemfile ruby declaration ─────────────────────────────────────────


_RUBY_DECL = re.compile(r'^\s*ruby\s+["\']([^"\']+)["\']', re.MULTILINE)


def _detect_gemfile_ruby(
    root: Path, sources: list[_RuntimeSource], builder: EvidenceBuilder,
) -> None:
    fpath = root / "Gemfile"
    if not fpath.exists():
        return
    text = read_text(fpath)
    if not text:
        return
    m = _RUBY_DECL.search(text)
    if not m:
        return
    version = m.group(1)
    src = _RuntimeSource("Ruby", "Gemfile", "manifest", version)
    sources.append(src)
    builder.add(
        type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
        category="dependencies",
        summary=f"Ruby runtime version from Gemfile: {version}",
        location_file="Gemfile",
        subject="Ruby",
        raw_observation=f"Ruby:{version}:Gemfile",
        confidence="High",
        metadata={
            "signal": RUNTIME_SIGNAL_PINNED,
            "runtime": "Ruby",
            "version": version,
            "constraint_kind": src.constraint_kind,
            "source_file": "Gemfile",
            "source_kind": "manifest",
            "observation_strength": OBSERVATION_STRENGTH_DIRECT,
            "completeness": COMPLETENESS_COMPLETE,
            "parser": PARSER_FILESYSTEM,
            "read_mode": READ_MODE_TEXT,
        },
    )


# ── Maven compiler settings ──────────────────────────────────────────


_MAVEN_RELEASE = re.compile(r'<maven\.compiler\.release>\s*(\d+)\s*</maven\.compiler\.release>')
_MAVEN_SOURCE = re.compile(r'<maven\.compiler\.source>\s*(\d+)\s*</maven\.compiler\.source>')


def _detect_maven_java(
    root: Path, sources: list[_RuntimeSource], builder: EvidenceBuilder,
) -> None:
    fpath = root / "pom.xml"
    if not fpath.exists():
        return
    text = read_text(fpath)
    if not text:
        return

    # Prefer maven.compiler.release, fall back to source
    m = _MAVEN_RELEASE.search(text) or _MAVEN_SOURCE.search(text)
    if not m:
        return
    version = m.group(1)
    src = _RuntimeSource("Java", "pom.xml", "manifest", version)
    sources.append(src)
    builder.add(
        type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
        category="dependencies",
        summary=f"Java runtime version from Maven compiler settings: {version}",
        location_file="pom.xml",
        subject="Java",
        raw_observation=f"Java:{version}:maven.compiler",
        confidence="High",
        metadata={
            "signal": RUNTIME_SIGNAL_PINNED,
            "runtime": "Java",
            "version": version,
            "constraint_kind": src.constraint_kind,
            "source_file": "pom.xml",
            "source_kind": "manifest",
            "observation_strength": OBSERVATION_STRENGTH_DIRECT,
            "completeness": COMPLETENESS_COMPLETE,
            "parser": PARSER_FILESYSTEM,
            "read_mode": READ_MODE_TEXT,
        },
    )


# ── Gradle Java version ──────────────────────────────────────────────


_GRADLE_COMPAT = re.compile(r'sourceCompatibility\s*=\s*JavaVersion\.VERSION_(\d+)')
_GRADLE_TOOLCHAIN = re.compile(r'languageVersion\s*=\s*JavaLanguageVersion\.of\((\d+)\)')


def _detect_gradle_java(
    root: Path, sources: list[_RuntimeSource], builder: EvidenceBuilder,
) -> None:
    for gradle_file in ["build.gradle", "build.gradle.kts"]:
        fpath = root / gradle_file
        if not fpath.exists():
            continue
        text = read_text(fpath)
        if not text:
            continue

        m = _GRADLE_TOOLCHAIN.search(text) or _GRADLE_COMPAT.search(text)
        if not m:
            continue
        version = m.group(1)
        src = _RuntimeSource("Java", gradle_file, "manifest", version)
        sources.append(src)
        builder.add(
            type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
            category="dependencies",
            summary=f"Java runtime version from {gradle_file}: {version}",
            location_file=gradle_file,
            subject="Java",
            raw_observation=f"Java:{version}:{gradle_file}",
            confidence="High",
            metadata={
                "signal": RUNTIME_SIGNAL_PINNED,
                "runtime": "Java",
                "version": version,
                "constraint_kind": src.constraint_kind,
                "source_file": gradle_file,
                "source_kind": "manifest",
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_FILESYSTEM,
                "read_mode": READ_MODE_TEXT,
            },
        )
        break  # Only process first matching gradle file


# ── Dockerfile runtime evidence ──────────────────────────────────────


_FROM_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'FROM\s+python:(\d+(?:\.\d+)?)'), "Python"),
    (re.compile(r'FROM\s+node:(\d+(?:\.\d+)?)'), "Node.js"),
    (re.compile(r'FROM\s+ruby:(\d+(?:\.\d+)?)'), "Ruby"),
    (re.compile(r'FROM\s+eclipse-temurin[\-\:]?[\w]*?(\d+)'), "Java"),
    (re.compile(r'FROM\s+openjdk[\-\:]?[\w]*?(\d+)'), "Java"),
    (re.compile(r'FROM\s+maven:\S*?[\-_](\d+)'), "Java"),
    (re.compile(r'FROM\s+gradle:\S*?[\-_]jdk(\d+)'), "Java"),
]


def _detect_dockerfile_runtimes(
    root: Path, sources: list[_RuntimeSource], builder: EvidenceBuilder,
) -> None:
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

            # Check for ARG-based FROM (partial)
            if "${" in line:
                # ARG-driven — try to detect runtime name without version
                _RUNTIME_NAME_PATTERNS = [
                    (re.compile(r'FROM\s+python[:\s]'), "Python"),
                    (re.compile(r'FROM\s+node[:\s]'), "Node.js"),
                    (re.compile(r'FROM\s+ruby[:\s]'), "Ruby"),
                    (re.compile(r'FROM\s+(eclipse-temurin|openjdk|maven|gradle)[:\-_]'), "Java"),
                ]
                for name_pat, runtime in _RUNTIME_NAME_PATTERNS:
                    if name_pat.search(line):
                        builder.add(
                            type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
                            category="dependencies",
                            summary=f"{runtime} runtime from Dockerfile (ARG-driven, version unknown)",
                            location_file=rel_path,
                            subject=runtime,
                            raw_observation=f"{runtime}:partial:dockerfile",
                            confidence="Low",
                            metadata={
                                "signal": RUNTIME_SIGNAL_PARTIAL,
                                "runtime": runtime,
                                "constraint_kind": "partial",
                                "source_file": rel_path,
                                "source_kind": "container",
                                "observation_strength": OBSERVATION_STRENGTH_HEURISTIC,
                                "completeness": COMPLETENESS_PARTIAL,
                                "parser": PARSER_FILESYSTEM,
                                "read_mode": READ_MODE_TEXT,
                            },
                        )
                continue

            # Check for specific version FROM
            for pattern, runtime in _FROM_PATTERNS:
                m = pattern.search(line)
                if m:
                    version = m.group(1)
                    src = _RuntimeSource(runtime, rel_path, "container", version)
                    sources.append(src)
                    builder.add(
                        type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
                        category="dependencies",
                        summary=f"{runtime} runtime from Dockerfile: {version}",
                        location_file=rel_path,
                        subject=runtime,
                        raw_observation=f"{runtime}:{version}:dockerfile",
                        confidence="Medium",
                        metadata={
                            "signal": RUNTIME_SIGNAL_FROM_CONTAINER,
                            "runtime": runtime,
                            "version": version,
                            "constraint_kind": src.constraint_kind,
                            "source_file": rel_path,
                            "source_kind": "container",
                            "observation_strength": OBSERVATION_STRENGTH_HEURISTIC,
                            "completeness": COMPLETENESS_PARTIAL,
                            "parser": PARSER_FILESYSTEM,
                            "read_mode": READ_MODE_TEXT,
                        },
                    )


# ── GitHub Actions runtime evidence ──────────────────────────────────


_GH_SETUP_ACTIONS: dict[str, tuple[str, str]] = {
    "actions/setup-python": ("python-version", "Python"),
    "actions/setup-node": ("node-version", "Node.js"),
    "ruby/setup-ruby": ("ruby-version", "Ruby"),
    "actions/setup-java": ("java-version", "Java"),
}


def _detect_ci_runtimes(
    root: Path, sources: list[_RuntimeSource], builder: EvidenceBuilder,
) -> None:
    workflows_dir = root / ".github" / "workflows"
    if not workflows_dir.exists():
        return

    for wf_path in sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml")):
        _parse_github_workflow(root, wf_path, sources, builder)


def _parse_github_workflow(
    root: Path,
    wf_path: Path,
    sources: list[_RuntimeSource],
    builder: EvidenceBuilder,
) -> None:
    rel_path = str(wf_path.relative_to(root)).replace("\\", "/")
    text = read_text(wf_path)
    if not text:
        return

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        # Malformed workflow — emit partial evidence and continue
        builder.add(
            type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
            category="dependencies",
            summary="CI workflow file could not be parsed",
            location_file=rel_path,
            subject="CI",
            raw_observation="ci:malformed_yaml",
            confidence="Low",
            metadata={
                "signal": RUNTIME_SIGNAL_PARTIAL,
                "runtime": "unknown",
                "constraint_kind": "partial",
                "source_file": rel_path,
                "source_kind": "ci",
                "observation_strength": OBSERVATION_STRENGTH_LIMITATION,
                "completeness": COMPLETENESS_PARTIAL,
                "parser": PARSER_FILESYSTEM,
                "read_mode": READ_MODE_YAML,
            },
        )
        return

    if not isinstance(data, dict):
        return

    jobs = data.get("jobs", {})
    if not isinstance(jobs, dict):
        return

    for _job_name, job_data in jobs.items():
        if not isinstance(job_data, dict):
            continue
        steps = job_data.get("steps", [])
        if not isinstance(steps, list):
            continue

        for step in steps:
            if not isinstance(step, dict):
                continue
            uses = step.get("uses", "")
            if not isinstance(uses, str):
                continue

            # Match setup actions (handle versioned uses like "actions/setup-python@v5")
            uses_base = uses.split("@")[0]
            action_info = _GH_SETUP_ACTIONS.get(uses_base)
            if not action_info:
                continue

            version_key, runtime = action_info
            with_data = step.get("with", {})
            if not isinstance(with_data, dict):
                continue

            version_val = with_data.get(version_key)
            if version_val is None:
                continue

            # Handle matrix expressions → partial
            version_str = str(version_val)
            if "${{" in version_str:
                builder.add(
                    type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
                    category="dependencies",
                    summary=f"{runtime} runtime from CI (matrix/expr, version undetermined)",
                    location_file=rel_path,
                    subject=runtime,
                    raw_observation=f"{runtime}:partial:ci",
                    confidence="Low",
                    metadata={
                        "signal": RUNTIME_SIGNAL_PARTIAL,
                        "runtime": runtime,
                        "constraint_kind": "partial",
                        "source_file": rel_path,
                        "source_kind": "ci",
                        "observation_strength": OBSERVATION_STRENGTH_HEURISTIC,
                        "completeness": COMPLETENESS_PARTIAL,
                        "parser": PARSER_FILESYSTEM,
                        "read_mode": READ_MODE_YAML,
                    },
                )
                continue

            # Handle list of versions → emit one per version, all partial
            if isinstance(version_val, list):
                for v in version_val:
                    v_str = str(v)
                    builder.add(
                        type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
                        category="dependencies",
                        summary=f"{runtime} runtime from CI matrix: {v_str}",
                        location_file=rel_path,
                        subject=runtime,
                        raw_observation=f"{runtime}:{v_str}:ci_matrix",
                        confidence="Low",
                        metadata={
                            "signal": RUNTIME_SIGNAL_PARTIAL,
                            "runtime": runtime,
                            "version": v_str,
                            "constraint_kind": "partial",
                            "source_file": rel_path,
                            "source_kind": "ci",
                            "observation_strength": OBSERVATION_STRENGTH_HEURISTIC,
                            "completeness": COMPLETENESS_PARTIAL,
                            "parser": PARSER_FILESYSTEM,
                            "read_mode": READ_MODE_YAML,
                        },
                    )
                continue

            # Exact version from CI
            src = _RuntimeSource(runtime, rel_path, "ci", version_str)
            sources.append(src)
            builder.add(
                type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
                category="dependencies",
                summary=f"{runtime} runtime from CI ({uses_base}): {version_str}",
                location_file=rel_path,
                subject=runtime,
                raw_observation=f"{runtime}:{version_str}:ci",
                confidence="Medium",
                metadata={
                    "signal": RUNTIME_SIGNAL_FROM_CI,
                    "runtime": runtime,
                    "version": version_str,
                    "constraint_kind": src.constraint_kind,
                    "source_file": rel_path,
                    "source_kind": "ci",
                    "action": uses_base,
                    "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                    "completeness": COMPLETENESS_COMPLETE,
                    "parser": PARSER_FILESYSTEM,
                    "read_mode": READ_MODE_YAML,
                },
            )


# ── Conflict detection ───────────────────────────────────────────────


def _detect_runtime_conflicts(
    sources: list[_RuntimeSource], builder: EvidenceBuilder,
) -> None:
    """Detect runtime version conflicts across all sources.

    One conflict evidence item per runtime, grouped.
    Only flags definite conflicts (exact vs exact disagreement, or range excludes exact).
    """
    # Group sources by runtime
    by_runtime: dict[str, list[_RuntimeSource]] = {}
    for src in sources:
        by_runtime.setdefault(src.runtime, []).append(src)

    for runtime, rt_sources in by_runtime.items():
        exact_sources = [s for s in rt_sources if s.constraint_kind == "exact" and s.normalized]
        range_sources = [s for s in rt_sources if s.constraint_kind == "range"]
        # partial/unknown never participate in conflicts

        if len(exact_sources) < 2 and not (exact_sources and range_sources):
            continue

        # Check exact vs exact
        exact_conflicts: list[_RuntimeSource] = []
        if len(exact_sources) >= 2:
            normalized_versions = set(s.normalized for s in exact_sources)
            if len(normalized_versions) > 1:
                exact_conflicts = exact_sources

        # Check range vs exact
        range_exact_conflicts: list[_RuntimeSource] = []
        if not exact_conflicts and exact_sources and range_sources:
            exact_src = exact_sources[0]
            for rng in range_sources:
                if rng.normalized is not None and exact_src.normalized is not None:
                    if _range_excludes_exact(
                        rng.raw_version, rng.normalized,
                        exact_src.raw_version, exact_src.normalized,
                    ):
                        range_exact_conflicts = [exact_src, rng]
                        break

        conflict_sources = exact_conflicts or range_exact_conflicts
        if not conflict_sources:
            continue

        conflict_reason = (
            "exact_vs_exact_disagreement"
            if exact_conflicts
            else "range_excludes_exact"
        )

        sources_meta = [
            {
                "source_file": s.source_file,
                "source_kind": s.source_kind,
                "version": s.raw_version,
                "normalized": s.normalized,
                "constraint_kind": s.constraint_kind,
            }
            for s in conflict_sources
        ]

        builder.add(
            type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
            category="dependencies",
            summary=f"{runtime} runtime version declarations conflict",
            location_file=".",
            subject=runtime,
            raw_observation=f"{runtime}:conflict:{conflict_reason}",
            confidence="High",
            metadata={
                "signal": RUNTIME_SIGNAL_CONFLICT,
                "runtime": runtime,
                "sources": sources_meta,
                "conflict_reason": conflict_reason,
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_FILESYSTEM,
                "read_mode": READ_MODE_TEXT,
            },
        )


# ── Missing runtime pin detection ────────────────────────────────────


_MISSING_PIN_TRIGGERS: dict[str, list[str]] = {
    "Python": ["pyproject.toml", "requirements.txt", "setup.py", "Pipfile", "runtime.txt"],
    "Node.js": ["package.json"],
    "Ruby": ["Gemfile", ".gemspec"],
    "Java": ["pom.xml", "build.gradle", "build.gradle.kts"],
}


def _detect_missing_runtime_pins(
    root: Path, sources: list[_RuntimeSource], builder: EvidenceBuilder,
) -> None:
    """Emit advisory evidence when manifests exist but runtime pins are missing.

    Trigger is manifest-based only. Source files alone do NOT trigger advisories.
    """
    detected_runtimes = {s.runtime for s in sources}

    for runtime, trigger_files in _MISSING_PIN_TRIGGERS.items():
        if runtime in detected_runtimes:
            continue
        has_trigger = any((root / f).exists() for f in trigger_files)
        if not has_trigger:
            continue

        builder.add(
            type_=EVIDENCE_RUNTIME_VERSION_SIGNAL,
            category="dependencies",
            summary=f"{runtime} manifest detected without runtime version pin",
            location_file=".",
            subject=runtime,
            raw_observation=f"runtime_version_missing:{runtime}",
            confidence="Medium",
            metadata={
                "signal": RUNTIME_SIGNAL_MISSING,
                "runtime": runtime,
                "observation_strength": OBSERVATION_STRENGTH_LIMITATION,
                "completeness": COMPLETENESS_PARTIAL,
                "parser": PARSER_FILESYSTEM,
                "read_mode": READ_MODE_SKIPPED,
            },
        )
