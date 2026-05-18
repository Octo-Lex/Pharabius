"""Build architecture dependency graph from existing evidence.

Reads ``.ai-debt/evidence.json``, optional analysis-units, project-profile,
and architecture-policy. Produces ``architecture-graph.json`` with nodes,
edges, cycles, boundary violations, and coupling metrics.

This module is purely additive — it does not modify source artifacts.
"""

from __future__ import annotations

import contextlib
import fnmatch
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pharabius.schemas.architecture_graph import (
    ArchitectureCycle,
    ArchitectureEdge,
    ArchitectureGraph,
    ArchitectureNode,
    ArchitecturePolicy,
    BoundaryViolation,
    CouplingMetrics,
    PolicyLayer,
    stable_cycle_id,
    stable_node_id,
    stable_violation_id,
)

logger = logging.getLogger(__name__)

# ── Standard library filters ─────────────────────────────────────────

_PYTHON_STDLIB: frozenset[str] = frozenset(
    {
        "__future__",
        "abc",
        "argparse",
        "ast",
        "asyncio",
        "base64",
        "bisect",
        "calendar",
        "cgi",
        "cmd",
        "codecs",
        "collections",
        "colorsys",
        "compileall",
        "concurrent",
        "configparser",
        "contextlib",
        "copy",
        "csv",
        "ctypes",
        "dataclasses",
        "datetime",
        "decimal",
        "difflib",
        "dis",
        "email",
        "enum",
        "fileinput",
        "fnmatch",
        "fractions",
        "functools",
        "glob",
        "gzip",
        "hashlib",
        "heapq",
        "hmac",
        "html",
        "http",
        "importlib",
        "inspect",
        "io",
        "itertools",
        "json",
        "keyword",
        "linecache",
        "locale",
        "logging",
        "lzma",
        "mailbox",
        "marshal",
        "math",
        "mimetypes",
        "multiprocessing",
        "numbers",
        "operator",
        "os",
        "pathlib",
        "pdb",
        "pickle",
        "platform",
        "plistlib",
        "pprint",
        "profile",
        "pstats",
        "queue",
        "re",
        "readline",
        "reprlib",
        "secrets",
        "select",
        "shelve",
        "shlex",
        "shutil",
        "signal",
        "site",
        "socket",
        "socketserver",
        "sqlite3",
        "statistics",
        "string",
        "struct",
        "subprocess",
        "symtable",
        "sys",
        "sysconfig",
        "tabnanny",
        "tarfile",
        "tempfile",
        "textwrap",
        "threading",
        "time",
        "timeit",
        "token",
        "tokenize",
        "trace",
        "traceback",
        "tracemalloc",
        "turtle",
        "turtledemo",
        "types",
        "typing",
        "unicodedata",
        "unittest",
        "urllib",
        "uuid",
        "venv",
        "warnings",
        "weakref",
        "webbrowser",
        "wsgiref",
        "xml",
        "xmlrpc",
        "zipapp",
        "zipfile",
        "zipimport",
        "zlib",
    }
)

_JS_TS_STDLIB: frozenset[str] = frozenset(
    {
        "assert",
        "buffer",
        "child_process",
        "cluster",
        "console",
        "constants",
        "crypto",
        "dgram",
        "dns",
        "domain",
        "events",
        "fs",
        "http",
        "https",
        "module",
        "net",
        "os",
        "path",
        "perf_hooks",
        "process",
        "punycode",
        "querystring",
        "readline",
        "repl",
        "stream",
        "string_decoder",
        "sys",
        "timers",
        "tls",
        "tty",
        "url",
        "util",
        "v8",
        "vm",
        "worker_threads",
        "zlib",
    }
)

_TS_EXTENSIONS: list[str] = [".ts", ".tsx", ".js", ".jsx"]
_TS_INDEX_FILES: list[str] = [
    "index.ts",
    "index.tsx",
    "index.js",
    "index.jsx",
]

_SOURCE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".go",
        ".rs",
        ".java",
        ".rb",
        ".cs",
        ".php",
    }
)


# ── Data structures ──────────────────────────────────────────────────


@dataclass
class GraphResult:
    """Result of graph construction."""

    graph: ArchitectureGraph
    warnings: list[str] = field(default_factory=list)


# ── Import extraction ────────────────────────────────────────────────


def _extract_imports_from_evidence(item: dict[str, Any]) -> list[str]:
    """Extract import list from an evidence item with fallback.

    1. Prefer metadata.imports if present and list-like.
    2. Fallback: parse raw_observation as comma-separated.
    3. If neither, return empty list (caller adds limitation).
    """
    imports = item.get("metadata", {}).get("imports")
    if isinstance(imports, list) and imports:
        return [str(i) for i in imports]

    raw = item.get("raw_observation", "")
    if raw:
        return [i.strip() for i in raw.split(",") if i.strip()]

    return []


# ── Node derivation ──────────────────────────────────────────────────


def _derive_python_node_path(file_path: str) -> tuple[str, str]:
    """Derive (package_name, node_path) from a Python file path.

    Returns (name, path) where name is the top-level package/module name
    and path is the directory root for that node.
    """
    parts = Path(file_path).parts

    # src/<package>/... layout
    if len(parts) >= 3 and parts[0] == "src":
        # src/pharabius/core/analyzer.py -> name=pharabius, path=src/pharabius
        # src/myapp/utils.py -> name=myapp, path=src/myapp
        # Top-level package: parts[1]
        top_pkg = parts[1]
        # Node path is always src/<top_pkg> (directory, not file)
        return top_pkg, "src/" + top_pkg

    # Direct module at root
    if len(parts) >= 2:
        return parts[0], parts[0]

    # Single file
    p = Path(file_path)
    return p.stem, str(p.parent) if str(p.parent) != "." else "."


