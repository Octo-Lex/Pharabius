"""Pydantic models for the architecture dependency graph IR.

Defines the output contract for ``ai-debt graph`` — nodes, edges,
cycles, boundary violations, coupling metrics, and optional policy schema.

All list/dict fields use ``Field(default_factory=...)`` to ensure
independent defaults across instances.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── Stable ID helpers ────────────────────────────────────────────────


def stable_node_id(node_type: str, name: str, path: str) -> str:
    """Deterministic node ID: ARCH-NODE-{TYPE}-{HASH8}."""
    import hashlib

    raw = f"{node_type}:{name}:{path}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8].upper()
    prefix = node_type.upper()
    return f"ARCH-NODE-{prefix}-{h}"


def stable_cycle_id(sorted_node_ids: list[str]) -> str:
    """Deterministic cycle ID: ARCH-CYCLE-{HASH8}."""
    import hashlib

    raw = "cycle:" + ",".join(sorted(sorted_node_ids))
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8].upper()
    return f"ARCH-CYCLE-{h}"


def stable_violation_id(
    source_node_id: str,
    target_node_id: str,
    policy_name: str,
    rule: str,
) -> str:
    """Deterministic violation ID: ARCH-VIOL-{HASH8}."""
    import hashlib

    raw = f"viol:{source_node_id}:{target_node_id}:{policy_name}:{rule}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8].upper()
    return f"ARCH-VIOL-{h}"


# ── Graph models ─────────────────────────────────────────────────────


class ArchitectureNode(BaseModel):
    """A single node in the architecture dependency graph."""

    node_id: str
    node_type: str  # package, module, analysis_unit
    name: str
    path: str = ""
    analysis_unit_id: str = ""
    files: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class ArchitectureEdge(BaseModel):
    """A directed edge representing an internal import dependency."""

    source_node_id: str
    target_node_id: str
    edge_type: str = "internal_import"
    import_count: int = 1
    evidence_ids: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class ArchitectureCycle(BaseModel):
    """A detected dependency cycle (SCC with >= 2 nodes)."""

    cycle_id: str
    node_ids: list[str] = Field(default_factory=list)
    edge_count: int = 0
    evidence_ids: list[str] = Field(default_factory=list)
    severity_hint: str = "Low"
    description: str = ""


class BoundaryViolation(BaseModel):
    """A layer boundary violation detected from policy."""

    violation_id: str
    source_node_id: str
    target_node_id: str
    policy_name: str = ""
    rule: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    severity_hint: str = "Low"
    description: str = ""


class CouplingMetrics(BaseModel):
    """Coupling metrics for a single graph node."""

    node_id: str
    fan_in: int = 0
    fan_out: int = 0
    instability: float = 0.0
    evidence_count: int = 0


class ArchitectureGraph(BaseModel):
    """Complete architecture dependency graph IR."""

    schema_version: str = "1.0"
    repository: str = ""
    generated_at: str = ""
    graph_scope: str = "both"
    nodes: list[ArchitectureNode] = Field(default_factory=list)
    edges: list[ArchitectureEdge] = Field(default_factory=list)
    cycles: list[ArchitectureCycle] = Field(default_factory=list)
    boundary_violations: list[BoundaryViolation] = Field(default_factory=list)
    coupling_metrics: list[CouplingMetrics] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


# ── Policy models ────────────────────────────────────────────────────


class PolicyLayer(BaseModel):
    """A single layer in an architecture boundary policy."""

    name: str
    paths: list[str] = Field(default_factory=list)
    may_import: list[str] = Field(default_factory=list)


class ArchitecturePolicy(BaseModel):
    """Architecture boundary policy loaded from YAML."""

    schema_version: str = "1.0"
    layers: list[PolicyLayer] = Field(default_factory=list)
