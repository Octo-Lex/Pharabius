"""Dependency manifest parsers and lockfile consistency checks.

Extracted from scanner.py in v3.4.0. Handles manifest parsing, unpinned
dependency detection, and lockfile consistency verification.
"""

from __future__ import annotations

from pathlib import Path

from pharabius.core.constants import (
    COMPLETENESS_COMPLETE,
    COMPLETENESS_PARTIAL,
    EVIDENCE_DEPENDENCY_SIGNAL,
    OBSERVATION_STRENGTH_DIRECT,
    OBSERVATION_STRENGTH_LIMITATION,
    PARSER_FILESYSTEM,
    PARSER_MANIFEST,
    READ_MODE_JSON,
    READ_MODE_SKIPPED,
    READ_MODE_TEXT,
)
from pharabius.core.dependency_utils import classify_python_specifier
from pharabius.core.io_helpers import read_json, read_text
from pharabius.schemas.evidence import EvidenceBuilder


def scan_dependency_manifest(
    file_path: Path,
    relative: str,
    builder: EvidenceBuilder,
) -> bool:
    """Parse a dependency manifest file for signals.

    Returns True if the file was a supported dependency manifest.
    Returns False if the file is not a recognized manifest.
    """
    name = file_path.name
    if name == "package.json":
        _check_node_unpinned_deps(file_path, relative, builder)
        return True
    if name == "requirements.txt":
        _check_python_unpinned_deps(file_path, relative, builder)
        return True
    if name == "pyproject.toml":
        _parse_pyproject_deps(file_path, relative, builder)
        return True
    if name == "Pipfile":
        _parse_pipfile_deps(file_path, relative, builder)
        return True
    return False


def scan_repository_dependency_consistency(
    root: Path,
    builder: EvidenceBuilder,
) -> None:
    """Check repository-level dependency consistency (lockfiles, etc.)."""
    _check_node_lockfile_conflicts(root, builder)
    _check_poetry_lockfile(root, builder)
    _check_pipfile_lockfile(root, builder)


def _parse_dep_name(dep_str: str) -> str:
    """Extract package name from a PEP 508 dependency string."""
    name = dep_str
    for ch in (">", "<", "~", "=", "!", " ", "\t", ";", "[", "("):
        name = name.split(ch)[0]
    return name.strip()


def _check_node_unpinned_deps(
    file_path: Path,
    relative: str,
    builder: EvidenceBuilder,
) -> None:
    """Check package.json for unpinned or broad version ranges."""
    data = read_json(file_path)
    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
    unpinned: list[dict[str, str]] = []
    for name, version in deps.items():
        if not isinstance(version, str):
            continue
        if (
            version in ("*", "latest", "")
            or version.startswith(">")
            or version.startswith("<")
            or version.startswith("~")
        ):
            unpinned.append({"name": name, "specifier": version})
    if unpinned:
        builder.add(
            type_=EVIDENCE_DEPENDENCY_SIGNAL,
            category="dependencies",
            summary=f"Unpinned Node.js dependencies in {relative}",
            location_file=relative,
            subject=relative,
            raw_observation=f"unpinned:{len(unpinned)}",
            confidence="High",
            metadata={
                "signal": "unpinned_dependency",
                "ecosystem": "Node.js",
                "count": len(unpinned),
                "examples": unpinned[:10],
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_MANIFEST,
                "read_mode": READ_MODE_JSON,
            },
        )


