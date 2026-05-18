"""Tests for architecture graph schema models and ID stability."""

from __future__ import annotations

import json

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

# ── Node tests ───────────────────────────────────────────────────────


class TestArchitectureNode:
    def test_default_fields_independent(self) -> None:
        n1 = ArchitectureNode(node_id="a", node_type="package", name="foo")
        n2 = ArchitectureNode(node_id="b", node_type="module", name="bar")
        n1.files.append("x.py")
        assert n2.files == []

    def test_metadata_default_independent(self) -> None:
        n1 = ArchitectureNode(node_id="a", node_type="package", name="foo")
        n2 = ArchitectureNode(node_id="b", node_type="module", name="bar")
        n1.metadata["key"] = "val"
        assert n2.metadata == {}

    def test_serialization_roundtrip(self) -> None:
        node = ArchitectureNode(
            node_id="ARCH-NODE-PKG-ABC12345",
            node_type="package",
            name="my_pkg",
            path="src/my_pkg",
            files=["a.py", "b.py"],
        )
        data = json.loads(node.model_dump_json())
        restored = ArchitectureNode.model_validate(data)
        assert restored.node_id == node.node_id
        assert restored.files == node.files


# ── Edge tests ───────────────────────────────────────────────────────


class TestArchitectureEdge:
    def test_default_type(self) -> None:
        edge = ArchitectureEdge(source_node_id="a", target_node_id="b")
        assert edge.edge_type == "internal_import"

    def test_default_fields_independent(self) -> None:
        e1 = ArchitectureEdge(source_node_id="a", target_node_id="b")
        e2 = ArchitectureEdge(source_node_id="c", target_node_id="d")
        e1.evidence_ids.append("EVD-001")
        assert e2.evidence_ids == []


# ── Cycle tests ──────────────────────────────────────────────────────


class TestArchitectureCycle:
    def test_default_severity(self) -> None:
        c = ArchitectureCycle(cycle_id="ARCH-CYCLE-ABC12345")
        assert c.severity_hint == "Low"

    def test_fields_independent(self) -> None:
        c1 = ArchitectureCycle(cycle_id="a")
        c2 = ArchitectureCycle(cycle_id="b")
        c1.node_ids.append("x")
        assert c2.node_ids == []


# ── Violation tests ──────────────────────────────────────────────────


class TestBoundaryViolation:
    def test_defaults(self) -> None:
        v = BoundaryViolation(
            violation_id="ARCH-VIOL-ABC12345",
            source_node_id="a",
            target_node_id="b",
        )
        assert v.severity_hint == "Low"
        assert v.policy_name == ""

    def test_fields_independent(self) -> None:
        v1 = BoundaryViolation(violation_id="a", source_node_id="a", target_node_id="b")
        v2 = BoundaryViolation(violation_id="b", source_node_id="c", target_node_id="d")
        v1.evidence_ids.append("EVD-001")
        assert v2.evidence_ids == []


# ── Coupling metrics tests ───────────────────────────────────────────


class TestCouplingMetrics:
    def test_defaults(self) -> None:
        m = CouplingMetrics(node_id="a")
        assert m.fan_in == 0
        assert m.fan_out == 0
        assert m.instability == 0.0

    def test_instability_formula(self) -> None:
        m = CouplingMetrics(node_id="a", fan_in=3, fan_out=2, instability=0.4)
        assert m.instability == 0.4


# ── Graph round-trip tests ───────────────────────────────────────────