def _discover_python_internal_prefixes(
    root: Path,
    analysis_units: list[dict[str, Any]] | None = None,
) -> set[str]:
    """Discover internal Python package prefixes from repository structure."""
    prefixes: set[str] = set()

    # src/<package>/__init__.py layout
    for init in root.rglob("src/*/__init__.py"):
        parts = init.relative_to(root).parts
        if len(parts) >= 3:
            prefixes.add(parts[1])

    # Top-level directories with __init__.py (non-src layout)
    for init in root.glob("*/__init__.py"):
        prefixes.add(init.parent.name)

    # Analysis unit roots with Python files
    if analysis_units:
        for unit in analysis_units:
            files = unit.get("files", [])
            if any(str(f).endswith(".py") for f in files):
                rp = unit.get("root_path", "")
                if rp and rp != ".":
                    prefixes.add(Path(rp).parts[0] if Path(rp).parts else rp)

    return prefixes


def _is_python_stdlib(module_name: str) -> bool:
    """Check if a Python module name is stdlib."""
    top = module_name.split(".")[0]
    return top in _PYTHON_STDLIB


def _is_js_ts_stdlib(module_name: str) -> bool:
    """Check if a JS/TS module name is stdlib/builtin."""
    return module_name in _JS_TS_STDLIB


def _is_external_import(
    module_name: str,
    internal_prefixes: set[str],
) -> bool:
    """Check if a module import is external (not internal to this repo)."""
    top = module_name.split(".")[0]

    # Check if it matches any internal prefix
    for prefix in internal_prefixes:
        if top == prefix or module_name.startswith(prefix + "."):
            return False

    # Relative TS/JS imports start with ./
    return not module_name.startswith(".")


def _resolve_ts_relative(
    import_path: str,
    source_file: str,
    root: Path,
) -> str | None:
    """Resolve a relative TS/JS import by probing file extensions.

    Returns resolved file path relative to root, or None.
    """
    source_dir = (root / source_file).parent
    target = (source_dir / import_path).resolve()

    # Direct file match with extension probing
    for ext in _TS_EXTENSIONS:
        candidate = Path(str(target) + ext)
        try:
            return str(candidate.relative_to(root)).replace("\\", "/")
        except ValueError:
            continue

    # Index file match (directory import)
    for index in _TS_INDEX_FILES:
        candidate = target / index
        try:
            return str(candidate.relative_to(root)).replace("\\", "/")
        except ValueError:
            continue

    return None


# ── Language detection ─────────────────────────────────────────────


def _detect_file_language(file_path: str) -> str:
    ext = Path(file_path).suffix
    if ext in (".py",):
        return "python"
    if ext in (".ts", ".tsx", ".js", ".jsx"):
        return "typescript"
    if ext == ".rs":
        return "rust"
    if ext == ".go":
        return "go"
    if ext == ".java":
        return "java"
    return "unknown"


# ── TypeScript monorepo helpers ──────────────────────────────────────

_MONOREPO_ROOTS: frozenset[str] = frozenset({"packages", "apps", "services", "libs", "modules"})


def _discover_ts_packages(root: Path) -> dict[str, dict[str, str]]:
    """Discover TS/JS packages in monorepo structure.

    Returns dict of package_key -> {"name": str, "path": str, "dir": str}.
    Only discovers packages under known monorepo root directories
    (packages/*, apps/*, services/*, libs/*, modules/*).
    """
    packages: dict[str, dict[str, str]] = {}

    for monorepo_dir in _MONOREPO_ROOTS:
        monorepo_path = root / monorepo_dir
        if not monorepo_path.is_dir():
            continue

        for child in sorted(monorepo_path.iterdir()):
            if not child.is_dir():
                continue
            pkg_json = child / "package.json"
            if not pkg_json.exists():
                continue

            # Read package name
            pkg_name = child.name  # fallback
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8"))
                if isinstance(data.get("name"), str) and data["name"]:
                    pkg_name = data["name"]
            except (json.JSONDecodeError, OSError):
                pass

            rel_dir = str(child.relative_to(root)).replace("\\", "/")
            key = f"ts:{pkg_name}:{rel_dir}"
            packages[key] = {
                "name": pkg_name,
                "path": rel_dir,
                "dir": child.name,
            }

    return packages


def _is_ts_monorepo(root: Path, ts_packages: dict[str, dict[str, str]]) -> bool:
    """Check if repo has a TS monorepo structure."""
    return len(ts_packages) >= 1


def _derive_ts_node_path(
    file_path: str, ts_packages: dict[str, dict[str, str]]
) -> tuple[str, str] | None:
    """Derive (name, node_path) for a TS/JS file in a monorepo.

    Returns None if the file doesn't belong to any discovered package.
    """
    for _key, pkg in ts_packages.items():
        pkg_path = pkg["path"]
        if file_path.startswith(pkg_path + "/"):
            return pkg["name"], pkg_path
    return None


def _match_ts_workspace_import(import_name: str, package_names: set[str]) -> str | None:
    """Match a TS import against local package names using longest-prefix.

    Rules:
    1. Exact match first.
    2. Longest valid prefix only if followed by '/'.
    3. @repo/core-extra does NOT match @repo/core.
    """
    # Exact match
    if import_name in package_names:
        return import_name

    # Longest prefix match with / separator
    best: str | None = None
    for pkg_name in package_names:
        if import_name.startswith(pkg_name + "/") and (best is None or len(pkg_name) > len(best)):
            best = pkg_name
    return best


# ── Python sub-package helpers ──────────────────────────────────────


def _policy_has_subdirectory_layers(policy: ArchitecturePolicy | None, root: Path) -> bool:
    """Check if policy layers target subdirectories under src/<pkg>/."""
    if not policy or not policy.layers:
        return False

    # Collect all src/<pkg>/ prefixes from policy paths
    pkg_subdirs: dict[str, set[str]] = {}  # top_pkg -> set of subdirectories
    for layer in policy.layers:
        for path_pattern in layer.paths:
            norm = path_pattern.replace("\\", "/")
            # Match src/<pkg>/<sub>/... pattern
            parts = norm.split("/")
            if len(parts) >= 3 and parts[0] == "src" and parts[-1] == "**":
                top_pkg = parts[1]
                subdir = parts[2] if len(parts) >= 4 else None
                if subdir and subdir != "**":
                    if top_pkg not in pkg_subdirs:
                        pkg_subdirs[top_pkg] = set()
                    pkg_subdirs[top_pkg].add(subdir)

    return any(len(subs) >= 2 for _pkg, subs in pkg_subdirs.items())