def _check_python_unpinned_deps(
    file_path: Path,
    relative: str,
    builder: EvidenceBuilder,
) -> None:
    """Check requirements.txt for unpinned version specifiers.

    Pinned: package==1.2.3, package===1.2.3, package @ file://...
    Unpinned/broad: package, package>=1.0, package~=1.2, package<3
    """
    text = read_text(file_path)
    if not text:
        return
    unpinned: list[dict[str, str]] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Remove environment markers
        if ";" in line:
            line = line.split(";")[0].strip()
        # Remove extras
        if "[" in line and "]" in line:
            base = line.split("[")[0]
            rest = line.split("]", 1)[1]
            line = base + rest
        # Check pinning
        if "==" in line or "===" in line or " @ " in line:
            continue  # Pinned
        # Anything else with a name is unpinned
        name = line
        for ch in (">", "<", "~", "=", "!", " ", "\t"):
            name = name.split(ch)[0]
        name = name.strip()
        if name:
            unpinned.append({"name": name, "specifier": line})
    if unpinned:
        builder.add(
            type_=EVIDENCE_DEPENDENCY_SIGNAL,
            category="dependencies",
            summary=f"Unpinned Python dependencies in {relative}",
            location_file=relative,
            subject=relative,
            raw_observation=f"unpinned:{len(unpinned)}",
            confidence="High",
            metadata={
                "signal": "unpinned_dependency",
                "ecosystem": "Python",
                "count": len(unpinned),
                "examples": unpinned[:10],
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_MANIFEST,
                "read_mode": READ_MODE_TEXT,
            },
        )


def _parse_pyproject_deps(
    file_path: Path,
    relative: str,
    builder: EvidenceBuilder,
) -> None:
    """Parse pyproject.toml for dependency signals."""

    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        text = read_text(file_path)
        data = tomllib.loads(text)
    except Exception:
        builder.add(
            type_=EVIDENCE_DEPENDENCY_SIGNAL,
            category="dependencies",
            summary=f"Could not parse {relative}",
            location_file=relative,
            subject=relative,
            raw_observation="dependency_manifest_parse_failure",
            confidence="Low",
            metadata={
                "signal": "dependency_manifest_parse_failure",
                "ecosystem": "Python",
                "manifest": "pyproject.toml",
                "reason": "toml_parse_error",
                "observation_strength": OBSERVATION_STRENGTH_LIMITATION,
                "completeness": COMPLETENESS_PARTIAL,
                "parser": PARSER_MANIFEST,
                "read_mode": READ_MODE_TEXT,
            },
        )
        return

    unpinned: list[dict[str, str]] = []
    sections_found: list[str] = []

    # PEP 621 [project].dependencies
    project_deps = data.get("project", {}).get("dependencies", [])
    if project_deps:
        sections_found.append("project.dependencies")
        for dep_str in project_deps:
            name = _parse_dep_name(dep_str)
            if classify_python_specifier(dep_str, "pep508") != "pinned":
                unpinned.append(
                    {"name": name, "specifier": dep_str, "section": "project.dependencies"}
                )

    # PEP 621 [project].optional-dependencies
    opt_deps = data.get("project", {}).get("optional-dependencies", {})
    if opt_deps:
        sections_found.append("project.optional-dependencies")
        for group, deps in opt_deps.items():
            for dep_str in deps:
                name = _parse_dep_name(dep_str)
                if classify_python_specifier(dep_str, "pep508") != "pinned":
                    unpinned.append(
                        {
                            "name": name,
                            "specifier": dep_str,
                            "section": f"project.optional-dependencies.{group}",
                        }
                    )

    # Poetry [tool.poetry.dependencies]
    poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    if poetry_deps:
        sections_found.append("tool.poetry.dependencies")
        for name, version in poetry_deps.items():
            if name.lower() == "python":
                continue
            v = version if isinstance(version, str) else version.get("version", "")
            if classify_python_specifier(str(v), "poetry") != "pinned":
                unpinned.append(
                    {"name": name, "specifier": str(version), "section": "tool.poetry.dependencies"}
                )

    # Poetry [tool.poetry.group.*.dependencies]
    poetry_groups = data.get("tool", {}).get("poetry", {}).get("group", {})
    for group_name, group_data in poetry_groups.items():
        group_deps = group_data.get("dependencies", {})
        if group_deps:
            sections_found.append(f"tool.poetry.group.{group_name}.dependencies")
            for name, version in group_deps.items():
                v = version if isinstance(version, str) else version.get("version", "")
                if classify_python_specifier(str(v), "poetry") != "pinned":
                    unpinned.append(
                        {
                            "name": name,
                            "specifier": str(version),
                            "section": f"tool.poetry.group.{group_name}.dependencies",
                        }
                    )

    # Poetry [tool.poetry.dev-dependencies] (legacy)
    dev_deps = data.get("tool", {}).get("poetry", {}).get("dev-dependencies", {})
    if dev_deps:
        sections_found.append("tool.poetry.dev-dependencies")
        for name, version in dev_deps.items():
            v = version if isinstance(version, str) else version.get("version", "")
            if classify_python_specifier(str(v), "poetry") != "pinned":
                unpinned.append(
                    {
                        "name": name,
                        "specifier": str(version),
                        "section": "tool.poetry.dev-dependencies",
                    }
                )

    if unpinned:
        builder.add(
            type_=EVIDENCE_DEPENDENCY_SIGNAL,
            category="dependencies",
            summary=f"Unpinned Python dependencies in {relative}",
            location_file=relative,
            subject=relative,
            raw_observation=f"unpinned:{len(unpinned)}",
            confidence="High",
            metadata={
                "signal": "unpinned_dependency",
                "ecosystem": "Python",
                "count": len(unpinned),
                "examples": unpinned[:10],
                "sections": sections_found,
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_MANIFEST,
                "read_mode": READ_MODE_TEXT,
            },
        )


