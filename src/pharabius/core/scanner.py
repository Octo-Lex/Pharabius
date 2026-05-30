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
from pharabius.schemas.evidence import EvidenceItem, EvidenceLocation, EvidenceStore

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
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except Exception:
        return ""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    if isinstance(value, dict):
        return value

    return {}


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


class EvidenceBuilder:
    def __init__(self) -> None:
        self._counter = 0
        self.items: list[EvidenceItem] = []

    def add(
        self,
        *,
        type_: str,
        category: str,
        summary: str,
        location_file: str = "",
        line_start: int | None = None,
        line_end: int | None = None,
        subject: str = "",
        object_: str = "",
        raw_observation: str = "",
        confidence: str = "Medium",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._counter += 1

        item = EvidenceItem(
            evidence_id=f"EVD-{self._counter:06d}",
            type=type_,
            category=category,
            location=EvidenceLocation(
                file=location_file,
                line_start=line_start,
                line_end=line_end,
            ),
            subject=subject,
            object=object_,
            summary=summary,
            raw_observation=raw_observation,
            confidence=confidence,
            metadata=metadata or {},
        )

        self.items.append(item)


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
    text: str, relative: str, builder: EvidenceBuilder,
) -> None:
    """Detect Python functions exceeding LONG_FUNCTION_LINE_THRESHOLD.

    Uses indentation-based span counting. Only applies to .py files.
    Observation strength is heuristic — not AST-grade certainty.
    End detection prefers next nonblank line at same or lesser indent
    for better accuracy than simple next-function-start.
    """
    lines = text.split('\n')
    func_starts: list[tuple[int, int, str]] = []  # (line_index, indent, name)

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped or stripped.startswith('#'):
            continue
        indent = len(line) - len(stripped)
        if stripped.startswith(('def ', 'async def ')):
            # Extract function name
            def_line = stripped.split('(')[0]
            name = def_line.replace('def ', '').replace('async ', '').strip()
            func_starts.append((i, indent, name))

    for start_idx, (start_line, base_indent, func_name) in enumerate(func_starts):
        # Find end: next nonblank line at same or lesser indent, or next function start
        end_line = len(lines) - 1
        # First try: next nonblank line at <= base_indent
        found_end = False
        for j in range(start_line + 1, len(lines)):
            stripped = lines[j].lstrip()
            if not stripped or stripped.startswith('#'):
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
                summary=(
                    f"Long function {func_name} spans {func_lines} lines in {relative}"
                ),
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


def _parse_dep_name(dep_str: str) -> str:
    """Extract package name from a PEP 508 dependency string."""
    name = dep_str
    for ch in (">", "<", "~", "=", "!", " ", "\t", ";", "[", "("):
        name = name.split(ch)[0]
    return name.strip()


