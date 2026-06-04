from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from pharabius.core.constants import (
    BROAD_EXCEPTION_PER_FILE_THRESHOLD,
    COMPLETENESS_COMPLETE,
    COMPLETENESS_PARTIAL,
    COMPLETENESS_SKIPPED,
    COVERAGE_LOW_THRESHOLD_PCT,
    COVERAGE_PATTERNS,
    DEFAULT_MAX_FILE_SIZE_KB,
    EVIDENCE_BROAD_EXCEPTION,
    EVIDENCE_COVERAGE_GAP,
    EVIDENCE_COVERAGE_METRIC,
    EVIDENCE_COVERAGE_REPORT,
    EVIDENCE_DEBT_MARKER,
    EVIDENCE_DEPENDENCY_SIGNAL,
    EVIDENCE_LARGE_FILE,
    EVIDENCE_LONG_FUNCTION,
    EVIDENCE_SOURCE_FILE_SKIPPED,
    LARGE_FILE_LINE_THRESHOLD,
    LONG_FUNCTION_LINE_THRESHOLD,
    OBSERVATION_STRENGTH_DIRECT,
    OBSERVATION_STRENGTH_HEURISTIC,
    OBSERVATION_STRENGTH_LIMITATION,
    PARSER_BUILTIN_REGEX,
    PARSER_COVERAGE,
    PARSER_FILESYSTEM,
    PARSER_MANIFEST,
    READ_MODE_JSON,
    READ_MODE_SKIPPED,
    READ_MODE_TEXT,
)
from pharabius.core.exclusions import EXCLUDED_DIR_NAMES, is_excluded_path
from pharabius.schemas.evidence import (
    EvidenceBuilder,
    EvidenceItem,
    EvidenceLocation,
    EvidenceStore,
)

_DEBT_MARKER_RE = re.compile(r"\b(todo|fixme|hack|xxx)\b", re.IGNORECASE)

SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".kt",
    ".kts",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".swift",
    ".c",
    ".h",
    ".cpp",
    ".cc",
    ".hpp",
    ".scala",
}


TEXT_EXTENSIONS = SOURCE_EXTENSIONS | {
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".xml",
    ".md",
    ".txt",
    ".ini",
    ".cfg",
    ".env",
}


MANIFEST_FILES = {
    "package.json": "node_manifest",
    "Pipfile": "pipfile_manifest",
    "package-lock.json": "node_lockfile",
    "yarn.lock": "node_lockfile",
    "pnpm-lock.yaml": "node_lockfile",
    "bun.lock": "node_lockfile",
    "bun.lockb": "node_lockfile",
    "pnpm-workspace.yaml": "node_workspace",
    "turbo.json": "node_workspace",
    "nx.json": "node_workspace",
    "lerna.json": "node_workspace",
    "rush.json": "node_workspace",
    "requirements.txt": "python_manifest",
    "pyproject.toml": "python_manifest",
    "poetry.lock": "python_lockfile",
    "uv.lock": "python_lockfile",
    "Pipfile": "python_manifest",
    "Pipfile.lock": "python_lockfile",
    "pom.xml": "java_manifest",
    "build.gradle": "java_manifest",
    "build.gradle.kts": "java_manifest",
    "settings.gradle": "java_workspace",
    "settings.gradle.kts": "java_workspace",
    "go.mod": "go_manifest",
    "go.sum": "go_lockfile",
    "Cargo.toml": "rust_manifest",
    "Cargo.lock": "rust_lockfile",
    "composer.json": "php_manifest",
    "composer.lock": "php_lockfile",
    "Gemfile": "ruby_manifest",
    "Gemfile.lock": "ruby_lockfile",
    "Package.swift": "swift_manifest",
    "packages.lock.json": "dotnet_lockfile",
}


MANIFEST_SUFFIXES: dict[str, str] = {
    ".csproj": "dotnet_manifest",
    ".fsproj": "dotnet_manifest",
    ".vbproj": "dotnet_manifest",
}


CONFIG_FILES = {
    ".env",
    ".env.example",
    ".env.local",
    ".editorconfig",
    ".gitignore",
    ".dockerignore",
    "tsconfig.json",
    "jsconfig.json",
    "eslint.config.js",
    ".eslintrc",
    ".eslintrc.js",
    ".eslintrc.json",
    ".prettierrc",
    ".prettierrc.json",
    "ruff.toml",
    "mypy.ini",
    "pytest.ini",
    "tox.ini",
    "pyproject.toml",
    "setup.cfg",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
}


