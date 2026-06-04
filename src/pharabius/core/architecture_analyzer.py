"""Analyze architecture graph IR and produce TD-ARCH finding specifications.

Reads ``.ai-debt/architecture-graph.json`` if present and returns structured
finding specs for cycles and boundary violations. The caller (analyzer.py)
owns ``FindingBuilder`` and converts specs into ``DebtFinding`` entries.

This module does **not** import from ``analyzer.py`` — no circular imports.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from pharabius.schemas.architecture_graph import (
    ArchitectureGraph,
    ArchitectureNode,
)

logger = logging.getLogger(__name__)

_MAX_FINDINGS_PER_TYPE = 20

# Risk breakdown template for TD-ARCH findings
_CYCLE_RISK_BREAKDOWN: dict[str, int] = {
    "technical_severity": 5,
    "architecture_centrality": 4,
    "blast_radius": 4,
    "change_frequency": 1,
    "test_gap": 2,
    "security_exposure": 0,
    "compliance_exposure": 0,
    "dependency_risk": 2,
    "operational_exposure": 1,
    "business_critical_proxy": 2,
    "remediation_simplicity": -2,
    "confidence_modifier": 0,
}

_VIOLATION_RISK_BREAKDOWN: dict[str, int] = {
    "technical_severity": 4,
    "architecture_centrality": 3,
    "blast_radius": 3,
    "change_frequency": 1,
    "test_gap": 1,
    "security_exposure": 0,
    "compliance_exposure": 0,
    "dependency_risk": 1,
    "operational_exposure": 1,
    "business_critical_proxy": 2,
    "remediation_simplicity": -2,
    "confidence_modifier": 0,
}


@dataclass
class ArchFindingSpec:
    """Specification for a single TD-ARCH finding.

    The caller converts this into a DebtFinding via FindingBuilder.
    """

    category: str = "TD-ARCH"
    title: str = ""
    description: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    analysis_unit_ids: list[str] = field(default_factory=list)
    kind: str = ""  # "cycle" or "boundary_violation" — used for governance routing
    severity: str = "Medium"
    confidence: str = "High"
    technical_impact: str = ""
    business_impact: str = ""
    risk_breakdown: dict[str, int] = field(default_factory=dict)
    remediation_effort: str = "Medium"
    recommended_action: str = ""
    verification_recommendations: list[str] = field(default_factory=list)
    risks_and_cautions: list[str] = field(default_factory=list)
    suggested_owner_area: str = "Architecture / Engineering"
    cap_note: str = ""


def _load_graph(repository_root: Path) -> ArchitectureGraph | None:
    """Load architecture-graph.json. Returns None if absent or malformed."""
    path = repository_root.resolve() / ".ai-debt" / "architecture-graph.json"
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return ArchitectureGraph.model_validate(data)
    except Exception as exc:
        logger.warning("Could not read architecture-graph.json: %s", exc)
        return None


def _map_severity(severity_hint: str) -> str:
    """Map graph severity_hint to finding severity.

    Rules:
    - High -> High
    - Medium -> Medium
    - Low -> Low
    - unknown/empty -> Medium
    """
    mapping = {
        "High": "High",
        "Medium": "Medium",
        "Low": "Low",
    }
    return mapping.get(severity_hint, "Medium")


def _build_node_map(
    nodes: list[ArchitectureNode],
) -> dict[str, ArchitectureNode]:
    """Build node_id -> ArchitectureNode lookup."""
    return {n.node_id: n for n in nodes}


def _derive_locations(
    graph: ArchitectureGraph,
    evidence_ids: list[str],
    node_ids: list[str],
) -> list[str]:
    """Derive locations from graph edges and nodes."""
    locations: list[str] = []
    ev_set = set(evidence_ids)

    # Priority 1: edge files with overlapping evidence
    for edge in graph.edges:
        if ev_set & set(edge.evidence_ids):
            for f in edge.files:
                if f and f not in locations:
                    locations.append(f)

    # Priority 2: node paths (fallback)
    if not locations:
        node_map = _build_node_map(graph.nodes)
        for nid in node_ids:
            node = node_map.get(nid)
            if node and node.path and node.path not in locations:
                locations.append(node.path)

    return locations


def _derive_analysis_units(
    graph: ArchitectureGraph,
    node_ids: list[str],
) -> list[str]:
    """Derive analysis_unit_ids from graph nodes."""
    unit_ids: list[str] = []
    node_map = _build_node_map(graph.nodes)
    for nid in node_ids:
        node = node_map.get(nid)
        if node and node.analysis_unit_id and node.analysis_unit_id not in unit_ids:
            unit_ids.append(node.analysis_unit_id)
    return unit_ids


def _analyze_cycles(graph: ArchitectureGraph) -> list[ArchFindingSpec]:
    """Generate TD-ARCH finding specs for circular dependencies."""
    specs: list[ArchFindingSpec] = []

    eligible = [c for c in graph.cycles if len(c.node_ids) >= 2 and c.evidence_ids]

    capped = len(eligible) > _MAX_FINDINGS_PER_TYPE
    to_process = eligible[:_MAX_FINDINGS_PER_TYPE]

    for cycle in to_process:
        node_map = _build_node_map(graph.nodes)
        node_names = [
            node_map.get(
                nid,
                ArchitectureNode(
                    node_id=nid,
                    node_type="unknown",
                    name=nid,
                ),
            ).name
            for nid in cycle.node_ids
        ]

        locations = _derive_locations(graph, cycle.evidence_ids, cycle.node_ids)
        au_ids = _derive_analysis_units(graph, cycle.node_ids)

        # Adjust risk breakdown based on severity
        breakdown = dict(_CYCLE_RISK_BREAKDOWN)
        if cycle.severity_hint == "High":
            breakdown["architecture_centrality"] = 5
            breakdown["blast_radius"] = 5
        elif cycle.severity_hint == "Low":
            breakdown["architecture_centrality"] = 2
            breakdown["blast_radius"] = 2

        desc = (
            f"Confirmed circular dependency detected between architecture nodes "
            f"(cycle: {cycle.cycle_id}). "
        )
        if cycle.description:
            desc += cycle.description
        else:
            desc += " → ".join([*node_names, node_names[0]]) if node_names else "cycle"

        cap_note = ""
        if capped:
            cap_note = (
                f"Architecture graph contains {len(eligible)} cycles; "
                f"only first {_MAX_FINDINGS_PER_TYPE} converted to findings."
            )

        specs.append(
            ArchFindingSpec(
                category="TD-ARCH",
                title="Confirmed circular dependency detected between architecture nodes",
                description=desc,
                evidence_ids=list(cycle.evidence_ids),
                locations=locations,
                analysis_unit_ids=au_ids,
                kind="cycle",
                severity=_map_severity(cycle.severity_hint),
                confidence="High" if cycle.evidence_ids else "Medium",
                technical_impact=(
                    "Circular dependencies increase coupling, make modules harder to test "
                    "in isolation, and complicate dependency injection and refactoring."
                ),
                business_impact=(
                    "Circular dependencies slow feature development and increase the risk "
                    "of regression when changes propagate through coupled modules."
                ),
                risk_breakdown=breakdown,
                remediation_effort="Medium",
                recommended_action=(
                    "Break the cycle by introducing an interface or abstraction, moving "
                    "shared code to a lower-level module, or inverting dependencies. "
                    "Review with the owning engineering team."
                ),
                verification_recommendations=[
                    "Run ai-debt graph after refactoring and confirm the cycle is absent.",
                    "Verify that module tests pass independently after cycle removal.",
                ],
                risks_and_cautions=[
                    "Do not break cycles by moving code without understanding the "
                    "ownership boundary.",
                    "Ensure interface extraction does not introduce abstraction leaks.",
                ],
                suggested_owner_area="Architecture / Engineering",
                cap_note=cap_note,
            )
        )

    # Add cap note to last finding if capped
    if capped and specs:
        last = specs[-1]
        last.risks_and_cautions.append(
            f"Note: {len(eligible)} cycles found; only "
            f"{_MAX_FINDINGS_PER_TYPE} converted to findings. "
            f"Run ai-debt graph to see all cycles."
        )

    return specs


def _analyze_violations(graph: ArchitectureGraph) -> list[ArchFindingSpec]:
    """Generate TD-ARCH finding specs for boundary policy violations."""
    specs: list[ArchFindingSpec] = []

    eligible = [v for v in graph.boundary_violations if v.evidence_ids and v.rule and v.policy_name]

    capped = len(eligible) > _MAX_FINDINGS_PER_TYPE
    to_process = eligible[:_MAX_FINDINGS_PER_TYPE]

    node_map = _build_node_map(graph.nodes)

    for violation in to_process:
        locations = _derive_locations(
            graph,
            violation.evidence_ids,
            [violation.source_node_id, violation.target_node_id],
        )
        au_ids = _derive_analysis_units(
            graph,
            [violation.source_node_id, violation.target_node_id],
        )

        source_node = node_map.get(violation.source_node_id)
        target_node = node_map.get(violation.target_node_id)
        source_name = source_node.name if source_node else violation.source_node_id
        target_name = target_node.name if target_node else violation.target_node_id

        # Adjust risk breakdown
        breakdown = dict(_VIOLATION_RISK_BREAKDOWN)
        if violation.severity_hint == "High":
            breakdown["architecture_centrality"] = 4
            breakdown["blast_radius"] = 4
        elif violation.severity_hint == "Low":
            breakdown["architecture_centrality"] = 1
            breakdown["blast_radius"] = 1

        desc = (
            f"Architecture boundary policy violation detected "
            f"(violation: {violation.violation_id}). "
        )
        if violation.description:
            desc += violation.description
        else:
            desc += f"{source_name} imports {target_name} — {violation.rule}"

        specs.append(
            ArchFindingSpec(
                category="TD-ARCH",
                title="Architecture boundary policy violation detected",
                description=desc,
                evidence_ids=list(violation.evidence_ids),
                locations=locations,
                analysis_unit_ids=au_ids,
                kind="boundary_violation",
                severity=_map_severity(violation.severity_hint),
                confidence="High" if violation.evidence_ids else "Medium",
                technical_impact=(
                    "Layer boundary violations erode the intended architecture separation, "
                    "making the codebase harder to understand and maintain."
                ),
                business_impact=(
                    "Architecture violations increase the cost of feature development and "
                    "make it harder for new team members to understand the system."
                ),
                risk_breakdown=breakdown,
                remediation_effort="Medium",
                recommended_action=(
                    "Align import direction with the architecture policy, move shared "
                    "abstractions to an allowed layer, or update the policy if the "
                    "violation reflects intentional architecture."
                ),
                verification_recommendations=[
                    "Run ai-debt graph after refactoring and confirm the violation is absent.",
                    "Review architecture-policy.yaml to ensure it reflects the intended layering.",
                ],
                risks_and_cautions=[
                    "Do not update the policy solely to suppress violations without team review.",
                    "Ensure layer moves do not break downstream consumers.",
                ],
                suggested_owner_area="Architecture / Engineering",
                cap_note="",
            )
        )

    # Add cap note to last finding if capped
    if capped and specs:
        last = specs[-1]
        last.risks_and_cautions.append(
            f"Note: {len(eligible)} violations found; only "
            f"{_MAX_FINDINGS_PER_TYPE} converted to findings. "
            f"Run ai-debt graph to see all violations."
        )

    return specs


def analyze_architecture_graph(
    repository_root: Path,
) -> list[ArchFindingSpec]:
    """Analyze architecture graph and return TD-ARCH finding specs.

    Returns empty list if graph file is absent or malformed.
    Does not raise on missing/invalid graph.
    """
    graph = _load_graph(repository_root)
    if graph is None:
        return []

    specs: list[ArchFindingSpec] = []
    specs.extend(_analyze_cycles(graph))
    specs.extend(_analyze_violations(graph))

    return specs
