"""S01 — Architecture signal inventory and characterization tests.

These tests lock down the CURRENT behavior of architecture-risk analysis
before migration to governed signals.

Boundary: architecture_analyzer.py produces ArchFindingSpec[] with kind field.
analyzer.py converts specs into DebtFinding via FindingBuilder.
"""

from __future__ import annotations

from pathlib import Path

from pharabius.core.architecture_analyzer import (
    ArchFindingSpec,
    _analyze_cycles,
    _analyze_violations,
    analyze_architecture_graph,
)
from pharabius.schemas.architecture_graph import (
    ArchitectureCycle,
    ArchitectureGraph,
    ArchitectureNode,
    BoundaryViolation,
    CouplingMetrics,
)


def _write_file(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _make_graph(
    nodes: list[ArchitectureNode] | None = None,
    cycles: list[ArchitectureCycle] | None = None,
    violations: list[BoundaryViolation] | None = None,
    coupling: list[CouplingMetrics] | None = None,
) -> ArchitectureGraph:
    return ArchitectureGraph(
        nodes=nodes or [],
        cycles=cycles or [],
        boundary_violations=violations or [],
        coupling_metrics=coupling or [],
    )


def _write_graph(tmp_path: Path, graph: ArchitectureGraph) -> Path:
    ai_debt = tmp_path / ".ai-debt"
    ai_debt.mkdir(parents=True, exist_ok=True)
    path = ai_debt / "architecture-graph.json"
    path.write_text(graph.model_dump_json(indent=2), encoding="utf-8")
    return path


# ═══════════════════════════════════════════════════════════════════════
# S01 Inventory: ArchFindingSpec kind field
# ═══════════════════════════════════════════════════════════════════════


class TestSpecKindField:
    """ArchFindingSpec has a stable kind field for governance routing."""

    def test_cycle_spec_has_kind_cycle(self) -> None:
        n1 = ArchitectureNode(node_id="n1", node_type="module", name="a", path="a.py")
        n2 = ArchitectureNode(node_id="n2", node_type="module", name="b", path="b.py")
        cycle = ArchitectureCycle(
            cycle_id="ARCH-CYCLE-TEST",
            node_ids=["n1", "n2"],
            evidence_ids=["EVD-001"],
        )
        graph = _make_graph(nodes=[n1, n2], cycles=[cycle])
        specs = _analyze_cycles(graph)
        assert len(specs) == 1
        assert specs[0].kind == "cycle"

    def test_violation_spec_has_kind_boundary_violation(self) -> None:
        n1 = ArchitectureNode(node_id="n1", node_type="module", name="app", path="app/")
        n2 = ArchitectureNode(node_id="n2", node_type="module", name="infra", path="infra/")
        viol = BoundaryViolation(
            violation_id="ARCH-VIOL-TEST",
            source_node_id="n1",
            target_node_id="n2",
            policy_name="layered",
            rule="app may not import infra",
            evidence_ids=["EVD-001"],
        )
        graph = _make_graph(nodes=[n1, n2], violations=[viol])
        specs = _analyze_violations(graph)
        assert len(specs) == 1
        assert specs[0].kind == "boundary_violation"

    def test_default_kind_is_empty(self) -> None:
        spec = ArchFindingSpec()
        assert spec.kind == ""

    def test_routing_does_not_use_title(self) -> None:
        """Signal routing must use spec.kind, not title text."""
        n1 = ArchitectureNode(node_id="n1", node_type="module", name="a", path="a.py")
        n2 = ArchitectureNode(node_id="n2", node_type="module", name="b", path="b.py")
        cycle = ArchitectureCycle(
            cycle_id="ARCH-CYCLE-TEST",
            node_ids=["n1", "n2"],
            evidence_ids=["EVD-001"],
        )
        graph = _make_graph(nodes=[n1, n2], cycles=[cycle])
        specs = _analyze_cycles(graph)
        assert specs[0].kind == "cycle"
        # Even if title changes, kind stays stable
        assert specs[0].kind != specs[0].title


# ═══════════════════════════════════════════════════════════════════════
# S01 Inventory: What does NOT create findings
# ═══════════════════════════════════════════════════════════════════════


class TestNegativeCases:
    """Architecture signals that must NOT produce findings."""

    def test_high_coupling_only_no_finding(self) -> None:
        coupling = CouplingMetrics(node_id="n1", fan_in=20, fan_out=15, instability=0.43)
        graph = _make_graph(coupling=[coupling])
        (
            analyze_architecture_graph.__wrapped__(graph)
            if hasattr(analyze_architecture_graph, "__wrapped__")
            else []
        )
        # Direct analysis: cycles + violations should be empty
        cycle_specs = _analyze_cycles(graph)
        viol_specs = _analyze_violations(graph)
        assert len(cycle_specs) == 0
        assert len(viol_specs) == 0

    def test_cycle_without_evidence_no_finding(self) -> None:
        cycle = ArchitectureCycle(
            cycle_id="ARCH-CYCLE-NOEV",
            node_ids=["n1", "n2"],
            evidence_ids=[],  # No evidence
        )
        graph = _make_graph(cycles=[cycle])
        specs = _analyze_cycles(graph)
        assert len(specs) == 0

    def test_violation_without_evidence_no_finding(self) -> None:
        viol = BoundaryViolation(
            violation_id="ARCH-VIOL-NOEV",
            source_node_id="n1",
            target_node_id="n2",
            policy_name="layered",
            rule="some rule",
            evidence_ids=[],  # No evidence
        )
        graph = _make_graph(violations=[viol])
        specs = _analyze_violations(graph)
        assert len(specs) == 0

    def test_violation_without_rule_no_finding(self) -> None:
        viol = BoundaryViolation(
            violation_id="ARCH-VIOL-NORULE",
            source_node_id="n1",
            target_node_id="n2",
            policy_name="layered",
            rule="",  # No rule
            evidence_ids=["EVD-001"],
        )
        graph = _make_graph(violations=[viol])
        specs = _analyze_violations(graph)
        assert len(specs) == 0

    def test_violation_without_policy_no_finding(self) -> None:
        viol = BoundaryViolation(
            violation_id="ARCH-VIOL-NOPOL",
            source_node_id="n1",
            target_node_id="n2",
            policy_name="",  # No policy
            rule="some rule",
            evidence_ids=["EVD-001"],
        )
        graph = _make_graph(violations=[viol])
        specs = _analyze_violations(graph)
        assert len(specs) == 0

    def test_graph_absent_no_findings(self, tmp_path: Path) -> None:
        specs = analyze_architecture_graph(tmp_path)
        assert specs == []


# ═══════════════════════════════════════════════════════════════════════
# S01 Inventory: Cycle finding output lock-down
# ═══════════════════════════════════════════════════════════════════════


class TestCycleOutputLockdown:
    """Lock down exact cycle finding output."""

    def test_cycle_category_is_td_arch(self) -> None:
        n1 = ArchitectureNode(node_id="n1", node_type="module", name="alpha", path="a.py")
        n2 = ArchitectureNode(node_id="n2", node_type="module", name="beta", path="b.py")
        cycle = ArchitectureCycle(
            cycle_id="ARCH-CYCLE-AB",
            node_ids=["n1", "n2"],
            evidence_ids=["EVD-001"],
        )
        graph = _make_graph(nodes=[n1, n2], cycles=[cycle])
        specs = _analyze_cycles(graph)
        assert len(specs) == 1
        assert specs[0].category == "TD-ARCH"

    def test_cycle_confidence_high_with_evidence(self) -> None:
        n1 = ArchitectureNode(node_id="n1", node_type="module", name="a", path="a.py")
        n2 = ArchitectureNode(node_id="n2", node_type="module", name="b", path="b.py")
        cycle = ArchitectureCycle(
            cycle_id="ARCH-CYCLE-CONF",
            node_ids=["n1", "n2"],
            evidence_ids=["EVD-001"],
        )
        graph = _make_graph(nodes=[n1, n2], cycles=[cycle])
        specs = _analyze_cycles(graph)
        assert specs[0].confidence == "High"

    def test_cycle_title_exact(self) -> None:
        n1 = ArchitectureNode(node_id="n1", node_type="module", name="a", path="a.py")
        n2 = ArchitectureNode(node_id="n2", node_type="module", name="b", path="b.py")
        cycle = ArchitectureCycle(
            cycle_id="ARCH-CYCLE-TITLE",
            node_ids=["n1", "n2"],
            evidence_ids=["EVD-001"],
        )
        graph = _make_graph(nodes=[n1, n2], cycles=[cycle])
        specs = _analyze_cycles(graph)
        assert specs[0].title == "Confirmed circular dependency detected between architecture nodes"


# ═══════════════════════════════════════════════════════════════════════
# S01 Inventory: Cap behavior lock-down
# ═══════════════════════════════════════════════════════════════════════


class TestCapBehavior:
    """Cap (20 per type) must be preserved."""

    def test_cap_note_on_last_finding(self) -> None:
        nodes = [
            ArchitectureNode(node_id=f"n{i}", node_type="module", name=f"mod{i}", path=f"mod{i}.py")
            for i in range(25)
        ]
        cycles = [
            ArchitectureCycle(
                cycle_id=f"ARCH-CYCLE-{i}",
                node_ids=[f"n{i}", f"n{(i + 1) % 25}"],
                evidence_ids=[f"EVD-{i}"],
            )
            for i in range(25)
        ]
        graph = _make_graph(nodes=nodes, cycles=cycles)
        specs = _analyze_cycles(graph)
        # Should cap at 20
        assert len(specs) == 20
        # Last finding should have cap note in risks_and_cautions
        last_caution = " ".join(specs[-1].risks_and_cautions)
        assert "25 cycles found" in last_caution
        assert "only 20" in last_caution