RISK_KEYWORDS = {
    "auth",
    "authentication",
    "authorization",
    "permission",
    "role",
    "session",
    "token",
    "jwt",
    "oauth",
    "saml",
    "password",
    "secret",
    "credential",
    "payment",
    "billing",
    "invoice",
    "checkout",
    "subscription",
    "order",
    "transaction",
    "refund",
    "settlement",
    "pii",
    "personal",
    "customer",
    "patient",
    "financial",
    "audit",
    "retention",
    "encryption",
    "consent",
    "gdpr",
    "hipaa",
    "pci",
    "deploy",
    "release",
    "migration",
    "rollback",
    "incident",
    "alert",
    "monitoring",
    "logging",
    "tracing",
}


IMPORT_PATTERNS = [
    re.compile(r"^\s*import\s+([\w.]+)", re.MULTILINE),
    re.compile(r"^\s*from\s+([\w.]+)\s+import\s+", re.MULTILINE),
    re.compile(r"^\s*import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
    re.compile(r"^\s*const\s+.*?=\s+require\(['\"]([^'\"]+)['\"]\)", re.MULTILINE),
]

# Rust-specific patterns (handled separately for grouped expansion)
_RUST_SIMPLE_USE = re.compile(r"^\s*use\s+([\w:]+)\s*;", re.MULTILINE)
_RUST_GROUPED_USE = re.compile(r"^\s*use\s+([\w:]+)::\{([^}]+)\}\s*;", re.MULTILINE)
_RUST_LINE_COMMENT = re.compile(r"^\s*//")


from pharabius.core.io_helpers import read_json, read_text
from pharabius.core.path_utils import (
    normalize_repo_path,
    path_matches_exact_or_suffix,
    relative_repo_path,
)


# Keep _relative as thin wrapper for backward compatibility with call sites
def _relative(path: Path, root: Path) -> str:
    return relative_repo_path(path, root)


def _is_excluded(
    path: Path,
    root: Path,
    extra_exclude_paths: set[str] | None = None,
) -> bool:
    if is_excluded_path(path, root):
        return True
    if extra_exclude_paths:
        try:
            relative = path.relative_to(root)
        except ValueError:
            return True
        parts_str = "/" + relative.as_posix()
        for exc in extra_exclude_paths:
            exc_norm = exc.strip("/")
            if not exc_norm:
                continue
            # Match as path segment: exact or followed by /
            if parts_str == "/" + exc_norm:
                return True
            if parts_str.startswith("/" + exc_norm + "/"):
                return True
            # Also match if a path component equals the exclusion
            for segment in relative.parts:
                if segment == exc_norm:
                    return True
    return False


def _iter_files(
    root: Path,
    extra_exclude_paths: set[str] | None = None,
) -> list[Path]:
    files: list[Path] = []

    for path in root.rglob("*"):
        if path.is_dir():
            continue

        if _is_excluded(path, root, extra_exclude_paths=extra_exclude_paths):
            continue

        files.append(path)

    return sorted(files)


def _read_text(path: Path, max_chars: int = 100_000) -> str:
    return read_text(path, max_chars=max_chars)


def _read_json(path: Path) -> dict[str, Any]:
    return read_json(path)


def _is_test_path(path: Path, root: Path) -> bool:
    parts = {part.lower() for part in path.relative_to(root).parts}
    name = path.name.lower()

    is_in_test_dir = bool(
        parts
        & {
            "test",
            "tests",
            "__tests__",
            "spec",
            "specs",
            "e2e",
            "integration-tests",
            "unit-tests",
        }
    )

    is_test_file = any(
        name.endswith(suffix)
        for suffix in (
            ".test.py",
            ".test.ts",
            ".test.tsx",
            ".test.js",
            ".test.jsx",
            ".spec.ts",
            ".spec.tsx",
            ".spec.js",
            ".spec.jsx",
        )
    ) or name.endswith("_test.go")

    return is_in_test_dir or is_test_file


def _is_documentation_file(path: Path, root: Path) -> bool:
    parts = path.relative_to(root).parts
    name = path.name.lower()

    if name.startswith("readme"):
        return True

    if name in {"changelog.md", "contributing.md", "architecture.md", "adr.md"}:
        return True

    return bool(parts and parts[0].lower() in {"docs", "documentation", "adr", "adrs"})


def _is_deployment_file(path: Path, root: Path) -> bool:
    relative = _relative(path, root)
    name = path.name.lower()

    if name in {
        "dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
        "procfile",
        "fly.toml",
        "render.yaml",
        "app.yaml",
    }:
        return True

    if relative.startswith(".github/workflows/"):
        return True

    if relative.startswith(".gitlab-ci"):
        return True

    return name in {"jenkinsfile", "bitbucket-pipelines.yml", "azure-pipelines.yml"}


def _is_infrastructure_file(path: Path, root: Path) -> bool:
    relative = _relative(path, root)
    name = path.name.lower()

    if path.suffix == ".tf":
        return True

    if "k8s" in relative.lower() or "kubernetes" in relative.lower():
        return path.suffix in {".yaml", ".yml", ".json"}

    if "helm" in relative.lower():
        return path.suffix in {".yaml", ".yml", ".tpl"}

    return name in {"serverless.yml", "serverless.yaml", "pulumi.yaml", "pulumi.yml"}


def _risk_keywords_for_path(path: Path, root: Path) -> list[str]:
    relative = _relative(path, root).lower()
    normalized = relative.replace("\\", "/").replace("-", "_").replace(".", "_")

    return sorted(keyword for keyword in RISK_KEYWORDS if keyword in normalized)


_CI_PATH_PREFIXES: frozenset[str] = frozenset(
    {
        ".github/workflows/",
        ".gitlab/",
    }
)

_CI_PATH_EXACT: frozenset[str] = frozenset(
    {
        ".gitlab-ci.yml",
        "jenkinsfile",
        "azure-pipelines.yml",
        "bitbucket-pipelines.yml",
    }
)

# Keywords suppressed in CI/deployment files to avoid false risk signals.
# 'checkout' matches actions/checkout in GitHub Actions (not a payment signal there).
# Operational terms (deploy, release, monitoring, etc.) are infrastructure signals,
# not security risks by themselves.
_CI_SUPPRESSED_KEYWORDS: frozenset[str] = frozenset(
    {
        "checkout",
        "deploy",
        "release",
        "migration",
        "rollback",
        "incident",
        "alert",
        "monitoring",
        "logging",
        "tracing",
    }
)


def _is_ci_or_deployment_path(path: Path, root: Path) -> bool:
    """Return True if the file is a CI/deployment workflow file."""
    try:
        relative = _relative(path, root)
    except ValueError:
        relative = str(path).lower()
    lower = relative.lower()
    forward = lower.replace("\\", "/")

    if forward in _CI_PATH_EXACT:
        return True
    return any(forward.startswith(prefix) for prefix in _CI_PATH_PREFIXES)


def _risk_keywords_for_text(text: str) -> list[str]:
    lowered = text.lower()

    return sorted(keyword for keyword in RISK_KEYWORDS if keyword in lowered)


def _extract_rust_imports(text: str) -> list[str]:
    """Extract Rust use imports with grouped expansion and comment filtering.

    Handles:
    - Simple: use crate::foo::bar;
    - Grouped: use crate::{foo, bar::baz}; -> crate::foo, crate::bar::baz
    - Skips line comments: // use crate::fake;
    - Never emits bare crate/super/self from grouped imports.
    """
    imports: set[str] = set()

    # Filter out line-commented lines
    clean_lines: list[str] = []
    for line in text.splitlines():
        if not _RUST_LINE_COMMENT.match(line):
            clean_lines.append(line)
    clean_text = "\n".join(clean_lines)

    # Extract grouped imports first (they also match simple pattern)
    grouped_prefixes: set[str] = set()
    for match in _RUST_GROUPED_USE.finditer(clean_text):
        prefix = match.group(1)  # e.g. crate, super, crate::module
        items_str = match.group(2)  # e.g. foo, bar::baz
        grouped_prefixes.add(prefix)
        for item in items_str.split(","):
            item = item.strip()
            if item:
                full = f"{prefix}::{item}"
                imports.add(full)

    # Extract simple imports, skip those already handled as grouped
    for match in _RUST_SIMPLE_USE.finditer(clean_text):
        imported = match.group(1)
        # Skip if this was the prefix of a grouped import
        if imported in grouped_prefixes:
            continue
        imports.add(imported)

    return sorted(imports)


def _extract_imports(path: Path) -> list[str]:
    if path.suffix not in SOURCE_EXTENSIONS:
        return []

    text = _read_text(path)
    if not text:
        return []

    # Rust uses separate extraction with grouped import expansion
    if path.suffix == ".rs":
        return _extract_rust_imports(text)

    imports: set[str] = set()

    for pattern in IMPORT_PATTERNS:
        for match in pattern.finditer(text):
            imported = match.group(1).strip()
            if imported:
                imports.add(imported)

    return sorted(imports)


def _package_json_scripts(path: Path) -> dict[str, str]:
    if path.name != "package.json":
        return {}

    package_json = _read_json(path)
    scripts = package_json.get("scripts")

    if not isinstance(scripts, dict):
        return {}

    result: dict[str, str] = {}

    for name, command in scripts.items():
        if isinstance(name, str) and isinstance(command, str):
            result[name] = command

    return result


def _git_value(root: Path, command: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *command],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return ""

    if result.returncode != 0:
        return ""

    return result.stdout.strip()


def _debt_markers_in_text(text: str) -> dict[str, int]:
    """Count debt-marker occurrences (TODO/FIXME/HACK/XXX) in source text.

    Returns {"todo": 5, "fixme": 3, ...} — occurrence counts, not just presence.
    """
    counts: dict[str, int] = {}
    for match in _DEBT_MARKER_RE.finditer(text):
        marker = match.group(1).lower()
        counts[marker] = counts.get(marker, 0) + 1
    return counts


def _detect_long_python_functions(
    text: str,
    relative: str,
    builder: EvidenceBuilder,
) -> None:
    """Detect Python functions exceeding LONG_FUNCTION_LINE_THRESHOLD.

    Uses indentation-based span counting. Only applies to .py files.
    Observation strength is heuristic — not AST-grade certainty.
    End detection prefers next nonblank line at same or lesser indent
    for better accuracy than simple next-function-start.
    """
    lines = text.split("\n")
    func_starts: list[tuple[int, int, str]] = []  # (line_index, indent, name)

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(stripped)
        if stripped.startswith(("def ", "async def ")):
            # Extract function name
            def_line = stripped.split("(")[0]
            name = def_line.replace("def ", "").replace("async ", "").strip()
            func_starts.append((i, indent, name))

    for start_idx, (start_line, base_indent, func_name) in enumerate(func_starts):
        # Find end: next nonblank line at same or lesser indent, or next function start
        end_line = len(lines) - 1
        # First try: next nonblank line at <= base_indent
        found_end = False
        for j in range(start_line + 1, len(lines)):
            stripped = lines[j].lstrip()
            if not stripped or stripped.startswith("#"):
                continue
            current_indent = len(lines[j]) - len(stripped)
            if current_indent <= base_indent:
                end_line = j - 1
                found_end = True
                break
        if not found_end:
            end_line = len(lines) - 1

        func_lines = end_line - start_line + 1
        if func_lines >= LONG_FUNCTION_LINE_THRESHOLD:
            builder.add(
                type_=EVIDENCE_LONG_FUNCTION,
                category="code_structure",
                summary=(f"Long function {func_name} spans {func_lines} lines in {relative}"),
                location_file=relative,
                subject=func_name,
                raw_observation=f"{func_name}:{func_lines}lines",
                confidence="Medium",
                metadata={
                    "function_name": func_name,
                    "line_start": start_line + 1,
                    "line_end": end_line + 1,
                    "line_count": func_lines,
                    "threshold": LONG_FUNCTION_LINE_THRESHOLD,
                    "language": "python",
                    "observation_strength": OBSERVATION_STRENGTH_HEURISTIC,
                    "completeness": COMPLETENESS_PARTIAL,
                    "parser": PARSER_BUILTIN_REGEX,
                    "read_mode": READ_MODE_TEXT,
                },
            )


def _detect_broad_exceptions(
    text: str,
    relative: str,
    builder: EvidenceBuilder,
) -> None:
    """Detect bare except / catch-all patterns in source code.

    Supports Python, JavaScript/TypeScript, and Java patterns.
    """
    BROAD_PATTERNS: list[tuple[str, str]] = [
        (r"^\s*except\s*:", "python_bare_except"),
        (r"^\s*except\s+Exception\s*[:\[]", "python_exception_catch"),
        (r"^\s*except\s+BaseException\s*:", "python_base_exception"),
        (r"catch\s*\(\s*\w*\s*\)\s*\{", "js_catch_all"),
        (r"catch\s*\(\s*Exception\s+\w+\s*\)", "java_exception_catch"),
        (r"catch\s*\(\s*Throwable\s+\w+\s*\)", "java_throwable_catch"),
    ]
    lines = text.split("\n")
    for i, line in enumerate(lines):
        for pattern, label in BROAD_PATTERNS:
            if re.search(pattern, line):
                builder.add(
                    type_=EVIDENCE_BROAD_EXCEPTION,
                    category="code_structure",
                    summary=(f"Broad exception handler ({label}) in {relative} line {i + 1}"),
                    location_file=relative,
                    subject=relative,
                    raw_observation=f"{label}:line{i + 1}",
                    confidence="Medium",
                    metadata={
                        "pattern": label,
                        "line_number": i + 1,
                        "observation_strength": OBSERVATION_STRENGTH_HEURISTIC,
                        "completeness": COMPLETENESS_PARTIAL,
                        "parser": PARSER_BUILTIN_REGEX,
                        "read_mode": READ_MODE_TEXT,
                    },
                )
                break  # one detection per line


from pharabius.core.coverage_parsers import scan_coverage_artifact
from pharabius.core.dependency_parsers import (
    scan_dependency_manifest,
    scan_repository_dependency_consistency,
)
from pharabius.core.runtime_parsers import detect_runtime_version_pins


def scan_repository(
    repository_root: Path,
    *,
    extra_exclude_paths: set[str] | None = None,
    max_file_size_kb: int | None = None,
) -> EvidenceStore:
    root = repository_root.resolve()
    files = _iter_files(root, extra_exclude_paths=extra_exclude_paths)

    builder = EvidenceBuilder()

    builder.add(
        type_="repository_summary",
        category="repository",
        summary=f"Repository scan discovered {len(files)} files after exclusions.",
        subject=root.name,
        raw_observation=str(root),
        confidence="High",
        metadata={
            "excluded_directories": sorted(EXCLUDED_DIR_NAMES),
            "file_count": len(files),
        },
    )

    branch = _git_value(root, ["rev-parse", "--abbrev-ref", "HEAD"])
    commit = _git_value(root, ["rev-parse", "HEAD"])

    if branch:
        builder.add(
            type_="git_branch",
            category="repository_metadata",
            summary=f"Current git branch is {branch}.",
            subject="git_branch",
            object_=branch,
            raw_observation=branch,
            confidence="High",
        )

    if commit:
        builder.add(
            type_="git_commit",
            category="repository_metadata",
            summary=f"Current git commit is {commit}.",
            subject="git_commit",
            object_=commit,
            raw_observation=commit,
            confidence="High",
        )

    # Repository-level dependency signals
    scan_repository_dependency_consistency(root, builder)

    # Runtime version pinning (v3.3.0)
    detect_runtime_version_pins(root, builder)

    # Repository-level coverage artifact scanning (v3.2.0)
    # Coverage dirs are normally excluded, so we scan them separately
    for pattern, format_type in COVERAGE_PATTERNS.items():
        parts = pattern.split("/")
        candidate = root / Path(*parts)
        if candidate.exists() and candidate.is_file():
            rel = _relative(candidate, root)
            scan_coverage_artifact(candidate, rel, format_type, builder)

    for file_path in files:
        relative = _relative(file_path, root)

        builder.add(
            type_="file_detected",
            category="file_tree",
            summary=f"File detected: {relative}",
            location_file=relative,
            subject=relative,
            raw_observation=relative,
            confidence="High",
            metadata={
                "suffix": file_path.suffix,
                "size_bytes": file_path.stat().st_size,
            },
        )

        # Size-based skip for source files (v3.2.0)
        if max_file_size_kb is not None and file_path.suffix in SOURCE_EXTENSIONS:
            try:
                size_kb = file_path.stat().st_size / 1024
            except OSError:
                size_kb = 0
            if size_kb > max_file_size_kb:
                builder.add(
                    type_=EVIDENCE_SOURCE_FILE_SKIPPED,
                    category="scanner_limit",
                    summary=(
                        f"Source file skipped: {relative} "
                        f"({size_kb:.0f} KB exceeds {max_file_size_kb} KB limit)"
                    ),
                    location_file=relative,
                    subject=relative,
                    raw_observation=f"skipped:{size_kb:.0f}kb>max:{max_file_size_kb}kb",
                    confidence="High",
                    metadata={
                        "size_kb": round(size_kb, 1),
                        "max_file_size_kb": max_file_size_kb,
                        "reason": "file_size_limit",
                        "observation_strength": OBSERVATION_STRENGTH_LIMITATION,
                        "completeness": COMPLETENESS_SKIPPED,
                        "parser": PARSER_FILESYSTEM,
                        "read_mode": READ_MODE_SKIPPED,
                    },
                )
                continue  # Skip all content scanning for this file

        if file_path.name in MANIFEST_FILES:
            builder.add(
                type_="manifest_detected",
                category="dependencies",
                summary=f"Dependency or package manifest detected: {relative}",
                location_file=relative,
                subject=relative,
                object_=MANIFEST_FILES[file_path.name],
                raw_observation=file_path.name,
                confidence="High",
                metadata={"manifest_type": MANIFEST_FILES[file_path.name]},
            )

            # Dependency signal: unpinned deps
            scan_dependency_manifest(file_path, relative, builder)

        # Suffix-based manifest detection (.NET project files)
        if file_path.suffix in MANIFEST_SUFFIXES:
            builder.add(
                type_="manifest_detected",
                category="dependencies",
                summary=f"Dependency or package manifest detected: {relative}",
                location_file=relative,
                subject=relative,
                object_=MANIFEST_SUFFIXES[file_path.suffix],
                raw_observation=file_path.name,
                confidence="High",
                metadata={"manifest_type": MANIFEST_SUFFIXES[file_path.suffix]},
            )

        # .NET solution file: distinct evidence type, not a dependency manifest
        if file_path.suffix == ".sln":
            builder.add(
                type_="solution_file_detected",
                category="structure",
                summary=f".NET solution file detected: {relative}",
                location_file=relative,
                subject=relative,
                object_="dotnet_solution",
                raw_observation=file_path.name,
                confidence="High",
            )

        # Terraform lockfile: reproducibility evidence, not a package manifest
        if file_path.name == ".terraform.lock.hcl":
            builder.add(
                type_="lockfile_detected",
                category="dependencies",
                summary=f"Terraform provider lockfile detected: {relative}",
                location_file=relative,
                subject=relative,
                object_="terraform_lockfile",
                raw_observation=".terraform.lock.hcl",
                confidence="High",
            )

        # Root package.json workspaces: only at repository root
        if file_path.name == "package.json" and relative == "package.json":
            pkg_data = _read_json(file_path)
            workspaces = pkg_data.get("workspaces")
            if workspaces and isinstance(workspaces, (list, dict)):
                builder.add(
                    type_="manifest_detected",
                    category="dependencies",
                    summary=f"Node.js workspace manifest detected: {relative}",
                    location_file=relative,
                    subject=relative,
                    object_="node_workspace",
                    raw_observation="package.json workspaces",
                    confidence="High",
                    metadata={"workspace_type": "package.json"},
                )

        if file_path.name in CONFIG_FILES or file_path.suffix in {".env"}:
            builder.add(
                type_="configuration_file_detected",
                category="configuration",
                summary=f"Configuration file detected: {relative}",
                location_file=relative,
                subject=relative,
                raw_observation=relative,
                confidence="High",
            )

        # Coverage report detection (v3.2.0) — handles files NOT in excluded dirs
        for pattern, format_type in COVERAGE_PATTERNS.items():
            if path_matches_exact_or_suffix(relative, pattern):
                scan_coverage_artifact(file_path, relative, format_type, builder)
                break
                break
                break

        if _is_test_path(file_path, root):
            builder.add(
                type_="test_file_detected",
                category="test",
                summary=f"Test-related file detected: {relative}",
                location_file=relative,
                subject=relative,
                raw_observation=relative,
                confidence="High",
            )

        if _is_documentation_file(file_path, root):
            builder.add(
                type_="documentation_file_detected",
                category="documentation",
                summary=f"Documentation file detected: {relative}",
                location_file=relative,
                subject=relative,
                raw_observation=relative,
                confidence="High",
            )

        if _is_deployment_file(file_path, root):
            builder.add(
                type_="deployment_file_detected",
                category="operations",
                summary=f"Deployment or CI/CD file detected: {relative}",
                location_file=relative,
                subject=relative,
                raw_observation=relative,
                confidence="High",
            )

        if _is_infrastructure_file(file_path, root):
            builder.add(
                type_="infrastructure_file_detected",
                category="operations",
                summary=f"Infrastructure-as-code file detected: {relative}",
                location_file=relative,
                subject=relative,
                raw_observation=relative,
                confidence="High",
            )

        path_keywords = _risk_keywords_for_path(file_path, root)
        if path_keywords:
            builder.add(
                type_="risk_sensitive_path_detected",
                category="risk_signal",
                summary=f"Risk-sensitive path detected: {relative}",
                location_file=relative,
                subject=relative,
                raw_observation=relative,
                confidence="Medium",
                metadata={"keywords": path_keywords},
            )

        if file_path.suffix in TEXT_EXTENSIONS or file_path.name in MANIFEST_FILES:
            text = _read_text(file_path)
            text_keywords = _risk_keywords_for_text(text)

            # Suppress operational/CI keywords in CI/deployment files
            if text_keywords and _is_ci_or_deployment_path(file_path, root):
                text_keywords = [k for k in text_keywords if k not in _CI_SUPPRESSED_KEYWORDS]

            if text_keywords:
                builder.add(
                    type_="risk_sensitive_keyword_detected",
                    category="risk_signal",
                    summary=f"Risk-sensitive keyword detected in {relative}",
                    location_file=relative,
                    subject=relative,
                    raw_observation=", ".join(text_keywords),
                    confidence="Medium",
                    metadata={"keywords": text_keywords[:50]},
                )

            # Debt marker detection (occurrence-counting, not just unique names)
            if file_path.suffix in SOURCE_EXTENSIONS:
                marker_counts = _debt_markers_in_text(text)
                total_marker_count = sum(marker_counts.values())
                if total_marker_count:
                    builder.add(
                        type_=EVIDENCE_DEBT_MARKER,
                        category="code_quality",
                        summary=f"Debt markers detected in {relative}",
                        location_file=relative,
                        subject=relative,
                        raw_observation=", ".join(
                            f"{marker}:{count}" for marker, count in sorted(marker_counts.items())
                        ),
                        confidence="High",
                        metadata={
                            "marker_counts": marker_counts,
                            "total_count": total_marker_count,
                        },
                    )

            # Large file detection for source files
            if file_path.suffix in SOURCE_EXTENSIONS:
                line_count = text.count("\n") + 1
                if line_count >= LARGE_FILE_LINE_THRESHOLD:
                    builder.add(
                        type_=EVIDENCE_LARGE_FILE,
                        category="code_structure",
                        summary=f"Large source file: {relative} ({line_count} lines)",
                        location_file=relative,
                        subject=relative,
                        raw_observation=f"{line_count} lines",
                        confidence="High",
                        metadata={"line_count": line_count},
                    )

            # Long function detection (Python only for v3.2.0)
            if file_path.suffix == ".py":
                _detect_long_python_functions(text, relative, builder)

            # Broad exception detection
            _detect_broad_exceptions(text, relative, builder)

        imports = _extract_imports(file_path)
        if imports:
            builder.add(
                type_="imports_detected",
                category="code_structure",
                summary=f"Import statements detected in {relative}",
                location_file=relative,
                subject=relative,
                raw_observation=", ".join(imports),
                confidence="Medium",
                metadata={"imports": imports[:200]},
            )

        scripts = _package_json_scripts(file_path)
        if scripts:
            for script_name, command in scripts.items():
                script_category = "build"
                if "test" in script_name.lower():
                    script_category = "test"
                elif script_name.lower() in {"start", "dev", "serve"}:
                    script_category = "runtime"

                builder.add(
                    type_="package_script_detected",
                    category=script_category,
                    summary=f"Package script detected: {script_name}",
                    location_file=relative,
                    subject=script_name,
                    object_=command,
                    raw_observation=command,
                    confidence="High",
                    metadata={"script_name": script_name, "command": command},
                )

    return EvidenceStore(repository=str(root), evidence=builder.items)


def write_evidence_store(
    repository_root: Path,
    *,
    extra_exclude_paths: set[str] | None = None,
    max_file_size_kb: int | None = None,
) -> EvidenceStore:
    store = scan_repository(
        repository_root,
        extra_exclude_paths=extra_exclude_paths,
        max_file_size_kb=max_file_size_kb,
    )
    output_path = repository_root.resolve() / ".ai-debt" / "evidence.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(store.model_dump_json(indent=2) + "\n", encoding="utf-8")

    return store