def _derive_python_subpackage_path(file_path: str) -> tuple[str, str]:
    """Derive sub-package node from Python file path.

    src/myapp/api/routes.py -> name=myapp.api, path=src/myapp/api
    src/myapp/__init__.py -> name=myapp, path=src/myapp
    """
    parts = Path(file_path).parts
    if len(parts) >= 4 and parts[0] == "src":
        top_pkg = parts[1]
        sub_pkg = parts[2]
        if parts[3] == "__init__.py":
            # Root package init
            return top_pkg, "src/" + top_pkg
        # Sub-package
        name = f"{top_pkg}.{sub_pkg}"
        path = f"src/{top_pkg}/{sub_pkg}"
        return name, path
    # Fallback to default
    return _derive_python_node_path(file_path)


# ── Rust crate helpers ───────────────────────────────────────────────


def _discover_rust_crates(root: Path) -> dict[str, dict[str, str]]:
    """Discover Rust crates from Cargo.toml files.

    Returns dict of crate_key -> {"name": str, "path": str}.
    """
    crates: dict[str, dict[str, str]] = {}

    for cargo_toml in root.rglob("Cargo.toml"):
        try:
            text = cargo_toml.read_text(encoding="utf-8")
        except OSError:
            continue

        # Simple [package] name extraction
        in_package = False
        crate_name: str | None = None
        for line in text.splitlines():
            stripped = line.strip()
            if stripped == "[package]":
                in_package = True
                continue
            if stripped.startswith("[") and stripped.endswith("]"):
                in_package = False
                continue
            if in_package and stripped.startswith("name"):
                val = stripped.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    crate_name = val
                    break

        if not crate_name:
            continue

        rel_dir = str(cargo_toml.parent.relative_to(root)).replace("\\", "/")

        # Skip workspace root (path ".") if it's a workspace aggregator
        if rel_dir == "." and "[workspace]" in text:
            continue

        key = f"rust:{crate_name}:{rel_dir}"
        crates[key] = {"name": crate_name, "path": rel_dir}

    return crates


def _normalize_rust_crate_name(name: str) -> str:
    """Normalize Rust crate name for matching.

    Rust converts kebab-case to snake_case in use statements:
    symbiot-core -> symbiot_core
    """
    return name.replace("-", "_")


def _derive_rust_node_path(
    file_path: str,
    rust_crates: dict[str, dict[str, str]],
) -> tuple[str, str] | None:
    """Derive (name, node_path) for a Rust file in a workspace.

    Returns None if file doesn't belong to any discovered crate.
    """
    for _key, crate_info in rust_crates.items():
        crate_path = crate_info["path"]  # e.g. "crates/symbiot-cli"
        if file_path.startswith(crate_path + "/"):
            return crate_info["name"], crate_path
    return None


def _resolve_rust_import_to_node_id(
    import_name: str,
    rust_crates: dict[str, dict[str, str]],
    source_file: str,
    nodes: dict[str, ArchitectureNode],
) -> str | None:
    """Resolve a Rust import to a target node ID.

    Handles:
    - crate::foo -> match crate "foo" to node
    - crate::foo::bar -> match crate "foo" to node
    - super::module -> best-effort relative resolution
    """
    if import_name.startswith("crate::"):
        # crate::foo::bar -> extract crate-local module name
        parts = import_name[7:].split("::")  # strip 'crate::'
        if not parts:
            return None
        # The first component is a module name; try to match to containing node
        # For workspace crates, 'crate' refers to the current crate
        # We resolve by finding the source file's node and looking for sibling modules
        source_node_id = _file_to_node_id(source_file, nodes)
        if source_node_id:
            return source_node_id  # Intra-crate; maps to same node with current granularity
        return None

    if import_name.startswith("super::"):
        # super::module -> relative to parent directory
        # Best-effort: map to containing node
        source_node_id = _file_to_node_id(source_file, nodes)
        if source_node_id:
            return source_node_id  # Same node for current granularity
        return None

    if import_name.startswith("self::"):
        return None  # Intra-module, not a cross-node edge

    # External or workspace-external crate: check if it matches a local crate name
    top = import_name.split("::")[0]
    for _key, crate_info in rust_crates.items():
        if crate_info["name"] == top:
            # Find the node for this crate's directory
            for _nkey, node in nodes.items():
                if node.node_type == "analysis_unit":
                    continue
                if node.path == crate_info["path"] or node.name == top:
                    return node.node_id
            # Node doesn't exist yet; find by path prefix
            for _nkey, node in nodes.items():
                if node.node_type == "analysis_unit":
                    continue
                crate_dir = crate_info["path"]
                if crate_dir and node.path and crate_dir.startswith(node.path):
                    return node.node_id
    return None


def _resolve_ts_import(
    imp: str,
    file_path: str,
    nodes: dict[str, ArchitectureNode],
    root: Path | None,
    ts_package_names: set[str],
    ts_name_to_path: dict[str, str],
    internal_prefixes: set[str],
    limitations: list[str],
) -> str | None:
    """Resolve a TS/JS import to a target node ID."""
    # Relative import
    if imp.startswith("."):
        if root is None:
            return None
        resolved = _resolve_ts_relative(imp, file_path, root)
        if resolved:
            return _file_to_node_id(resolved, nodes)
        return None

    # Workspace/bare import
    if ts_package_names:
        matched = _match_ts_workspace_import(imp, ts_package_names)
        if matched:
            # Find the node for this package
            pkg_path = ts_name_to_path.get(matched, "")
            for _key, node in nodes.items():
                if node.node_type == "analysis_unit":
                    continue
                if node.path == pkg_path or node.name == matched:
                    return node.node_id
        return None  # No workspace match → external

    # No monorepo packages → use default resolution
    return _resolve_import_to_node_id(imp, nodes, internal_prefixes)


