"""Enhanced risk scoring — graph/git-backed scoring factors.

Scoring principles:
- Evidence-backed only — factors derive from repository data
- Deterministic at a fixed commit — same repo + commit = same scores
- Conservative by default — disabled unless explicitly opted in
- Missing data falls back safely — factor = Low (1), warning logged
- No network access — git is local only
- No provider/AI involvement — purely deterministic
- No governance.yaml scoring flags — scoring config in config.yaml
- No review sidecar influence — review decisions never affect scoring

Factor scale matches the existing Pharabius risk model:
  Low = 1, Medium = 3, High = 5, Critical = 8 (reserved/deferred for v1.5)
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Factor scale (matches existing risk model) ────────────────────────

FACTOR_SCALE: dict[str, int] = {
    "Low": 1,
    "Medium": 3,
    "High": 5,
    "Critical": 8,  # reserved — not emitted in v1.5
}


# ── Signal dataclasses ────────────────────────────────────────────────


@dataclass
class CentralitySignal:
    """Architecture centrality signal for a single path."""

    path: str
    level: str  # "Low", "Medium", "High"
    value: int
    reason: str
    source: str = "architecture-graph.json"


@dataclass
class ChangeFrequencySignal:
    """Change frequency signal for a single path."""

    path: str
    commit_count: int
    level: str  # "Low", "Medium", "High"
    value: int
    reason: str
    source: str = "git log"


# ── Architecture centrality ──────────────────────────────────────────


def _load_graph(graph_path: Path) -> dict[str, Any] | None:
    """Load architecture-graph.json. Returns None if missing/malformed."""
    if not graph_path.exists():
        return None
    try:
        data: dict[str, Any] | None = json.loads(graph_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        return None
    except (json.JSONDecodeError, OSError):
        logger.warning("Malformed architecture-graph.json, skipping centrality")
        return None


def _compute_node_metrics(
    graph: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Compute fan-in, fan-out, and cycle participation per node."""
    nodes: dict[str, dict[str, Any]] = {}

    # Initialize from graph nodes
    for node in graph.get("nodes", []):
        nid = node.get("id", "")
        npath = node.get("path", nid)
        nodes[nid] = {
            "path": npath,
            "fan_in": 0,
            "fan_out": 0,
            "in_cycle": False,
        }

    # Count edges
    for edge in graph.get("edges", []):
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        if src in nodes:
            nodes[src]["fan_out"] += 1
        if tgt in nodes:
            nodes[tgt]["fan_in"] += 1

    # Detect cycle participation from SCCs
    # The graph may include sccs in metrics, or we derive from strongly_connected
    sccs = graph.get("strongly_connected_components", [])
    if not sccs:
        # Try metrics
        graph.get("metrics", {})
        # If no SCC data, skip cycle detection
        pass

    for scc in sccs:
        if len(scc) > 1:
            for nid in scc:
                if nid in nodes:
                    nodes[nid]["in_cycle"] = True

    return nodes


def compute_centrality_signals(
    repo_root: Path,
    locations: list[str],
) -> list[CentralitySignal]:
    """Compute architecture centrality for finding locations.

    Returns one signal per unique location path.
    """
    graph_path = repo_root / ".ai-debt" / "architecture-graph.json"
    graph = _load_graph(graph_path)

    if graph is None or not locations:
        return [
            CentralitySignal(
                path=loc,
                level="Low",
                value=FACTOR_SCALE["Low"],
                reason="No architecture graph available"
                if graph is None
                else "No locations to score",
            )
            for loc in (locations or ["<none>"])
        ]

    node_metrics = _compute_node_metrics(graph)

    # Build path → node lookup
    path_to_node: dict[str, dict[str, Any]] = {}
    for _nid, metrics in node_metrics.items():
        npath = metrics["path"]
        path_to_node[npath] = metrics

    signals: list[CentralitySignal] = []
    for loc in locations:
        # Try exact match, then prefix match
        node_data = path_to_node.get(loc)

        if node_data is None:
            # Try matching by file path prefix
            for npath, ndata in path_to_node.items():
                if loc.startswith(npath) or npath.startswith(loc):
                    node_data = ndata
                    break

        if node_data is None:
            signals.append(
                CentralitySignal(
                    path=loc,
                    level="Low",
                    value=FACTOR_SCALE["Low"],
                    reason="Node not found in architecture graph",
                )
            )
            continue

        fan_in = node_data["fan_in"]
        in_cycle = node_data["in_cycle"]

        # Thresholds:
        # Low: fan_in <= 2 AND not in cycle
        # Medium: fan_in 3-5 OR in non-trivial SCC
        # High: fan_in > 5 OR in cycle with hub role
        total_nodes = len(node_metrics)
        top_10_pct = max(1, total_nodes // 10)

        if fan_in > 5 or in_cycle:
            level = "High"
            parts = []
            if fan_in > 5:
                parts.append(f"fan_in={fan_in}")
            if in_cycle:
                parts.append("cycle_participation=true")
            all_fan_ins = sorted(n["fan_in"] for n in node_metrics.values())
            if total_nodes > 5:
                top_idx = max(0, len(all_fan_ins) - top_10_pct)
                if fan_in >= all_fan_ins[top_idx]:
                    parts.append("top_10_percent_hub=true")
            reason = "; ".join(parts)
        elif fan_in >= 3:
            level = "Medium"
            reason = f"fan_in={fan_in}; cycle_participation={in_cycle}"
        else:
            level = "Low"
            reason = f"fan_in={fan_in}; cycle_participation={in_cycle}"

        signals.append(
            CentralitySignal(
                path=loc,
                level=level,
                value=FACTOR_SCALE[level],
                reason=reason,
            )
        )

    return signals


# ── Change frequency ─────────────────────────────────────────────────


def _is_git_repo(root: Path) -> bool:
    """Check if path is inside a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            cwd=str(root),
            timeout=5,
        )
        return result.returncode == 0 and "true" in result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _is_shallow_clone(root: Path) -> bool:
    """Check if the git repository is a shallow clone."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"],
            capture_output=True,
            text=True,
            cwd=str(root),
            timeout=5,
        )
        return result.returncode == 0 and "true" in result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return True  # assume shallow if we can't check


