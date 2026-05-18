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


# ── Node construction ────────────────────────────────────────────────


def _build_package_nodes(
    imports_evidence: list[dict[str, Any]],
    analysis_units: list[dict[str, Any]] | None,
) -> dict[str, ArchitectureNode]:
    """Build package/module nodes from imports evidence.

    Returns dict of node_key -> ArchitectureNode.
    """
    nodes: dict[str, ArchitectureNode] = {}

    for item in imports_evidence:
        file_path = item.get("location", {}).get("file", "")
        if not file_path:
            continue

        name, node_path = _derive_python_node_path(file_path)

        # Determine node type
        suffix = Path(file_path).suffix
        if suffix in _SOURCE_EXTENSIONS:
            # Check if this looks like a package directory
            parts = Path(file_path).parts
            node_type = "package" if len(parts) >= 3 and parts[0] == "src" else "module"
        else:
            node_type = "module"

        key = f"{node_type}:{name}:{node_path}"

        if key not in nodes:
            # Find matching analysis unit
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

        # Add file to node
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
) -> list[ArchitectureEdge]:
    """Build internal import edges from evidence."""
    # Aggregate edges by (source_node_id, target_node_id)
    agg: dict[tuple[str, str], dict[str, Any]] = {}

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

        for imp in imports:
            target_node_id = _resolve_import_to_node_id(imp, nodes, internal_prefixes)

            if target_node_id is None:
                # Could be stdlib, external, or unresolved internal
                if _is_python_stdlib(imp) or _is_js_ts_stdlib(imp):
                    continue
                if _is_external_import(imp, internal_prefixes):
                    continue
                # Looks internal but unresolved
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

    # ── Build nodes ───────────────────────────────────────────────
    all_nodes: dict[str, ArchitectureNode] = {}

    if include_pkg:
        pkg_nodes = _build_package_nodes(imports_evidence, analysis_units)
        all_nodes.update(pkg_nodes)

    if include_au and analysis_units:
        au_nodes = _build_analysis_unit_nodes(analysis_units)
        for au_id, node in au_nodes.items():
            # Use node_id as key to avoid collisions
            all_nodes[f"au:{au_id}"] = node

    # ── Build edges ───────────────────────────────────────────────
    # Only package/module nodes participate in import edges
    pkg_node_ids = {k: v for k, v in all_nodes.items() if v.node_type != "analysis_unit"}
    edges = _build_edges(imports_evidence, pkg_node_ids, internal_prefixes, limitations)

    # ── Detect cycles ─────────────────────────────────────────────
    cycles = _detect_cycles(list(all_nodes.values()), edges)

    # ── Load policy and check boundaries ──────────────────────────
    violations: list[BoundaryViolation] = []

    resolved_policy_path = policy_path or (ai_debt / "architecture-policy.yaml")
    policy = _load_policy(resolved_policy_path)

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