def _resolve_python_import(
    imp: str,
    nodes: dict[str, ArchitectureNode],
    internal_prefixes: set[str],
    limitations: list[str],
) -> str | None:
    """Resolve a Python import with sub-package support."""
    if _is_python_stdlib(imp):
        return None
    if _is_external_import(imp, internal_prefixes):
        return None

    # Try sub-package name match first (e.g., myapp.api)
    parts = imp.split(".")
    if len(parts) >= 2:
        sub_name = f"{parts[0]}.{parts[1]}"
        for _key, node in nodes.items():
            if node.node_type == "analysis_unit":
                continue
            if node.name == sub_name:
                return node.node_id

    # Fallback to top-level match
    return _resolve_import_to_node_id(imp, nodes, internal_prefixes)


def _resolve_rust_import(
    imp: str,
    file_path: str,
    nodes: dict[str, ArchitectureNode],
    rust_crates: dict[str, dict[str, str]],
    internal_prefixes: set[str],
    limitations: list[str],
) -> str | None:
    """Resolve a Rust import to a target node ID (edge-level)."""
    # Intra-crate references (crate::, super::, self::) → same node
    if imp.startswith("crate::") or imp.startswith("super::") or imp.startswith("self::"):
        return None  # No cross-node edge for intra-crate refs

    # External or workspace crate
    top = imp.split("::")[0]
    top_normalized = _normalize_rust_crate_name(top)
    for _key, crate_info in rust_crates.items():
        crate_name_normalized = _normalize_rust_crate_name(crate_info["name"])
        if crate_name_normalized == top_normalized or crate_info["name"] == top:
            # Find the node for this crate's directory
            for _nkey, node in nodes.items():
                if node.node_type == "analysis_unit":
                    continue
                if node.path == crate_info["path"] or node.name == crate_info["name"]:
                    return node.node_id
    return None  # External crate


# ── Node construction ────────────────────────────────────────────────


def _build_package_nodes(
    imports_evidence: list[dict[str, Any]],
    analysis_units: list[dict[str, Any]] | None,
    *,
    root: Path | None = None,
    enable_python_subpackages: bool = False,
    rust_crates: dict[str, dict[str, str]] | None = None,
) -> dict[str, ArchitectureNode]:
    """Build package/module nodes from imports evidence.

    Returns dict of node_key -> ArchitectureNode.
    Language-aware: dispatches to appropriate derivation per file type.
    """
    nodes: dict[str, ArchitectureNode] = {}

    # Precompute TS monorepo packages
    ts_packages: dict[str, dict[str, str]] = {}
    is_ts_monorepo = False
    if root:
        ts_packages = _discover_ts_packages(root)
        is_ts_monorepo = _is_ts_monorepo(root, ts_packages)

    for item in imports_evidence:
        file_path = item.get("location", {}).get("file", "")
        if not file_path:
            continue

        lang = _detect_file_language(file_path)
        name: str | None = None
        node_path: str | None = None
        node_type = "module"

        if lang == "typescript" and is_ts_monorepo:
            result = _derive_ts_node_path(file_path, ts_packages)
            if result:
                name, node_path = result
                node_type = "module"
            # else: falls through to default

        if lang == "rust" and rust_crates:
            result = _derive_rust_node_path(file_path, rust_crates)
            if result:
                name, node_path = result
                node_type = "module"
            # else: falls through to default

        if lang == "python" and enable_python_subpackages:
            name, node_path = _derive_python_subpackage_path(file_path)
            parts = Path(file_path).parts
            node_type = "package" if len(parts) >= 3 and parts[0] == "src" else "module"

        if name is None or node_path is None:
            # Default: Python-style derivation
            name, node_path = _derive_python_node_path(file_path)
            suffix = Path(file_path).suffix
            if suffix in _SOURCE_EXTENSIONS:
                parts = Path(file_path).parts
                node_type = "package" if len(parts) >= 3 and parts[0] == "src" else "module"
            else:
                node_type = "module"

        key = f"{node_type}:{name}:{node_path}"

        if key not in nodes:
            au_id = ""
            if analysis_units:
                for unit in analysis_units:
                    unit_files = unit.get("files", [])
                    unit_root = unit.get("root_path", "")
                    if file_path in unit_files or (unit_root and file_path.startswith(unit_root)):
                        au_id = unit.get("analysis_unit_id", "")
                        break

            nid = stable_node_id(node_type, name, node_path)
            nodes[key] = ArchitectureNode(
                node_id=nid,
                node_type=node_type,
                name=name,
                path=node_path,
                analysis_unit_id=au_id,
                files=[],
            )

        if file_path not in nodes[key].files:
            nodes[key].files.append(file_path)

    return nodes


def _build_analysis_unit_nodes(
    analysis_units: list[dict[str, Any]],
) -> dict[str, ArchitectureNode]:
    """Build analysis-unit nodes from analysis-units.json.

    Returns dict of analysis_unit_id -> ArchitectureNode.
    """
    nodes: dict[str, ArchitectureNode] = {}

    for unit in analysis_units:
        au_id = unit.get("analysis_unit_id", "")
        if not au_id:
            continue

        name = unit.get("name", au_id)
        root_path = unit.get("root_path", "")
        files = unit.get("files", [])

        nid = stable_node_id("analysis_unit", name, root_path)
        nodes[au_id] = ArchitectureNode(
            node_id=nid,
            node_type="analysis_unit",
            name=name,
            path=root_path,
            analysis_unit_id=au_id,
            files=list(files) if isinstance(files, list) else [],
        )

    return nodes


# ── Edge construction ────────────────────────────────────────────────