def _detect_broad_exceptions(
    text: str, relative: str, builder: EvidenceBuilder,
) -> None:
    """Detect bare except / catch-all patterns in source code.

    Supports Python, JavaScript/TypeScript, and Java patterns.
    """
    BROAD_PATTERNS: list[tuple[str, str]] = [
        (r'^\s*except\s*:', 'python_bare_except'),
        (r'^\s*except\s+Exception\s*[:\[]', 'python_exception_catch'),
        (r'^\s*except\s+BaseException\s*:', 'python_base_exception'),
        (r'catch\s*\(\s*\w*\s*\)\s*\{', 'js_catch_all'),
        (r'catch\s*\(\s*Exception\s+\w+\s*\)', 'java_exception_catch'),
        (r'catch\s*\(\s*Throwable\s+\w+\s*\)', 'java_throwable_catch'),
    ]
    lines = text.split('\n')
    for i, line in enumerate(lines):
        for pattern, label in BROAD_PATTERNS:
            if re.search(pattern, line):
                builder.add(
                    type_=EVIDENCE_BROAD_EXCEPTION,
                    category="code_structure",
                    summary=(
                        f"Broad exception handler ({label}) "
                        f"in {relative} line {i + 1}"
                    ),
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


def _check_node_unpinned_deps(
    file_path: Path, relative: str, builder: EvidenceBuilder,
) -> None:
    """Check package.json for unpinned or broad version ranges."""
    data = _read_json(file_path)
    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
    unpinned: list[dict[str, str]] = []
    for name, version in deps.items():
        if not isinstance(version, str):
            continue
        if version in ("*", "latest", ""):
            unpinned.append({"name": name, "specifier": version})
        elif version.startswith(">") or version.startswith("<") or version.startswith("~"):
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
    file_path: Path, relative: str, builder: EvidenceBuilder,
) -> None:
    """Check requirements.txt for unpinned version specifiers.

    Pinned: package==1.2.3, package===1.2.3, package @ file://...
    Unpinned/broad: package, package>=1.0, package~=1.2, package<3
    """
    text = _read_text(file_path)
    if not text:
        return
    unpinned: list[dict[str, str]] = []
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('-'):
            continue
        # Remove environment markers
        if ';' in line:
            line = line.split(';')[0].strip()
        # Remove extras
        if '[' in line and ']' in line:
            base = line.split('[')[0]
            rest = line.split(']', 1)[1]
            line = base + rest
        # Check pinning
        if '==' in line or '===' in line or ' @ ' in line:
            continue  # Pinned
        # Anything else with a name is unpinned
        name = line
        for ch in ('>', '<', '~', '=', '!', ' ', '\t'):
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
    file_path: Path, relative: str, builder: EvidenceBuilder,
) -> None:
    """Parse pyproject.toml for dependency signals."""
    from pharabius.core.dependency_utils import classify_python_specifier

    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        text = _read_text(file_path)
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
                unpinned.append({"name": name, "specifier": dep_str, "section": "project.dependencies"})

    # PEP 621 [project].optional-dependencies
    opt_deps = data.get("project", {}).get("optional-dependencies", {})
    if opt_deps:
        sections_found.append("project.optional-dependencies")
        for group, deps in opt_deps.items():
            for dep_str in deps:
                name = _parse_dep_name(dep_str)
                if classify_python_specifier(dep_str, "pep508") != "pinned":
                    unpinned.append({"name": name, "specifier": dep_str, "section": f"project.optional-dependencies.{group}"})

    # Poetry [tool.poetry.dependencies]
    poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    if poetry_deps:
        sections_found.append("tool.poetry.dependencies")
        for name, version in poetry_deps.items():
            if name.lower() == "python":
                continue
            v = version if isinstance(version, str) else version.get("version", "")
            if classify_python_specifier(str(v), "poetry") != "pinned":
                unpinned.append({"name": name, "specifier": str(version), "section": "tool.poetry.dependencies"})

    # Poetry [tool.poetry.group.*.dependencies]
    poetry_groups = data.get("tool", {}).get("poetry", {}).get("group", {})
    for group_name, group_data in poetry_groups.items():
        group_deps = group_data.get("dependencies", {})
        if group_deps:
            sections_found.append(f"tool.poetry.group.{group_name}.dependencies")
            for name, version in group_deps.items():
                v = version if isinstance(version, str) else version.get("version", "")
                if classify_python_specifier(str(v), "poetry") != "pinned":
                    unpinned.append({"name": name, "specifier": str(version), "section": f"tool.poetry.group.{group_name}.dependencies"})

    # Poetry [tool.poetry.dev-dependencies] (legacy)
    dev_deps = data.get("tool", {}).get("poetry", {}).get("dev-dependencies", {})
    if dev_deps:
        sections_found.append("tool.poetry.dev-dependencies")
        for name, version in dev_deps.items():
            v = version if isinstance(version, str) else version.get("version", "")
            if classify_python_specifier(str(v), "poetry") != "pinned":
                unpinned.append({"name": name, "specifier": str(version), "section": "tool.poetry.dev-dependencies"})

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
    file_path: Path, relative: str, builder: EvidenceBuilder,
) -> None:
    """Parse Pipfile for unpinned dependency signals."""
    from pharabius.core.dependency_utils import classify_python_specifier

    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        text = _read_text(file_path)
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


def _detect_runtime_version_pins(root: Path, builder: EvidenceBuilder) -> None:
    """Detect runtime version pinning at repository level.

    v3.3.0: Python + Node.js only. Ruby/Java deferred.
    """
    from pharabius.core.constants import EVIDENCE_RUNTIME_VERSION_SIGNAL

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
        text = _read_text(fpath)
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
        data = _read_json(pkg_json)
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