def _parse_pipfile_deps(
    file_path: Path,
    relative: str,
    builder: EvidenceBuilder,
) -> None:
    """Parse Pipfile for unpinned dependency signals."""

    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        text = read_text(file_path)
        data = tomllib.loads(text)
    except Exception:
        builder.add(
            type_=EVIDENCE_DEPENDENCY_SIGNAL,
            category="dependencies",
            summary=f"Could not parse {relative}",
            location_file=relative,
            subject=relative,
            raw_observation="dependency_manifest_parse_failure",
            confidence="Low",
            metadata={
                "signal": "dependency_manifest_parse_failure",
                "ecosystem": "Python",
                "manifest": "Pipfile",
                "reason": "toml_parse_error",
                "observation_strength": OBSERVATION_STRENGTH_LIMITATION,
                "completeness": COMPLETENESS_PARTIAL,
                "parser": PARSER_MANIFEST,
                "read_mode": READ_MODE_TEXT,
            },
        )
        return

    unpinned: list[dict[str, str]] = []
    for section in ("packages", "dev-packages"):
        deps = data.get(section, {})
        for name, version in deps.items():
            v = version if isinstance(version, str) else version.get("version", "*")
            if classify_python_specifier(str(v), "pipfile") != "pinned":
                unpinned.append({"name": name, "specifier": str(version), "section": section})

    if unpinned:
        builder.add(
            type_=EVIDENCE_DEPENDENCY_SIGNAL,
            category="dependencies",
            summary=f"Unpinned Python dependencies in {relative}",
            location_file=relative,
            subject=relative,
            raw_observation=f"unpinned:{len(unpinned)}",
            confidence="High",
            metadata={
                "signal": "unpinned_dependency",
                "ecosystem": "Python",
                "count": len(unpinned),
                "examples": unpinned[:10],
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_MANIFEST,
                "read_mode": READ_MODE_TEXT,
            },
        )