def _file_to_node_id(file_path: str, nodes: dict[str, ArchitectureNode]) -> str | None:
    """Map a file path to its node ID."""
    for _key, node in nodes.items():
        if file_path in node.files:
            return node.node_id
        # Check if file is under node path
        if node.path and node.path != "." and file_path.startswith(node.path.replace("\\", "/")):
            return node.node_id
    return None


def _resolve_import_to_node_id(
    import_name: str,
    nodes: dict[str, ArchitectureNode],
    internal_prefixes: set[str],
) -> str | None:
    """Resolve an import name to a target node ID.

    Returns None if external, stdlib, or unresolved.
    """
    top = import_name.split(".")[0]

    # Skip stdlib
    if _is_python_stdlib(import_name):
        return None

    # Skip external
    if _is_external_import(import_name, internal_prefixes):
        return None

    # Try to match to existing nodes
    # Direct match: node name equals top-level import
    for _key, node in nodes.items():
        if node.node_type == "analysis_unit":
            continue
        if node.name == top:
            return node.node_id

    # Prefix match: import starts with node name
    for _key, node in nodes.items():
        if node.node_type == "analysis_unit":
            continue
        if top.startswith(node.name) or import_name.startswith(node.name + "."):
            return node.node_id

    return None


def _build_edges(
    imports_evidence: list[dict[str, Any]],
    nodes: dict[str, ArchitectureNode],
    internal_prefixes: set[str],
    limitations: list[str],
    *,
    root: Path | None = None,
    ts_packages: dict[str, dict[str, str]] | None = None,
    rust_crates: dict[str, dict[str, str]] | None = None,
) -> list[ArchitectureEdge]:
    """Build internal import edges from evidence."""
    agg: dict[tuple[str, str], dict[str, Any]] = {}

    # Precompute TS package names for workspace matching
    ts_package_names: set[str] = set()
    ts_name_to_path: dict[str, str] = {}
    if ts_packages:
        for _key, pkg in ts_packages.items():
            ts_package_names.add(pkg["name"])
            ts_name_to_path[pkg["name"]] = pkg["path"]

    for item in imports_evidence:
        file_path = item.get("location", {}).get("file", "")
        evidence_id = item.get("evidence_id", "")

        source_node_id = _file_to_node_id(file_path, nodes)
        if not source_node_id:
            continue

        imports = _extract_imports_from_evidence(item)
        if not imports:
            limitations.append(f"No import data in {evidence_id} ({file_path}); skipped.")
            continue

        lang = _detect_file_language(file_path)

        for imp in imports:
            target_node_id: str | None = None

            if lang == "typescript":
                target_node_id = _resolve_ts_import(
                    imp,
                    file_path,
                    nodes,
                    root,
                    ts_package_names,
                    ts_name_to_path,
                    internal_prefixes,
                    limitations,
                )
            elif lang == "rust":
                target_node_id = _resolve_rust_import(
                    imp,
                    file_path,
                    nodes,
                    rust_crates or {},
                    internal_prefixes,
                    limitations,
                )
            elif lang == "python" and "." in imp:
                # Python with possible sub-package resolution
                target_node_id = _resolve_python_import(
                    imp,
                    nodes,
                    internal_prefixes,
                    limitations,
                )
            else:
                # Default resolution
                target_node_id = _resolve_import_to_node_id(
                    imp,
                    nodes,
                    internal_prefixes,
                )

            if target_node_id is None:
                if _is_python_stdlib(imp) or _is_js_ts_stdlib(imp):
                    continue
                if _is_external_import(imp, internal_prefixes):
                    continue
                # Rust external crates
                if lang == "rust" and "::" in imp:
                    top = imp.split("::")[0]
                    if top in ("crate", "super", "self"):
                        continue  # Intra-crate, not a cross-node edge
                    # Check if it's a known local crate
                    is_local = False
                    if rust_crates:
                        for _ck, ci in rust_crates.items():
                            if ci["name"] == top:
                                is_local = True
                                break
                    if not is_local:
                        continue  # External crate
                limitations.append(f"Unresolved internal-looking import '{imp}' in {file_path}.")
                continue

            if target_node_id == source_node_id:
                continue  # Self-import, skip

            key = (source_node_id, target_node_id)
            if key not in agg:
                agg[key] = {
                    "source_node_id": source_node_id,
                    "target_node_id": target_node_id,
                    "import_count": 0,
                    "evidence_ids": [],
                    "files": [],
                }
            entry = agg[key]
            entry["import_count"] += 1
            if evidence_id and evidence_id not in entry["evidence_ids"]:
                entry["evidence_ids"].append(evidence_id)
            if file_path and file_path not in entry["files"]:
                entry["files"].append(file_path)

    return [
        ArchitectureEdge(
            source_node_id=v["source_node_id"],
            target_node_id=v["target_node_id"],
            edge_type="internal_import",
            import_count=v["import_count"],
            evidence_ids=v["evidence_ids"],
            files=v["files"],
        )
        for v in agg.values()
    ]


# ── Cycle detection (Tarjan SCC) ────────────────────────────────────


def _find_sccs(
    node_ids: list[str],
    adjacency: dict[str, list[str]],
) -> list[list[str]]:
    """Tarjan's SCC algorithm. Returns SCCs with size >= 2 (cycles)."""
    index_counter = [0]
    stack: list[str] = []
    on_stack: set[str] = set()
    index_map: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    sccs: list[list[str]] = []

    def strongconnect(v: str) -> None:
        index_map[v] = lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack.add(v)

        for w in adjacency.get(v, []):
            if w not in index_map:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], index_map[w])

        if lowlink[v] == index_map[v]:
            scc: list[str] = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                scc.append(w)
                if w == v:
                    break
            if len(scc) >= 2:
                sccs.append(sorted(scc))

    for v in sorted(node_ids):
        if v not in index_map:
            strongconnect(v)

    return sccs


