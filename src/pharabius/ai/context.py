"""Bounded context assembly for AI enrichment.

Reads existing .ai-debt/ artifacts and assembles a focused context
for each finding, respecting budget constraints.
Never reads source files — only artifact data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pharabius.schemas.ai_enrichment import (
    AIBudget,
    AIBudgetSummary,
    AIContextSummary,
    AIOmittedItems,
)


def _load_json(path: Path) -> dict[str, Any]:
    """Load JSON file, returning empty dict on any failure."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _truncate_snippet(text: str, max_chars: int = 300) -> str:
    """Truncate text to max_chars with ellipsis."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def load_artifacts(ai_debt_dir: Path) -> dict[str, Any]:
    """Load all available .ai-debt/ artifacts.

    Returns dict with keys: evidence, register, units, graph, verification.
    Missing artifacts are returned as empty dicts.
    """
    return {
        "evidence": _load_json(ai_debt_dir / "evidence.json"),
        "register": _load_json(ai_debt_dir / "debt-register.json"),
        "units": _load_json(ai_debt_dir / "analysis-units.json"),
        "graph": _load_json(ai_debt_dir / "architecture-graph.json"),
        "verification": _load_json(ai_debt_dir / "verification-report.json"),
    }


def get_evidence_map(artifacts: dict[str, Any]) -> dict[str, str]:
    """Build evidence_id -> raw_observation lookup."""
    evidence_data = artifacts.get("evidence", {})
    items = evidence_data.get("evidence", [])
    result: dict[str, str] = {}
    for item in items:
        eid = item.get("evidence_id", "")
        obs = item.get("raw_observation", "")
        if eid:
            result[eid] = obs
    return result


def get_finding_by_id(register: dict[str, Any], finding_id: str) -> dict[str, Any] | None:
    """Find a finding by ID in the register."""
    for f in register.get("findings", []):
        if isinstance(f, dict) and f.get("id") == finding_id:
            return f
    return None


def get_findings(
    register: dict[str, Any],
    max_findings: int = 10,
    finding_id: str | None = None,
) -> list[dict[str, Any]]:
    """Get findings to enrich, optionally filtered by ID."""
    all_findings: list[dict[str, Any]] = register.get("findings", []) or []
    if finding_id:
        return [f for f in all_findings if isinstance(f, dict) and f.get("id") == finding_id]
    return all_findings[:max_findings]


def get_all_finding_ids(register: dict[str, Any]) -> set[str]:
    """Get all finding IDs in the register."""
    return {f.get("id", "") for f in register.get("findings", [])}


def get_all_evidence_ids(artifacts: dict[str, Any]) -> set[str]:
    """Get all evidence IDs in the evidence store."""
    evidence_data = artifacts.get("evidence", {})
    return {
        item.get("evidence_id", "")
        for item in evidence_data.get("evidence", [])
        if item.get("evidence_id")
    }


def get_all_unit_ids(artifacts: dict[str, Any]) -> set[str]:
    """Get all analysis unit IDs."""
    units_data = artifacts.get("units", {})
    return {unit.get("unit_id", "") for unit in units_data.get("units", []) if unit.get("unit_id")}


def get_all_graph_ids(artifacts: dict[str, Any]) -> set[str]:
    """Get all architecture graph node/edge IDs."""
    graph_data = artifacts.get("graph", {})
    ids: set[str] = set()
    for node in graph_data.get("nodes", []):
        if node.get("node_id"):
            ids.add(node["node_id"])
    for edge in graph_data.get("edges", []):
        if edge.get("edge_id"):
            ids.add(edge["edge_id"])
    return ids


def get_linked_evidence(
    artifacts: dict[str, Any],
    evidence_ids: list[str],
    budget: AIBudget,
) -> tuple[list[dict[str, Any]], int]:
    """Get evidence items linked to a finding, respecting budget.

    Returns (included_items, omitted_count).
    """
    evidence_data = artifacts.get("evidence", {})
    all_items = evidence_data.get("evidence", [])

    # Build lookup
    item_map: dict[str, dict[str, Any]] = {}
    for item in all_items:
        eid = item.get("evidence_id", "")
        if eid:
            item_map[eid] = item

    included: list[dict[str, Any]] = []
    total_chars = 0

    # Priority: directly linked IDs first
    for eid in evidence_ids:
        if len(included) >= budget.max_evidence_items:
            break
        item = item_map.get(eid)
        if not item:
            continue
        snippet = _truncate_snippet(json.dumps(item, default=str), 500)
        if total_chars + len(snippet) > budget.max_context_chars:
            break
        included.append(item)
        total_chars += len(snippet)

    omitted = max(0, len(evidence_ids) - len(included))
    return included, omitted


def get_linked_units(
    artifacts: dict[str, Any],
    unit_ids: list[str],
    budget: AIBudget,
) -> tuple[list[dict[str, Any]], int]:
    """Get analysis units linked to a finding."""
    units_data = artifacts.get("units", {})
    all_units = units_data.get("units", [])

    item_map: dict[str, dict[str, Any]] = {}
    for unit in all_units:
        uid = unit.get("unit_id", "")
        if uid:
            item_map[uid] = unit

    included: list[dict[str, Any]] = []
    for uid in unit_ids:
        if len(included) >= budget.max_analysis_units:
            break
        item = item_map.get(uid)
        if item:
            included.append(item)

    omitted = max(0, len(unit_ids) - len(included))
    return included, omitted


def get_verification_status(artifacts: dict[str, Any], finding_id: str) -> str | None:
    """Get verification status for a finding."""
    ver_data = artifacts.get("verification", {})
    for entry in ver_data.get("verifications", []):
        if isinstance(entry, dict) and entry.get("finding_id") == finding_id:
            status = entry.get("status")
            return str(status) if status is not None else None
    return None


def build_context_for_finding(
    finding: dict[str, Any],
    artifacts: dict[str, Any],
    budget: AIBudget,
) -> dict[str, Any]:
    """Build bounded context for a single finding.

    Returns context dict with:
    - finding summary
    - evidence items
    - analysis units
    - graph records
    - verification status
    - budget usage
    """
    finding_id = finding.get("id", "")
    evidence_ids = finding.get("evidence_ids", [])
    unit_ids = finding.get("analysis_unit_ids", [])

    evidence_items, evidence_omitted = get_linked_evidence(artifacts, evidence_ids, budget)
    units, units_omitted = get_linked_units(artifacts, unit_ids, budget)
    ver_status = get_verification_status(artifacts, finding_id)

    # Graph records: find cycles/violations mentioning this finding
    graph_data = artifacts.get("graph", {})
    graph_records: list[dict[str, Any]] = []
    for cycle in graph_data.get("cycles", []):
        if finding_id in str(cycle):
            graph_records.append(cycle)
        if len(graph_records) >= budget.max_graph_edges:
            break
    for violation in graph_data.get("violations", []):
        if finding_id in str(violation):
            graph_records.append(violation)
        if len(graph_records) >= budget.max_graph_edges:
            break

    evidence_map = get_evidence_map(artifacts)

    return {
        "finding": finding,
        "evidence_items": evidence_items,
        "evidence_map": evidence_map,
        "analysis_units": units,
        "graph_records": graph_records,
        "verification_status": ver_status,
        "context_summary": AIContextSummary(
            evidence_items_included=len(evidence_items),
            evidence_items_omitted=evidence_omitted,
            analysis_units_included=len(units),
            analysis_units_omitted=units_omitted,
            graph_records_included=len(graph_records),
            total_context_chars=0,
            budget_limit_chars=budget.max_context_chars,
            omitted_items=AIOmittedItems(
                evidence_items=evidence_omitted,
                analysis_units=units_omitted,
            ),
            budget_summary=AIBudgetSummary(
                max_context_chars=budget.max_context_chars,
                max_evidence_items=budget.max_evidence_items,
                max_graph_records=budget.max_graph_edges,
                max_analysis_units=budget.max_analysis_units,
                used_evidence_items=len(evidence_items),
                used_graph_records=len(graph_records),
                used_analysis_units=len(units),
            ),
        ),
    }


def build_enrichment_context(
    artifacts: dict[str, Any],
    max_findings: int = 10,
    finding_id: str | None = None,
    budget: AIBudget | None = None,
) -> dict[str, Any]:
    """Build full enrichment context for all selected findings.

    Returns dict with:
    - findings: list of finding dicts to enrich
    - evidence_map: evidence_id -> raw_observation
    - per_finding_contexts: list of per-finding context dicts
    """
    if budget is None:
        budget = AIBudget()

    register = artifacts.get("register", {})
    findings = get_findings(register, max_findings, finding_id)
    evidence_map = get_evidence_map(artifacts)

    per_finding_contexts = []
    for finding in findings:
        ctx = build_context_for_finding(finding, artifacts, budget)
        per_finding_contexts.append(ctx)

    return {
        "findings": findings,
        "evidence_map": evidence_map,
        "per_finding_contexts": per_finding_contexts,
    }