def _check_node_lockfile_conflicts(root: Path, builder: EvidenceBuilder) -> None:
    """Detect when multiple Node.js lockfiles exist for the same ecosystem."""
    NODE_LOCKFILES = [
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lock", "bun.lockb",
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


_COVERAGE_PATTERNS = COVERAGE_PATTERNS  # Re-export from constants for backward compat


def _parse_istanbul_coverage(
    file_path: Path, relative: str, builder: EvidenceBuilder,
) -> None:
    data = _read_json(file_path)
    total = data.get("total", {})
    if not total:
        return
    for metric_name in ("lines", "statements", "functions", "branches"):
        metric_data = total.get(metric_name, {})
        pct = metric_data.get("pct", 0)
        if isinstance(pct, (int, float)):
            builder.add(
                type_=EVIDENCE_COVERAGE_METRIC,
                category="test_health",
                summary=f"{metric_name} coverage: {pct}%",
                location_file=relative,
                subject=metric_name,
                raw_observation=f"{metric_name}:{pct}%",
                confidence="High",
                metadata={
                    "metric": metric_name,
                    "percent": float(pct),
                    "format": "istanbul_json",
                    "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                    "completeness": COMPLETENESS_COMPLETE,
                    "parser": PARSER_COVERAGE,
                    "read_mode": READ_MODE_JSON,
                },
            )


def _parse_python_coverage(
    file_path: Path, relative: str, builder: EvidenceBuilder,
) -> None:
    data = _read_json(file_path)
    totals = data.get("totals", {})
    if not totals:
        return
    # coverage.py v5+ provides percent_covered directly
    pct = totals.get("percent_covered")
    if pct is not None:
        builder.add(
            type_=EVIDENCE_COVERAGE_METRIC,
            category="test_health",
            summary=f"line coverage: {float(pct):.1f}%",
            location_file=relative,
            subject="lines",
            raw_observation=f"lines:{float(pct):.1f}%",
            confidence="High",
            metadata={
                "metric": "lines",
                "percent": float(pct),
                "format": "python_coverage_json",
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_COVERAGE,
                "read_mode": READ_MODE_JSON,
            },
        )
    else:
        # Fallback: compute from covered_lines / num_statements
        covered = totals.get("covered_lines", 0)
        total_statements = totals.get("num_statements", 0)
        if total_statements > 0:
            pct = round(covered / total_statements * 100, 1)
            builder.add(
                type_=EVIDENCE_COVERAGE_METRIC,
                category="test_health",
                summary=f"line coverage: {pct}% (derived)",
                location_file=relative,
                subject="lines",
                raw_observation=f"lines:{pct}%",
                confidence="High",
                metadata={
                    "metric": "lines",
                    "percent": float(pct),
                    "format": "python_coverage_json",
                    "derived": True,
                    "observation_strength": OBSERVATION_STRENGTH_DERIVED,
                    "completeness": COMPLETENESS_COMPLETE,
                    "parser": PARSER_COVERAGE,
                    "read_mode": READ_MODE_JSON,
                },
            )


def _parse_lcov_coverage(
    file_path: Path, relative: str, builder: EvidenceBuilder,
) -> None:
    text = _read_text(file_path)
    if not text:
        return
    lf = 0  # line count found
    lh = 0  # line count hit
    fnf = 0  # function count found
    fnh = 0  # function count hit
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith('LF:'):
            try:
                lf += int(line[3:])
            except ValueError:
                pass
        elif line.startswith('LH:'):
            try:
                lh += int(line[3:])
            except ValueError:
                pass
        elif line.startswith('FNF:'):
            try:
                fnf += int(line[4:])
            except ValueError:
                pass
        elif line.startswith('FNH:'):
            try:
                fnh += int(line[4:])
            except ValueError:
                pass
    # Line coverage
    if lf > 0:
        line_pct = round(lh / lf * 100, 1)
        builder.add(
            type_=EVIDENCE_COVERAGE_METRIC,
            category="test_health",
            summary=f"line coverage: {line_pct}% (LCOV)",
            location_file=relative,
            subject="lines",
            raw_observation=f"lines:{line_pct}%:LH={lh}/LF={lf}",
            confidence="High",
            metadata={
                "metric": "lines",
                "percent": float(line_pct),
                "format": "lcov",
                "lf": lf,
                "lh": lh,
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_COVERAGE,
                "read_mode": READ_MODE_TEXT,
            },
        )
    # Function coverage (when present)
    if fnf > 0:
        func_pct = round(fnh / fnf * 100, 1)
        builder.add(
            type_=EVIDENCE_COVERAGE_METRIC,
            category="test_health",
            summary=f"function coverage: {func_pct}% (LCOV)",
            location_file=relative,
            subject="functions",
            raw_observation=f"functions:{func_pct}%:FNH={fnh}/FNF={fnf}",
            confidence="High",
            metadata={
                "metric": "functions",
                "percent": float(func_pct),
                "format": "lcov",
                "fnf": fnf,
                "fnh": fnh,
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_COVERAGE,
                "read_mode": READ_MODE_TEXT,
            },
        )


def _parse_cobertura_coverage(
    file_path: Path, relative: str, builder: EvidenceBuilder,
) -> None:
    """Parse Cobertura XML coverage report.

    Extracts line-rate and branch-rate from <coverage> root element.
    Rates are decimals (0.82 = 82%).
    """
    import xml.etree.ElementTree as ET

    text = _read_text(file_path)
    if not text:
        return

    root_el = ET.fromstring(text)

    line_rate = root_el.get("line-rate")
    branch_rate = root_el.get("branch-rate")

    if line_rate is not None:
        try:
            pct = round(float(line_rate) * 100, 1)
            builder.add(
                type_=EVIDENCE_COVERAGE_METRIC,
                category="test_health",
                summary=f"line coverage: {pct}% (Cobertura)",
                location_file=relative,
                subject="lines",
                raw_observation=f"lines:{pct}%:line-rate={line_rate}",
                confidence="High",
                metadata={
                    "metric": "lines",
                    "percent": float(pct),
                    "format": "cobertura_xml",
                    "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                    "completeness": COMPLETENESS_COMPLETE,
                    "parser": PARSER_COVERAGE,
                    "read_mode": READ_MODE_TEXT,
                },
            )
        except (ValueError, TypeError):
            pass

    if branch_rate is not None:
        try:
            pct = round(float(branch_rate) * 100, 1)
            builder.add(
                type_=EVIDENCE_COVERAGE_METRIC,
                category="test_health",
                summary=f"branch coverage: {pct}% (Cobertura)",
                location_file=relative,
                subject="branches",
                raw_observation=f"branches:{pct}%:branch-rate={branch_rate}",
                confidence="High",
                metadata={
                    "metric": "branches",
                    "percent": float(pct),
                    "format": "cobertura_xml",
                    "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                    "completeness": COMPLETENESS_COMPLETE,
                    "parser": PARSER_COVERAGE,
                    "read_mode": READ_MODE_TEXT,
                },
            )
        except (ValueError, TypeError):
            pass


def _parse_jacoco_coverage(
    file_path: Path, relative: str, builder: EvidenceBuilder,
) -> None:
    """Parse JaCoCo XML coverage report.

    JaCoCo uses <counter> elements with missed/covered attributes.
    Formula: coverage_pct = covered / (covered + missed) * 100

    Policy: prefer report-level counters. Only fall back to
    package-level counters if report-level counters are absent.
    Never sum report-level and child counters together.
    """
    import xml.etree.ElementTree as ET

    text = _read_text(file_path)
    if not text:
        return

    root_el = ET.fromstring(text)

    report_counters = list(root_el.findall("counter"))

    if report_counters:
        counters_to_use = report_counters
    else:
        counters_to_use = []
        for package in root_el.findall("package"):
            counters_to_use.extend(package.findall("counter"))

    TYPE_TO_METRIC = {
        "LINE": "lines",
        "BRANCH": "branches",
        "METHOD": "methods",
        "INSTRUCTION": "instructions",
        "COMPLEXITY": "complexity",
    }

    aggregated: dict[str, dict[str, int]] = {}
    for counter in counters_to_use:
        ctype = counter.get("type")
        if ctype is None:
            continue
        missed = int(counter.get("missed", 0))
        covered = int(counter.get("covered", 0))
        if ctype not in aggregated:
            aggregated[ctype] = {"missed": 0, "covered": 0}
        aggregated[ctype]["missed"] += missed
        aggregated[ctype]["covered"] += covered

    for ctype, data in aggregated.items():
        metric = TYPE_TO_METRIC.get(ctype)
        if metric is None:
            continue
        total = data["covered"] + data["missed"]
        if total == 0:
            continue
        pct = round(data["covered"] / total * 100, 1)
        builder.add(
            type_=EVIDENCE_COVERAGE_METRIC,
            category="test_health",
            summary=f"{metric} coverage: {pct}% (JaCoCo)",
            location_file=relative,
            subject=metric,
            raw_observation=f"{metric}:{pct}%:covered={data['covered']}/total={total}",
            confidence="High",
            metadata={
                "metric": metric,
                "percent": float(pct),
                "format": "jacoco_xml",
                "covered": data["covered"],
                "missed": data["missed"],
                "source": "report_level" if report_counters else "package_level",
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_COVERAGE,
                "read_mode": READ_MODE_TEXT,
            },
        )


def _scan_coverage_artifact(
    file_path: Path, relative: str, format_type: str, builder: EvidenceBuilder,
) -> None:
    """Scan a coverage report file."""
    builder.add(
        type_=EVIDENCE_COVERAGE_REPORT,
        category="test_health",
        summary=f"Coverage report detected: {relative}",
        location_file=relative,
        subject=relative,
        raw_observation=format_type,
        confidence="High",
        metadata={
            "format": format_type,
            "observation_strength": OBSERVATION_STRENGTH_DIRECT,
            "completeness": COMPLETENESS_COMPLETE,
            "parser": PARSER_COVERAGE,
            "read_mode": READ_MODE_JSON if format_type in ("istanbul_json", "python_coverage_json") else READ_MODE_TEXT,
        },
    )
    try:
        if format_type == "istanbul_json":
            _parse_istanbul_coverage(file_path, relative, builder)
        elif format_type == "python_coverage_json":
            _parse_python_coverage(file_path, relative, builder)
        elif format_type == "lcov":
            _parse_lcov_coverage(file_path, relative, builder)
        elif format_type == "cobertura_xml":
            _parse_cobertura_coverage(file_path, relative, builder)
        elif format_type == "jacoco_xml":
            _parse_jacoco_coverage(file_path, relative, builder)
    except Exception:
        # Malformed report — emit limitation evidence
        builder.add(
            type_=EVIDENCE_COVERAGE_GAP,
            category="test_health",
            summary=f"Coverage report {relative} could not be fully parsed",
            location_file=relative,
            subject=relative,
            raw_observation=f"parse_failure:{format_type}",
            confidence="Medium",
            metadata={
                "format": format_type,
                "reason": "malformed_report",
                "observation_strength": OBSERVATION_STRENGTH_LIMITATION,
                "completeness": COMPLETENESS_PARTIAL,
                "parser": PARSER_COVERAGE,
                "read_mode": READ_MODE_JSON if format_type in ("istanbul_json", "python_coverage_json") else READ_MODE_TEXT,
            },
        )


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
    _check_node_lockfile_conflicts(root, builder)
    _check_poetry_lockfile(root, builder)
    _check_pipfile_lockfile(root, builder)

    # Runtime version pinning (v3.3.0)
    _detect_runtime_version_pins(root, builder)

    # Repository-level coverage artifact scanning (v3.2.0)
    # Coverage dirs are normally excluded, so we scan them separately
    for pattern, format_type in _COVERAGE_PATTERNS.items():
        parts = pattern.split("/")
        candidate = root / Path(*parts)
        if candidate.exists() and candidate.is_file():
            rel = _relative(candidate, root)
            _scan_coverage_artifact(candidate, rel, format_type, builder)

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
            if file_path.name == "package.json":
                _check_node_unpinned_deps(file_path, relative, builder)
            if file_path.name == "requirements.txt":
                _check_python_unpinned_deps(file_path, relative, builder)
            if file_path.name == "pyproject.toml":
                _parse_pyproject_deps(file_path, relative, builder)
            if file_path.name == "Pipfile":
                _parse_pipfile_deps(file_path, relative, builder)

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
        for pattern, format_type in _COVERAGE_PATTERNS.items():
            if path_matches_exact_or_suffix(relative, pattern):
                _scan_coverage_artifact(file_path, relative, format_type, builder)
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
                            f"{marker}:{count}"
                            for marker, count in sorted(marker_counts.items())
                        ),
                        confidence="High",
                        metadata={
                            "marker_counts": marker_counts,
                            "total_count": total_marker_count,
                        },
                    )

            # Large file detection for source files
            if file_path.suffix in SOURCE_EXTENSIONS:
                line_count = text.count('\n') + 1
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
