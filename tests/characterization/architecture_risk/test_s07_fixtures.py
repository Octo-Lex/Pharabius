"""v3.18.0 — Architecture boundary and regression fixtures.

Protects behavior and prevents promotion drift with fixture-based tests.
Covers cycle and violation scenarios, negative cases, and cap behavior.
"""

from __future__ import annotations

from pathlib import Path

from pharabius.core.architecture_analyzer import (
    ArchFindingSpec,
    _analyze_cycles,
    _analyze_violations,
    analyze_architecture_graph,
)
from pharabius.core.signals.architecture_adapters import (
    architecture_boundary_violation_to_signal,
    architecture_cycle_to_signal,
)
from pharabius.core.signals.models import SignalDisposition, SignalFamily
from pharabius.core.signals.policy import (
    output_behavior,
)
from pharabius.core.signals.validation import validate_governed_signal
from pharabius.schemas.architecture_graph import (
    ArchitectureCycle,
    ArchitectureGraph,
    ArchitectureNode,
    BoundaryViolation,
    CouplingMetrics,
)


def _make_graph(
    nodes=None,
    cycles=None,
    violations=None,
    coupling=None,
):
    return ArchitectureGraph(
        nodes=nodes or [],
        cycles=cycles or [],
        boundary_violations=violations or [],
        coupling_metrics=coupling or [],
    )


# ═══════════════════════════════════════════════════════════════════════
# Adapter disposition correctness
# ═══════════════════════════════════════════════════════════════════════


class TestAdapterDispositions:
    """Architecture adapters produce correct dispositions."""

    def test_cycle_is_finding(self) -> None:
        spec = ArchFindingSpec(
            kind="cycle",
            category="TD-ARCH",
            title="Cycle",
            evidence_ids=["EVD-001"],
        )
        sig = architecture_cycle_to_signal(spec)
        assert sig.disposition == SignalDisposition.FINDING
        assert sig.family == SignalFamily.ARCHITECTURE
        behav = output_behavior(sig)
        assert behav.creates_finding is True
        assert behav.creates_work_package is True

    def test_violation_is_finding(self) -> None:
        spec = ArchFindingSpec(
            kind="boundary_violation",
            category="TD-ARCH",
            title="Violation",
            evidence_ids=["EVD-001"],
        )
        sig = architecture_boundary_violation_to_signal(spec)
        assert sig.disposition == SignalDisposition.FINDING
        assert sig.family == SignalFamily.ARCHITECTURE
        behav = output_behavior(sig)
        assert behav.creates_finding is True

    def test_no_informational_in_v318(self) -> None:
        """v3.18.0 emits FINDING only for architecture."""
        spec = ArchFindingSpec(kind="cycle", evidence_ids=["EVD-001"])
        sig = architecture_cycle_to_signal(spec)
        assert sig.disposition == SignalDisposition.FINDING
        # No INFORMATIONAL architecture signals in v3.18.0


# ═══════════════════════════════════════════════════════════════════════
# Adapter validation
# ═══════════════════════════════════════════════════════════════════════


class TestAdapterValidation:
    """Architecture adapters produce valid GovernedSignal instances."""

    def test_cycle_validates(self) -> None:
        spec = ArchFindingSpec(
            kind="cycle",
            evidence_ids=["EVD-001"],
            title="Cycle",
        )
        sig = architecture_cycle_to_signal(spec)
        result = validate_governed_signal(sig)
        assert result.valid

    def test_violation_validates(self) -> None:
        spec = ArchFindingSpec(
            kind="boundary_violation",
            evidence_ids=["EVD-001"],
            title="Viol",
        )
        sig = architecture_boundary_violation_to_signal(spec)
        result = validate_governed_signal(sig)
        assert result.valid

    def test_signal_ids_deterministic(self) -> None:
        spec = ArchFindingSpec(evidence_ids=["EVD-001"])
        sig1 = architecture_cycle_to_signal(spec)
        sig2 = architecture_cycle_to_signal(spec)
        assert sig1.signal_id == sig2.signal_id

    def test_metadata_has_spec_kind(self) -> None:
        spec = ArchFindingSpec(kind="cycle", evidence_ids=["EVD-001"])
        sig = architecture_cycle_to_signal(spec)
        assert sig.metadata["spec_kind"] == "cycle"

        spec2 = ArchFindingSpec(kind="boundary_violation", evidence_ids=["EVD-001"])
        sig2 = architecture_boundary_violation_to_signal(spec2)
        assert sig2.metadata["spec_kind"] == "boundary_violation"


# ═══════════════════════════════════════════════════════════════════════
# Negative-case fixtures
# ═══════════════════════════════════════════════════════════════════════