def _detect_cycles(
    nodes: list[ArchitectureNode],
    edges: list[ArchitectureEdge],
) -> list[ArchitectureCycle]:
    """Detect dependency cycles via Tarjan SCC."""
    node_ids = [n.node_id for n in nodes]
    node_name_map = {n.node_id: n.name for n in nodes}

    # Build adjacency list from internal edges
    adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for edge in edges:
        if edge.source_node_id in adjacency:
            adjacency[edge.source_node_id].append(edge.target_node_id)

    sccs = _find_sccs(node_ids, adjacency)

    cycles: list[ArchitectureCycle] = []
    for scc in sccs:
        # Collect evidence IDs from edges within the SCC
        scc_set = set(scc)
        scc_evidence: list[str] = []
        scc_edge_count = 0
        for edge in edges:
            if edge.source_node_id in scc_set and edge.target_node_id in scc_set:
                scc_edge_count += 1
                scc_evidence.extend(edge.evidence_ids)

        # Severity hint
        # Check if cycle spans multiple top-level packages
        node_types = set()
        for nid in scc:
            for n in nodes:
                if n.node_id == nid:
                    node_types.add(n.name.split(".")[0] if "." in n.name else n.name)

        severity = "High" if len(node_types) > 1 else "Medium"

        cycle_id = stable_cycle_id(scc)
        names = [node_name_map.get(nid, nid) for nid in sorted(scc)]
        desc = " -> ".join([*names, names[0]]) + f" ({len(scc)} nodes, {scc_edge_count} edges)"

        cycles.append(
            ArchitectureCycle(
                cycle_id=cycle_id,
                node_ids=sorted(scc),
                edge_count=scc_edge_count,
                evidence_ids=sorted(set(scc_evidence)),
                severity_hint=severity,
                description=desc,
            )
        )

    return cycles


# ── Coupling metrics ─────────────────────────────────────────────────


def _compute_coupling_metrics(
    nodes: list[ArchitectureNode],
    edges: list[ArchitectureEdge],
) -> list[CouplingMetrics]:
    """Compute fan_in, fan_out, instability for each node."""
    node_ids = [n.node_id for n in nodes]

    fan_in: dict[str, int] = dict.fromkeys(node_ids, 0)
    fan_out: dict[str, int] = dict.fromkeys(node_ids, 0)
    ev_count: dict[str, int] = dict.fromkeys(node_ids, 0)

    for edge in edges:
        if edge.target_node_id in fan_in:
            fan_in[edge.target_node_id] += 1
        if edge.source_node_id in fan_out:
            fan_out[edge.source_node_id] += 1
        if edge.source_node_id in ev_count:
            ev_count[edge.source_node_id] += len(edge.evidence_ids)
        if edge.target_node_id in ev_count:
            ev_count[edge.target_node_id] += len(edge.evidence_ids)

    metrics: list[CouplingMetrics] = []
    for nid in node_ids:
        fi = fan_in[nid]
        fo = fan_out[nid]
        total = fi + fo
        instability = fo / total if total > 0 else 0.0
        metrics.append(
            CouplingMetrics(
                node_id=nid,
                fan_in=fi,
                fan_out=fo,
                instability=round(instability, 4),
                evidence_count=ev_count[nid],
            )
        )

    return metrics


# ── Boundary policy ──────────────────────────────────────────────────


def _load_policy(path: Path) -> ArchitecturePolicy | None:
    """Load architecture policy from YAML file.

    Returns None if file missing or parse error.
    """
    if not path.exists():
        return None

    try:
        import yaml
    except ImportError:
        # Try to parse as simple YAML without dependency
        return _parse_simple_yaml_policy(path)

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return ArchitecturePolicy.model_validate(data)
    except Exception as exc:
        logger.warning("Could not parse policy: %s", exc)
        return None


def _parse_simple_yaml_policy(path: Path) -> ArchitecturePolicy | None:
    """Fallback YAML parser for architecture-policy.yaml.

    Handles the simple nested structure without requiring pyyaml.
    """
    try:
        text = path.read_text(encoding="utf-8")
        data: dict[str, Any] = {"schema_version": "1.0", "layers": []}
        current_layer: dict[str, Any] | None = None
        current_field: str | None = None

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if line.startswith("  - name:"):
                if current_layer:
                    data["layers"].append(current_layer)
                current_layer = {
                    "name": stripped[len("name:") :].strip().strip('"').strip("'"),
                    "paths": [],
                    "may_import": [],
                }
                current_field = None
            elif line.startswith("    paths:"):
                current_field = "paths"
            elif line.startswith("    may_import:"):
                current_field = "may_import"
            elif line.startswith("      - ") and current_layer and current_field:
                value = stripped[len("- ") :].strip().strip('"').strip("'")
                if current_field in current_layer and isinstance(
                    current_layer[current_field], list
                ):
                    current_layer[current_field].append(value)
            elif line.startswith("schema_version:"):
                data["schema_version"] = (
                    stripped[len("schema_version:") :].strip().strip('"').strip("'")
                )

        if current_layer:
            data["layers"].append(current_layer)

        return ArchitecturePolicy.model_validate(data)
    except Exception as exc:
        logger.warning("Could not parse policy: %s", exc)
        return None


def _match_layer(
    file_path: str,
    layers: list[PolicyLayer],
) -> str | None:
    """Match a file path to a policy layer.

    Uses glob/fnmatch patterns from layer paths.
    Returns layer name or None.
    """
    for layer in layers:
        for pattern in layer.paths:
            # Normalize separators
            norm_pattern = pattern.replace("\\", "/")
            norm_path = file_path.replace("\\", "/")

            if norm_pattern.endswith("/**"):
                # Directory prefix match
                prefix = norm_pattern[:-3]
                if norm_path.startswith(prefix):
                    return layer.name
            elif "*" in norm_pattern or "?" in norm_pattern:
                if fnmatch.fnmatch(norm_path, norm_pattern):
                    return layer.name
            else:
                if norm_path == norm_pattern:
                    return layer.name

    return None