class TestArchitectureGraphRoundTrip:
    def test_empty_graph(self) -> None:
        g = ArchitectureGraph(repository="test", generated_at="2026-01-01")
        data = json.loads(g.model_dump_json())
        restored = ArchitectureGraph.model_validate(data)
        assert restored.repository == "test"
        assert restored.nodes == []
        assert restored.edges == []
        assert restored.limitations == []

    def test_full_graph(self) -> None:
        g = ArchitectureGraph(
            repository="test",
            generated_at="2026-01-01",
            nodes=[ArchitectureNode(node_id="N1", node_type="package", name="pkg", files=["a.py"])],
            edges=[
                ArchitectureEdge(
                    source_node_id="N1",
                    target_node_id="N2",
                    evidence_ids=["EVD-001"],
                )
            ],
            cycles=[
                ArchitectureCycle(cycle_id="C1", node_ids=["N1", "N2"], severity_hint="Medium")
            ],
            boundary_violations=[
                BoundaryViolation(
                    violation_id="V1",
                    source_node_id="N1",
                    target_node_id="N2",
                    policy_name="policy",
                    rule="layer violation",
                    severity_hint="High",
                )
            ],
            coupling_metrics=[CouplingMetrics(node_id="N1", fan_in=1, fan_out=1, instability=0.5)],
            limitations=["test limitation"],
        )
        data = json.loads(g.model_dump_json())
        restored = ArchitectureGraph.model_validate(data)
        assert len(restored.nodes) == 1
        assert len(restored.edges) == 1
        assert len(restored.cycles) == 1
        assert len(restored.boundary_violations) == 1
        assert len(restored.coupling_metrics) == 1
        assert restored.limitations == ["test limitation"]


# ── Policy tests ─────────────────────────────────────────────────────


class TestPolicyLayer:
    def test_defaults(self) -> None:
        layer = PolicyLayer(name="core")
        assert layer.paths == []
        assert layer.may_import == []

    def test_fields_independent(self) -> None:
        l1 = PolicyLayer(name="a")
        l2 = PolicyLayer(name="b")
        l1.paths.append("src/a/**")
        assert l2.paths == []


class TestArchitecturePolicy:
    def test_empty_policy(self) -> None:
        p = ArchitecturePolicy()
        assert p.schema_version == "1.0"
        assert p.layers == []

    def test_with_layers(self) -> None:
        p = ArchitecturePolicy(
            layers=[
                PolicyLayer(
                    name="cli",
                    paths=["src/cli.py"],
                    may_import=["core", "schemas"],
                ),
                PolicyLayer(
                    name="core",
                    paths=["src/core/**"],
                    may_import=["schemas"],
                ),
                PolicyLayer(
                    name="schemas",
                    paths=["src/schemas/**"],
                    may_import=[],
                ),
            ]
        )
        assert len(p.layers) == 3
        assert p.layers[0].may_import == ["core", "schemas"]
        assert p.layers[2].may_import == []


# ── Stable ID tests ──────────────────────────────────────────────────


class TestStableIds:
    def test_node_id_deterministic(self) -> None:
        id1 = stable_node_id("package", "pharabius.core", "src/pharabius/core")
        id2 = stable_node_id("package", "pharabius.core", "src/pharabius/core")
        assert id1 == id2
        assert id1.startswith("ARCH-NODE-PACKAGE-")

    def test_node_id_different_inputs(self) -> None:
        id1 = stable_node_id("package", "foo", "src/foo")
        id2 = stable_node_id("module", "foo", "src/foo")
        assert id1 != id2

    def test_cycle_id_deterministic(self) -> None:
        id1 = stable_cycle_id(["N2", "N1"])
        id2 = stable_cycle_id(["N1", "N2"])
        assert id1 == id2  # Sort order doesn't matter
        assert id1.startswith("ARCH-CYCLE-")

    def test_violation_id_deterministic(self) -> None:
        id1 = stable_violation_id("N1", "N2", "policy", "rule")
        id2 = stable_violation_id("N1", "N2", "policy", "rule")
        assert id1 == id2
        assert id1.startswith("ARCH-VIOL-")

    def test_violation_id_different(self) -> None:
        id1 = stable_violation_id("N1", "N2", "policy", "rule1")
        id2 = stable_violation_id("N1", "N2", "policy", "rule2")
        assert id1 != id2