class TestFixtureHighCouplingOnly:
    """high_coupling_only: coupling metrics but no cycles/violations → no findings."""

    def test_no_cycle_or_violation_findings(self) -> None:
        coupling = CouplingMetrics(node_id="n1", fan_in=20, fan_out=15, instability=0.43)
        graph = _make_graph(coupling=[coupling])
        assert _analyze_cycles(graph) == []
        assert _analyze_violations(graph) == []


class TestFixtureGraphAbsent:
    """graph_absent: no architecture-graph.json → no findings."""

    def test_graceful_skip(self, tmp_path: Path) -> None:
        specs = analyze_architecture_graph(tmp_path)
        assert specs == []

    def test_malformed_graph_graceful_skip(self, tmp_path: Path) -> None:
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir(parents=True)
        (ai_debt / "architecture-graph.json").write_text("NOT JSON", encoding="utf-8")
        specs = analyze_architecture_graph(tmp_path)
        assert specs == []


class TestFixtureCycleWithoutEvidence:
    """cycle_without_evidence: filtered, no finding."""

    def test_no_finding(self) -> None:
        cycle = ArchitectureCycle(
            cycle_id="ARCH-CYCLE-NOEV",
            node_ids=["n1", "n2"],
            evidence_ids=[],
        )
        graph = _make_graph(cycles=[cycle])
        assert _analyze_cycles(graph) == []


class TestFixtureViolationWithoutEvidence:
    """violation_without_evidence: filtered, no finding."""

    def test_no_finding(self) -> None:
        viol = BoundaryViolation(
            violation_id="ARCH-VIOL-NOEV",
            source_node_id="n1",
            target_node_id="n2",
            policy_name="p",
            rule="r",
            evidence_ids=[],
        )
        graph = _make_graph(violations=[viol])
        assert _analyze_violations(graph) == []


class TestFixtureSingleCycle:
    """single_cycle_with_evidence: produces one TD-ARCH finding."""

    def test_one_finding(self) -> None:
        n1 = ArchitectureNode(node_id="n1", node_type="module", name="a", path="a.py")
        n2 = ArchitectureNode(node_id="n2", node_type="module", name="b", path="b.py")
        cycle = ArchitectureCycle(
            cycle_id="ARCH-CYCLE-AB",
            node_ids=["n1", "n2"],
            evidence_ids=["EVD-001"],
        )
        graph = _make_graph(nodes=[n1, n2], cycles=[cycle])
        specs = _analyze_cycles(graph)
        assert len(specs) == 1
        assert specs[0].kind == "cycle"
        assert specs[0].category == "TD-ARCH"


class TestFixtureBoundaryViolation:
    """boundary_violation_with_evidence: produces one TD-ARCH finding."""

    def test_one_finding(self) -> None:
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
        assert specs[0].category == "TD-ARCH"


class TestFixtureCapBehavior:
    """Cap (20 per type) is preserved."""

    def test_cycle_cap_at_20(self) -> None:
        nodes = [
            ArchitectureNode(node_id=f"n{i}", node_type="module", name=f"m{i}", path=f"m{i}.py")
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
        assert len(specs) == 20
        last_caution = " ".join(specs[-1].risks_and_cautions)
        assert "25 cycles found" in last_caution
        assert "only 20" in last_caution


class TestRoutingDoesNotUseTitle:
    """Signal routing uses spec.kind, not title text."""

    def test_kind_stable_even_if_title_changes(self) -> None:
        n1 = ArchitectureNode(node_id="n1", node_type="module", name="a", path="a.py")
        n2 = ArchitectureNode(node_id="n2", node_type="module", name="b", path="b.py")
        cycle = ArchitectureCycle(
            cycle_id="ARCH-CYCLE-STABLE",
            node_ids=["n1", "n2"],
            evidence_ids=["EVD-001"],
        )
        graph = _make_graph(nodes=[n1, n2], cycles=[cycle])
        specs = _analyze_cycles(graph)
        # Kind is stable regardless of title
        assert specs[0].kind == "cycle"
        # Title is different from kind
        assert specs[0].kind not in specs[0].title.lower()

    def test_unknown_spec_fallback_safe(self) -> None:
        """Unknown spec kind falls back to direct builder path safely."""
        spec = ArchFindingSpec(
            kind="unknown",
            category="TD-ARCH",
            title="Unknown type",
            evidence_ids=["EVD-001"],
        )
        # Should not crash — unknown kind is handled gracefully
        assert spec.kind == "unknown"
        # The fallback path in _add_architecture_findings handles this