def _check_boundary_violations(
    edges: list[ArchitectureEdge],
    nodes: list[ArchitectureNode],
    policy: ArchitecturePolicy,
) -> list[BoundaryViolation]:
    """Check edges for layer boundary violations."""
    if not policy.layers:
        return []

    # Build node_id -> name map and node_id -> representative file map
    node_map: dict[str, ArchitectureNode] = {n.node_id: n for n in nodes}

    # Build layer_name -> may_import set
    layer_allowed: dict[str, set[str]] = {}
    for layer in policy.layers:
        layer_allowed[layer.name] = set(layer.may_import)

    # Build layer_name -> PolicyLayer
    {layer.name: layer for layer in policy.layers}

    violations: list[BoundaryViolation] = []

    for edge in edges:
        source_node = node_map.get(edge.source_node_id)
        target_node = node_map.get(edge.target_node_id)
        if not source_node or not target_node:
            continue

        # Find source layer from any of its files
        source_layer: str | None = None
        for f in source_node.files:
            source_layer = _match_layer(f, policy.layers)
            if source_layer:
                break

        # Find target layer
        target_layer: str | None = None
        for f in target_node.files:
            target_layer = _match_layer(f, policy.layers)
            if target_layer:
                break
        if not target_layer:
            # Try matching by node name
            for layer in policy.layers:
                if layer.name == target_node.name:
                    target_layer = layer.name
                    break
        if not target_layer:
            # Try matching by node path against policy layer paths
            for layer in policy.layers:
                for pattern in layer.paths:
                    norm = pattern.replace("\\", "/")
                    if norm.endswith("/**"):
                        prefix = norm[:-3]
                        if target_node.path and target_node.path.startswith(prefix):
                            target_layer = layer.name
                            break
                if target_layer:
                    break

        # Skip if either not in policy
        if not source_layer or not target_layer:
            continue

        # Same-layer imports allowed
        if source_layer == target_layer:
            continue

        # Check violation
        allowed = layer_allowed.get(source_layer, set())
        if target_layer not in allowed:
            rule = f"{source_layer} may not import {target_layer}"
            vid = stable_violation_id(
                edge.source_node_id,
                edge.target_node_id,
                "architecture-policy",
                rule,
            )
            desc = (
                f"{source_node.name} ({source_layer}) imports "
                f"{target_node.name} ({target_layer}) — {rule}"
            )
            violations.append(
                BoundaryViolation(
                    violation_id=vid,
                    source_node_id=edge.source_node_id,
                    target_node_id=edge.target_node_id,
                    policy_name="architecture-policy",
                    rule=rule,
                    evidence_ids=edge.evidence_ids,
                    severity_hint="High",
                    description=desc,
                )
            )

    return violations


# ── Main entry point ─────────────────────────────────────────────────