def _check_poetry_lockfile(root: Path, builder: EvidenceBuilder) -> None:
    """Check Poetry manifest/lockfile consistency at repository level.

    Non-duplicative behavior: Poetry lockfile consistency depends on
    readable pyproject.toml. If parsing fails, _parse_pyproject_deps
    emits dependency_manifest_parse_failure; this function silently
    skips additional lockfile analysis to avoid duplicate limitation evidence.
    """
    pyproject = root / "pyproject.toml"
    poetry_lock = root / "poetry.lock"

    # poetry.lock without pyproject.toml (check BEFORE early return)
    if poetry_lock.exists() and not pyproject.exists():
        builder.add(
            type_=EVIDENCE_DEPENDENCY_SIGNAL,
            category="dependencies",
            summary="Poetry lockfile without pyproject.toml",
            location_file=".",
            subject="Python",
            raw_observation="poetry_lockfile_without_manifest",
            confidence="High",
            metadata={
                "signal": "poetry_lockfile_without_manifest",
                "ecosystem": "Python",
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_FILESYSTEM,
                "read_mode": READ_MODE_SKIPPED,
            },
        )
        return

    if not pyproject.exists():
        return

    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        text = pyproject.read_text(encoding="utf-8")
        data = tomllib.loads(text)
        has_poetry = bool(data.get("tool", {}).get("poetry"))
    except Exception:
        return  # Unparseable — _parse_pyproject_deps already emitted limitation

    if has_poetry and not poetry_lock.exists():
        builder.add(
            type_=EVIDENCE_DEPENDENCY_SIGNAL,
            category="dependencies",
            summary="Poetry manifest without lockfile",
            location_file=".",
            subject="Python",
            raw_observation="poetry_manifest_without_lockfile",
            confidence="High",
            metadata={
                "signal": "poetry_manifest_without_lockfile",
                "ecosystem": "Python",
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_FILESYSTEM,
                "read_mode": READ_MODE_SKIPPED,
            },
        )


def _check_pipfile_lockfile(root: Path, builder: EvidenceBuilder) -> None:
    """Check Pipfile/Pipfile.lock consistency at repository level."""
    pipfile = root / "Pipfile"
    pipfile_lock = root / "Pipfile.lock"

    # Pipfile.lock without Pipfile (check BEFORE early return)
    if pipfile_lock.exists() and not pipfile.exists():
        builder.add(
            type_=EVIDENCE_DEPENDENCY_SIGNAL,
            category="dependencies",
            summary="Pipfile.lock without Pipfile",
            location_file=".",
            subject="Python",
            raw_observation="pipfile_lock_without_manifest",
            confidence="High",
            metadata={
                "signal": "pipfile_lock_without_manifest",
                "ecosystem": "Python",
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_FILESYSTEM,
                "read_mode": READ_MODE_SKIPPED,
            },
        )
        return

    if pipfile.exists() and not pipfile_lock.exists():
        builder.add(
            type_=EVIDENCE_DEPENDENCY_SIGNAL,
            category="dependencies",
            summary="Pipfile without Pipfile.lock",
            location_file=".",
            subject="Python",
            raw_observation="pipfile_without_lockfile",
            confidence="High",
            metadata={
                "signal": "pipfile_without_lockfile",
                "ecosystem": "Python",
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_FILESYSTEM,
                "read_mode": READ_MODE_SKIPPED,
            },
        )


def _check_node_lockfile_conflicts(root: Path, builder: EvidenceBuilder) -> None:
    """Detect when multiple Node.js lockfiles exist for the same ecosystem."""
    NODE_LOCKFILES = [
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "bun.lock",
        "bun.lockb",
    ]
    found = [lf for lf in NODE_LOCKFILES if (root / lf).exists()]
    if len(found) > 1:
        builder.add(
            type_=EVIDENCE_DEPENDENCY_SIGNAL,
            category="dependencies",
            summary=f"Multiple Node.js lockfiles detected: {', '.join(found)}",
            location_file=".",
            subject="Node.js",
            raw_observation=f"lockfile_conflict:{','.join(found)}",
            confidence="High",
            metadata={
                "signal": "lockfile_conflict",
                "ecosystem": "Node.js",
                "lockfiles": found,
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_FILESYSTEM,
                "read_mode": READ_MODE_SKIPPED,
            },
        )