def _count_commits_for_path(
    root: Path,
    path: str,
    max_commits: int = 1000,
    timeout: int = 10,
) -> int:
    """Count commits touching a specific path."""
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                "--format=%H",
                f"--max-count={max_commits}",
                "--follow",
                "--",
                path,
            ],
            capture_output=True,
            text=True,
            cwd=str(root),
            timeout=timeout,
        )
        if result.returncode != 0:
            return 0
        lines = [ln for ln in result.stdout.strip().split("\n") if ln.strip()]
        return len(lines)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0


def compute_change_frequency_signals(
    repo_root: Path,
    locations: list[str],
    max_commits: int = 1000,
    timeout: int = 10,
) -> list[ChangeFrequencySignal]:
    """Compute change frequency for finding locations.

    Returns one signal per unique location path.
    """
    if not _is_git_repo(repo_root) or not locations:
        return [
            ChangeFrequencySignal(
                path=loc,
                commit_count=0,
                level="Low",
                value=FACTOR_SCALE["Low"],
                reason=(
                    "Not a git repository"
                    if not _is_git_repo(repo_root)
                    else "No locations to score"
                ),
            )
            for loc in (locations or ["<none>"])
        ]

    if _is_shallow_clone(repo_root):
        return [
            ChangeFrequencySignal(
                path=loc,
                commit_count=0,
                level="Low",
                value=FACTOR_SCALE["Low"],
                reason="Shallow clone detected, skipping",
            )
            for loc in locations
        ]

    signals: list[ChangeFrequencySignal] = []
    for loc in locations:
        count = _count_commits_for_path(
            repo_root,
            loc,
            max_commits=max_commits,
            timeout=timeout,
        )

        # Thresholds:
        # Low: 0-2 commits
        # Medium: 3-10 commits
        # High: > 10 commits
        if count > 10:
            level = "High"
        elif count >= 3:
            level = "Medium"
        else:
            level = "Low"

        signals.append(
            ChangeFrequencySignal(
                path=loc,
                commit_count=count,
                level=level,
                value=FACTOR_SCALE[level],
                reason=f"commits_touching_path={count}; max_git_commits={max_commits}",
            )
        )

    return signals


# ── Integration: update risk breakdown ────────────────────────────────


def enhance_risk_breakdown(
    repo_root: Path,
    locations: list[str],
    use_centrality: bool = False,
    use_frequency: bool = False,
    max_git_commits: int = 1000,
    git_timeout: int = 10,
) -> dict[str, dict[str, Any]]:
    """Compute enhanced scoring factors for a finding's locations.

    Returns a dict suitable for merging into risk_breakdown:
    {
        "architecture_centrality": {"level": ..., "value": ..., "source": ..., "reason": ...},
        "change_frequency": {"level": ..., "value": ..., "source": ..., "reason": ...},
    }
    """
    result: dict[str, dict[str, Any]] = {}

    if use_centrality:
        cent_signals = compute_centrality_signals(repo_root, locations)
        # Use the highest signal across all locations
        best = max(cent_signals, key=lambda s: s.value)
        result["architecture_centrality"] = {
            "level": best.level,
            "value": best.value,
            "source": best.source,
            "reason": best.reason,
        }
    else:
        result["architecture_centrality"] = {
            "level": "Low",
            "value": FACTOR_SCALE["Low"],
            "source": "default",
            "reason": "Enhanced centrality scoring not enabled",
        }

    if use_frequency:
        freq_signals = compute_change_frequency_signals(
            repo_root,
            locations,
            max_commits=max_git_commits,
            timeout=git_timeout,
        )
        best_freq = max(freq_signals, key=lambda s: s.value)
        result["change_frequency"] = {
            "level": best_freq.level,
            "value": best_freq.value,
            "source": best_freq.source,
            "reason": best_freq.reason,
        }
    else:
        result["change_frequency"] = {
            "level": "Low",
            "value": FACTOR_SCALE["Low"],
            "source": "default",
            "reason": "Enhanced change frequency scoring not enabled",
        }

    return result


def recalculate_risk_score(
    base_template: dict[str, int],
    enhanced_factors: dict[str, dict[str, Any]],
) -> int:
    """Recalculate total risk score with enhanced factors.

    Takes the base RISK_SCORE_TEMPLATE and substitutes enhanced values.
    """
    factors = dict(base_template)
    for key, data in enhanced_factors.items():
        if key in factors:
            factors[key] = data["value"]
    return sum(factors.values())