def build_graph(
    repository_root: Path,
    *,
    scope: str = "both",
    policy_path: Path | None = None,
) -> GraphResult:
    """Build architecture dependency graph from existing evidence.

    Args:
        repository_root: Repository root containing .ai-debt/.
        scope: 'package', 'analysis_unit', or 'both'.
        policy_path: Optional path to architecture-policy.yaml.

    Returns:
        GraphResult with ArchitectureGraph and warnings.

    Raises:
        FileNotFoundError: If evidence.json is missing.
        ValueError: If evidence.json is malformed or scope requires missing units.
    """
    root = repository_root.resolve()
    ai_debt = root / ".ai-debt"

    # ── Load evidence.json (required) ────────────────────────────
    evidence_path = ai_debt / "evidence.json"
    if not evidence_path.exists():
        raise FileNotFoundError("evidence.json not found. Run 'ai-debt scan' first.")

    try:
        evidence_data = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"Could not read evidence.json: {exc}") from exc

    all_evidence = evidence_data.get("evidence", [])
    imports_evidence = [
        e for e in all_evidence if isinstance(e, dict) and e.get("type") == "imports_detected"
    ]

    # ── Load analysis-units.json (optional, scope-dependent) ─────
    units_path = ai_debt / "analysis-units.json"
    analysis_units: list[dict[str, Any]] | None = None
    units_loaded = False

    if units_path.exists():
        try:
            units_data = json.loads(units_path.read_text(encoding="utf-8"))
            analysis_units = units_data.get("units", [])
            units_loaded = True
        except (json.JSONDecodeError, OSError):
            pass

    # Scope validation
    include_au = scope in ("analysis_unit", "both")
    include_pkg = scope in ("package", "both")

    if scope == "analysis_unit" and not units_loaded:
        raise FileNotFoundError(
            "analysis-units.json not found. Run 'ai-debt map' first or use --scope package."
        )

    # ── Load project-profile.json (optional) ─────────────────────
    profile_path = ai_debt / "project-profile.json"
    profile_data: dict[str, Any] | None = None
    if profile_path.exists():
        with contextlib.suppress(json.JSONDecodeError, OSError):
            profile_data = json.loads(profile_path.read_text(encoding="utf-8"))

    # ── Initialize graph and limitations ──────────────────────────
    limitations: list[str] = []
    warnings: list[str] = []

    if not units_loaded and include_au:
        limitations.append("analysis-units.json not found; analysis-unit graph scope skipped.")

    if not profile_data:
        limitations.append(
            "project-profile.json not found; language-aware node derivation limited."
        )

    # ── Detect internal prefixes ─────────────────────────────────
    internal_prefixes = _discover_python_internal_prefixes(root, analysis_units)

    # ── Discover TS packages and Rust crates ──────────────────────
    ts_packages = _discover_ts_packages(root)
    rust_crates = _discover_rust_crates(root)

    # ── Load policy for sub-package decision ───────────────────────
    resolved_policy_path = policy_path or (ai_debt / "architecture-policy.yaml")
    policy = _load_policy(resolved_policy_path)
    enable_python_subpackages = _policy_has_subdirectory_layers(policy, root)

    # ── Build nodes ───────────────────────────────────────────────
    all_nodes: dict[str, ArchitectureNode] = {}

    if include_pkg:
        pkg_nodes = _build_package_nodes(
            imports_evidence,
            analysis_units,
            root=root,
            enable_python_subpackages=enable_python_subpackages,
            rust_crates=rust_crates,
        )
        all_nodes.update(pkg_nodes)

    if include_au and analysis_units:
        au_nodes = _build_analysis_unit_nodes(analysis_units)
        for au_id, node in au_nodes.items():
            # Use node_id as key to avoid collisions
            all_nodes[f"au:{au_id}"] = node

    # ── Build edges ───────────────────────────────────────────────
    # Augment internal prefixes with discovered sub-package prefixes
    if enable_python_subpackages:
        for _key, node in all_nodes.items():
            if node.node_type == "analysis_unit":
                continue
            if "." in node.name:
                top = node.name.split(".")[0]
                internal_prefixes.add(top)
            else:
                internal_prefixes.add(node.name)

    # Create synthetic nodes for unresolved policy layer targets
    if enable_python_subpackages and policy:
        existing_names = {n.name for n in all_nodes.values() if n.node_type != "analysis_unit"}
        for item in imports_evidence:
            file_path = item.get("location", {}).get("file", "")
            if not file_path or _detect_file_language(file_path) != "python":
                continue
            imports = _extract_imports_from_evidence(item)
            for imp in imports:
                parts = imp.split(".")
                if len(parts) >= 2:
                    sub_name = f"{parts[0]}.{parts[1]}"
                    if sub_name not in existing_names:
                        # Check if this matches a policy layer
                        for layer in policy.layers:
                            for path_pattern in layer.paths:
                                norm = path_pattern.replace("\\", "/")
                                pat_parts = norm.split("/")
                                if (
                                    len(pat_parts) >= 4
                                    and pat_parts[0] == "src"
                                    and pat_parts[-1] == "**"
                                    and pat_parts[2] == parts[1]
                                    and pat_parts[1] == parts[0]
                                ):
                                    node_path = f"src/{parts[0]}/{parts[1]}"
                                    nid = stable_node_id("package", sub_name, node_path)
                                    key = f"package:{sub_name}:{node_path}"
                                    if key not in all_nodes:
                                        all_nodes[key] = ArchitectureNode(
                                            node_id=nid,
                                            node_type="package",
                                            name=sub_name,
                                            path=node_path,
                                            analysis_unit_id="",
                                            files=[],
                                        )
                                        existing_names.add(sub_name)
                                    break

    # Create synthetic nodes for Rust import targets matching discovered crates
    if rust_crates:
        existing_names = {n.name for n in all_nodes.values() if n.node_type != "analysis_unit"}
        existing_paths = {n.path for n in all_nodes.values() if n.node_type != "analysis_unit"}
        for item in imports_evidence:
            file_path = item.get("location", {}).get("file", "")
            if not file_path or _detect_file_language(file_path) != "rust":
                continue
            imports = _extract_imports_from_evidence(item)
            for imp in imports:
                if (
                    imp.startswith("crate::")
                    or imp.startswith("super::")
                    or imp.startswith("self::")
                ):
                    continue
                top = imp.split("::")[0]
                top_normalized = _normalize_rust_crate_name(top)
                for _key, crate_info in rust_crates.items():
                    crate_name_normalized = _normalize_rust_crate_name(crate_info["name"])
                    if (crate_name_normalized == top_normalized or crate_info["name"] == top) and (
                        crate_info["name"] not in existing_names
                        and crate_info["path"] not in existing_paths
                    ):
                        node_path = crate_info["path"]
                        nid = stable_node_id("module", crate_info["name"], node_path)
                        key = f"module:{crate_info['name']}:{node_path}"
                        if key not in all_nodes:
                            all_nodes[key] = ArchitectureNode(
                                node_id=nid,
                                node_type="module",
                                name=crate_info["name"],
                                path=node_path,
                                analysis_unit_id="",
                                files=[],
                            )
                            existing_names.add(crate_info["name"])
                            existing_paths.add(node_path)
                        break

    # Only package/module nodes participate in import edges
    pkg_node_ids = {k: v for k, v in all_nodes.items() if v.node_type != "analysis_unit"}
    edges = _build_edges(
        imports_evidence,
        pkg_node_ids,
        internal_prefixes,
        limitations,
        root=root,
        ts_packages=ts_packages,
        rust_crates=rust_crates,
    )

    # ── Detect cycles ─────────────────────────────────────────────
    cycles = _detect_cycles(list(all_nodes.values()), edges)

    # ── Check boundaries ──────────────────────────────────────────
    violations: list[BoundaryViolation] = []

    if policy:
        violations = _check_boundary_violations(edges, list(all_nodes.values()), policy)
    else:
        # Check if .importlinter exists
        importlinter_path = root / ".importlinter"
        if importlinter_path.exists():
            limitations.append(
                "Import Linter configuration (.importlinter) detected but not parsed. "
                "Translate layer policy into "
                ".ai-debt/architecture-policy.yaml for boundary checking."
            )
        limitations.append("No architecture policy found; boundary checks skipped.")

    # ── Compute coupling metrics ─────────────────────────────────
    coupling = _compute_coupling_metrics(list(all_nodes.values()), edges)

    # ── Handle zero-import case ───────────────────────────────────
    if not imports_evidence:
        limitations.append("No imports_detected evidence found; graph is empty.")

    # ── Build final graph ─────────────────────────────────────────
    repo_name = ""
    if profile_data:
        repo_name = profile_data.get("project_name", "")
    if not repo_name:
        repo_name = root.name

    graph = ArchitectureGraph(
        schema_version="1.0",
        repository=repo_name,
        generated_at=datetime.now(UTC).isoformat(),
        graph_scope=scope,
        nodes=list(all_nodes.values()),
        edges=edges,
        cycles=cycles,
        boundary_violations=violations,
        coupling_metrics=coupling,
        limitations=limitations,
    )

    return GraphResult(graph=graph, warnings=warnings)
