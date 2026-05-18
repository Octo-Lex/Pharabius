"""Tests for the architecture analyzer (TD-ARCH finding generation)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pharabius.core.architecture_analyzer import (
    _analyze_cycles,
    _analyze_violations,
    _derive_analysis_units,
    _derive_locations,
    _load_graph,
    _map_severity,
    analyze_architecture_graph,
)
from pharabius.schemas.architecture_graph import (
    ArchitectureCycle,
    ArchitectureEdge,
    ArchitectureGraph,
    ArchitectureNode,
    BoundaryViolation,
)
from pharabius.schemas.finding import DebtRegister, DebtRegisterSummary

# ── Helpers ──────────────────────────────────────────────────────────


def _make_node(
    node_id: str = "ARCH-NODE-PKG-TEST1",
    name: str = "test",
    path: str = "src/test",
    analysis_unit_id: str = "",
    files: list[str] | None = None,
) -> ArchitectureNode:
    return ArchitectureNode(
        node_id=node_id,
        node_type="package",
        name=name,
        path=path,
        analysis_unit_id=analysis_unit_id,
        files=files or [f"{path}/mod.py"],
    )


def _make_edge(
    source: str = "N1",
    target: str = "N2",
    evidence_ids: list[str] | None = None,
    files: list[str] | None = None,
) -> ArchitectureEdge:
    return ArchitectureEdge(
        source_node_id=source,
        target_node_id=target,
        edge_type="internal_import",
        evidence_ids=evidence_ids or ["EVD-001"],
        files=files or ["src/app/main.py"],
    )


def _make_graph(
    *,
    nodes: list[ArchitectureNode] | None = None,
    edges: list[ArchitectureEdge] | None = None,
    cycles: list[ArchitectureCycle] | None = None,
    violations: list[BoundaryViolation] | None = None,
) -> ArchitectureGraph:
    return ArchitectureGraph(
        schema_version="1.0",
        repository="test",
        generated_at="2026-01-01T00:00:00",
        graph_scope="both",
        nodes=nodes or [],
        edges=edges or [],
        cycles=cycles or [],
        boundary_violations=violations or [],
    )


def _setup_repo(
    tmp_path: Path,
    *,
    graph: ArchitectureGraph | None = None,
    with_evidence: bool = True,
    with_register: bool = False,
) -> Path:
    """Create .ai-debt workspace with optional graph and evidence."""
    ai_debt = tmp_path / ".ai-debt"
    ai_debt.mkdir(parents=True, exist_ok=True)

    if with_evidence:
        evidence = {
            "schema_version": "1.0",
            "repository": "test",
            "generated_at": "2026-01-01",
            "evidence": [
                {
                    "evidence_id": "EVD-001",
                    "type": "imports_detected",
                    "category": "code_structure",
                    "location": {"file": "src/app/main.py"},
                    "raw_observation": "utils",
                    "summary": "Import statements detected in src/app/main.py",
                    "metadata": {"imports": ["utils"]},
                },
            ],
        }
        (ai_debt / "evidence.json").write_text(json.dumps(evidence), encoding="utf-8")

    if graph is not None:
        (ai_debt / "architecture-graph.json").write_text(
            graph.model_dump_json(indent=2), encoding="utf-8"
        )

    if with_register:
        register = DebtRegister(
            project_name="test",
            findings=[],
            summary=DebtRegisterSummary(total_findings=0, medium=0),
        )
        (ai_debt / "debt-register.json").write_text(register.model_dump_json(), encoding="utf-8")

    return tmp_path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── Severity mapping ─────────────────────────────────────────────────


class TestSeverityMapping:
    def test_high(self) -> None:
        assert _map_severity("High") == "High"

    def test_medium(self) -> None:
        assert _map_severity("Medium") == "Medium"

    def test_low(self) -> None:
        assert _map_severity("Low") == "Low"

    def test_unknown(self) -> None:
        assert _map_severity("unknown") == "Medium"

    def test_empty(self) -> None:
        assert _map_severity("") == "Medium"


# ── Location derivation ──────────────────────────────────────────────


class TestLocationDerivation:
    def test_from_edge_files(self) -> None:
        n1 = _make_node("N1", files=["src/app/main.py"])
        n2 = _make_node("N2", files=["src/utils/helper.py"])
        edge = _make_edge("N1", "N2", evidence_ids=["EVD-001"], files=["src/app/main.py"])
        graph = _make_graph(nodes=[n1, n2], edges=[edge])

        locs = _derive_locations(graph, ["EVD-001"], ["N1", "N2"])
        assert "src/app/main.py" in locs

    def test_fallback_to_node_paths(self) -> None:
        n1 = _make_node("N1", path="src/app")
        n2 = _make_node("N2", path="src/utils")
        # No overlapping edges
        graph = _make_graph(nodes=[n1, n2], edges=[])

        locs = _derive_locations(graph, ["EVD-999"], ["N1", "N2"])
        assert "src/app" in locs
        assert "src/utils" in locs


# ── Analysis unit derivation ─────────────────────────────────────────


class TestAnalysisUnitDerivation:
    def test_derive_from_nodes(self) -> None:
        n1 = _make_node("N1", analysis_unit_id="AU-PKG-001")
        n2 = _make_node("N2", analysis_unit_id="AU-PKG-002")
        graph = _make_graph(nodes=[n1, n2])

        au_ids = _derive_analysis_units(graph, ["N1", "N2"])
        assert au_ids == ["AU-PKG-001", "AU-PKG-002"]

    def test_empty_when_no_units(self) -> None:
        n1 = _make_node("N1", analysis_unit_id="")
        graph = _make_graph(nodes=[n1])

        au_ids = _derive_analysis_units(graph, ["N1"])
        assert au_ids == []


# ── Graph loading ────────────────────────────────────────────────────


class TestGraphLoading:
    def test_missing_graph(self, tmp_path: Path) -> None:
        result = _load_graph(tmp_path)
        assert result is None

    def test_valid_graph(self, tmp_path: Path) -> None:
        graph = _make_graph()
        graph_path = tmp_path / ".ai-debt" / "architecture-graph.json"
        graph_path.parent.mkdir(parents=True)
        graph_path.write_text(graph.model_dump_json(), encoding="utf-8")
        result = _load_graph(tmp_path)
        assert result is not None

    def test_malformed_graph(self, tmp_path: Path) -> None:
        graph_path = tmp_path / ".ai-debt" / "architecture-graph.json"
        graph_path.parent.mkdir(parents=True)
        graph_path.write_text("NOT JSON{{{{", encoding="utf-8")
        result = _load_graph(tmp_path)
        assert result is None


# ── Cycle analysis ───────────────────────────────────────────────────


class TestCycleAnalysis:
    def test_one_cycle_one_finding(self) -> None:
        cycle = ArchitectureCycle(
            cycle_id="ARCH-CYCLE-TEST",
            node_ids=["N1", "N2"],
            evidence_ids=["EVD-001", "EVD-002"],
            severity_hint="High",
            description="a → b → a (2 nodes, 2 edges)",
        )
        n1 = _make_node("N1", name="module_a")
        n2 = _make_node("N2", name="module_b")
        graph = _make_graph(nodes=[n1, n2], cycles=[cycle])

        specs = _analyze_cycles(graph)
        assert len(specs) == 1
        assert specs[0].category == "TD-ARCH"
        assert "ARCH-CYCLE-TEST" in specs[0].description
        assert specs[0].severity == "High"
        assert specs[0].evidence_ids == ["EVD-001", "EVD-002"]

    def test_cycle_no_evidence_no_finding(self) -> None:
        cycle = ArchitectureCycle(
            cycle_id="ARCH-CYCLE-EMPTY",
            node_ids=["N1", "N2"],
            evidence_ids=[],
        )
        graph = _make_graph(cycles=[cycle])
        specs = _analyze_cycles(graph)
        assert len(specs) == 0

    def test_cycle_severity_medium(self) -> None:
        cycle = ArchitectureCycle(
            cycle_id="ARCH-CYCLE-MED",
            node_ids=["N1", "N2"],
            evidence_ids=["EVD-001"],
            severity_hint="Medium",
        )
        n1 = _make_node("N1")
        n2 = _make_node("N2")
        graph = _make_graph(nodes=[n1, n2], cycles=[cycle])
        specs = _analyze_cycles(graph)
        assert specs[0].severity == "Medium"

    def test_cycle_severity_low(self) -> None:
        cycle = ArchitectureCycle(
            cycle_id="ARCH-CYCLE-LOW",
            node_ids=["N1", "N2"],
            evidence_ids=["EVD-001"],
            severity_hint="Low",
        )
        n1 = _make_node("N1")
        n2 = _make_node("N2")
        graph = _make_graph(nodes=[n1, n2], cycles=[cycle])
        specs = _analyze_cycles(graph)
        assert specs[0].severity == "Low"

    def test_graph_id_in_description(self) -> None:
        cycle = ArchitectureCycle(
            cycle_id="ARCH-CYCLE-ABCD1234",
            node_ids=["N1", "N2"],
            evidence_ids=["EVD-001"],
        )
        n1 = _make_node("N1")
        n2 = _make_node("N2")
        graph = _make_graph(nodes=[n1, n2], cycles=[cycle])
        specs = _analyze_cycles(graph)
        assert "ARCH-CYCLE-ABCD1234" in specs[0].description

    def test_multiple_cycles_deterministic(self) -> None:
        cycles = [
            ArchitectureCycle(
                cycle_id=f"ARCH-CYCLE-{i:03d}",
                node_ids=["N1", "N2"],
                evidence_ids=[f"EVD-{i:03d}"],
                severity_hint="Medium",
            )
            for i in range(3)
        ]
        n1 = _make_node("N1")
        n2 = _make_node("N2")
        graph = _make_graph(nodes=[n1, n2], cycles=cycles)
        specs = _analyze_cycles(graph)
        assert len(specs) == 3

    def test_cycles_over_cap(self) -> None:
        cycles = [
            ArchitectureCycle(
                cycle_id=f"ARCH-CYCLE-{i:03d}",
                node_ids=["N1", "N2"],
                evidence_ids=[f"EVD-{i:03d}"],
                severity_hint="Medium",
            )
            for i in range(25)
        ]
        n1 = _make_node("N1")
        n2 = _make_node("N2")
        graph = _make_graph(nodes=[n1, n2], cycles=cycles)
        specs = _analyze_cycles(graph)
        assert len(specs) == 20
        # Last finding should have cap note
        assert any("25 cycles" in rc for rc in specs[-1].risks_and_cautions)


# ── Violation analysis ───────────────────────────────────────────────


class TestViolationAnalysis:
    def test_one_violation_one_finding(self) -> None:
        violation = BoundaryViolation(
            violation_id="ARCH-VIOL-TEST",
            source_node_id="N1",
            target_node_id="N2",
            policy_name="architecture-policy",
            rule="cli may not import schemas",
            evidence_ids=["EVD-001"],
            severity_hint="High",
            description="cli imports schemas — cli may not import schemas",
        )
        n1 = _make_node("N1", name="cli")
        n2 = _make_node("N2", name="schemas")
        graph = _make_graph(nodes=[n1, n2], violations=[violation])

        specs = _analyze_violations(graph)
        assert len(specs) == 1
        assert specs[0].category == "TD-ARCH"
        assert "ARCH-VIOL-TEST" in specs[0].description
        assert specs[0].severity == "High"

    def test_violation_no_evidence_no_finding(self) -> None:
        violation = BoundaryViolation(
            violation_id="ARCH-VIOL-EMPTY",
            source_node_id="N1",
            target_node_id="N2",
            policy_name="policy",
            rule="rule",
            evidence_ids=[],
        )
        graph = _make_graph(violations=[violation])
        specs = _analyze_violations(graph)
        assert len(specs) == 0

    def test_violation_no_rule_no_finding(self) -> None:
        violation = BoundaryViolation(
            violation_id="ARCH-VIOL-NORULE",
            source_node_id="N1",
            target_node_id="N2",
            policy_name="policy",
            rule="",
            evidence_ids=["EVD-001"],
        )
        graph = _make_graph(violations=[violation])
        specs = _analyze_violations(graph)
        assert len(specs) == 0

    def test_violation_no_policy_name_no_finding(self) -> None:
        violation = BoundaryViolation(
            violation_id="ARCH-VIOL-NOPOL",
            source_node_id="N1",
            target_node_id="N2",
            policy_name="",
            rule="some rule",
            evidence_ids=["EVD-001"],
        )
        graph = _make_graph(violations=[violation])
        specs = _analyze_violations(graph)
        assert len(specs) == 0

    def test_violation_severity_maps(self) -> None:
        for hint, expected in [
            ("High", "High"),
            ("Medium", "Medium"),
            ("Low", "Low"),
            ("", "Medium"),
        ]:
            violation = BoundaryViolation(
                violation_id=f"ARCH-VIOL-{hint}",
                source_node_id="N1",
                target_node_id="N2",
                policy_name="policy",
                rule="rule",
                evidence_ids=["EVD-001"],
                severity_hint=hint,
            )
            n1 = _make_node("N1")
            n2 = _make_node("N2")
            graph = _make_graph(nodes=[n1, n2], violations=[violation])
            specs = _analyze_violations(graph)
            assert specs[0].severity == expected, f"hint={hint!r}"

    def test_violations_over_cap(self) -> None:
        violations = [
            BoundaryViolation(
                violation_id=f"ARCH-VIOL-{i:03d}",
                source_node_id="N1",
                target_node_id="N2",
                policy_name="policy",
                rule=f"rule {i}",
                evidence_ids=[f"EVD-{i:03d}"],
                severity_hint="High",
            )
            for i in range(25)
        ]
        n1 = _make_node("N1")
        n2 = _make_node("N2")
        graph = _make_graph(nodes=[n1, n2], violations=violations)
        specs = _analyze_violations(graph)
        assert len(specs) == 20
        assert any("25 violations" in rc for rc in specs[-1].risks_and_cautions)


# ── High coupling exclusion ──────────────────────────────────────────


class TestHighCouplingExclusion:
    def test_high_coupling_no_finding(self) -> None:
        # Graph with nodes but no cycles or violations = no findings
        n1 = _make_node("N1")
        graph = _make_graph(nodes=[n1])
        cycle_specs = _analyze_cycles(graph)
        viol_specs = _analyze_violations(graph)
        assert len(cycle_specs) == 0
        assert len(viol_specs) == 0


# ── Full integration: analyze_architecture_graph ─────────────────────


class TestAnalyzeArchitectureGraphIntegration:
    def test_no_graph_no_findings(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path, graph=None)
        specs = analyze_architecture_graph(tmp_path)
        assert specs == []

    def test_graph_with_cycle(self, tmp_path: Path) -> None:
        cycle = ArchitectureCycle(
            cycle_id="ARCH-CYCLE-001",
            node_ids=["N1", "N2"],
            evidence_ids=["EVD-001"],
            severity_hint="Medium",
            description="a → b → a",
        )
        n1 = _make_node("N1")
        n2 = _make_node("N2")
        graph = _make_graph(nodes=[n1, n2], cycles=[cycle])
        _setup_repo(tmp_path, graph=graph)
        specs = analyze_architecture_graph(tmp_path)
        assert len(specs) == 1
        assert specs[0].category == "TD-ARCH"

    def test_graph_with_violation(self, tmp_path: Path) -> None:
        violation = BoundaryViolation(
            violation_id="ARCH-VIOL-001",
            source_node_id="N1",
            target_node_id="N2",
            policy_name="architecture-policy",
            rule="cli may not import schemas",
            evidence_ids=["EVD-001"],
            severity_hint="High",
        )
        n1 = _make_node("N1")
        n2 = _make_node("N2")
        graph = _make_graph(nodes=[n1, n2], violations=[violation])
        _setup_repo(tmp_path, graph=graph)
        specs = analyze_architecture_graph(tmp_path)
        assert len(specs) == 1

    def test_malformed_graph_returns_empty(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        graph_path = tmp_path / ".ai-debt" / "architecture-graph.json"
        graph_path.write_text("BROKEN{{{{", encoding="utf-8")
        specs = analyze_architecture_graph(tmp_path)
        assert specs == []


# ── Analyzer integration (via analyze_evidence) ──────────────────────


class TestAnalyzerIntegration:
    def test_analyze_without_graph_unchanged(self, tmp_path: Path) -> None:
        """Analyzer without graph produces same non-TD-ARCH findings as before."""
        from pharabius.core.analyzer import analyze_evidence

        # Setup minimal repo with evidence
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir(parents=True)
        evidence = {
            "schema_version": "1.0",
            "repository": "test",
            "generated_at": "2026-01-01",
            "evidence": [
                {
                    "evidence_id": "EVD-001",
                    "type": "manifest_detected",
                    "category": "dependency",
                    "location": {"file": "pyproject.toml"},
                    "subject": "pyproject.toml",
                    "raw_observation": "Python manifest",
                    "summary": "Python manifest detected",
                    "metadata": {"manifest_type": "python"},
                },
            ],
        }
        (ai_debt / "evidence.json").write_text(json.dumps(evidence), encoding="utf-8")

        # No graph file
        register = analyze_evidence(tmp_path)
        td_arch = [f for f in register.findings if f.category == "TD-ARCH"]
        assert len(td_arch) == 0

    def test_analyze_with_cycle_creates_td_arch(self, tmp_path: Path) -> None:
        """Analyzer with graph cycle creates TD-ARCH finding."""
        from pharabius.core.analyzer import analyze_evidence

        cycle = ArchitectureCycle(
            cycle_id="ARCH-CYCLE-001",
            node_ids=["N1", "N2"],
            evidence_ids=["EVD-001"],
            severity_hint="Medium",
            description="a → b → a (2 nodes, 2 edges)",
        )
        n1 = _make_node("N1", name="module_a")
        n2 = _make_node("N2", name="module_b")
        graph = _make_graph(nodes=[n1, n2], cycles=[cycle])
        _setup_repo(tmp_path, graph=graph, with_evidence=True)

        register = analyze_evidence(tmp_path)
        td_arch = [f for f in register.findings if f.category == "TD-ARCH"]
        assert len(td_arch) == 1
        assert "ARCH-CYCLE-001" in td_arch[0].description

    def test_analyze_with_violation_creates_td_arch(self, tmp_path: Path) -> None:
        """Analyzer with boundary violation creates TD-ARCH finding."""
        from pharabius.core.analyzer import analyze_evidence

        violation = BoundaryViolation(
            violation_id="ARCH-VIOL-001",
            source_node_id="N1",
            target_node_id="N2",
            policy_name="architecture-policy",
            rule="cli may not import schemas",
            evidence_ids=["EVD-001"],
            severity_hint="High",
        )
        n1 = _make_node("N1")
        n2 = _make_node("N2")
        graph = _make_graph(nodes=[n1, n2], violations=[violation])
        _setup_repo(tmp_path, graph=graph, with_evidence=True)

        register = analyze_evidence(tmp_path)
        td_arch = [f for f in register.findings if f.category == "TD-ARCH"]
        assert len(td_arch) == 1
        assert "ARCH-VIOL-001" in td_arch[0].description


# ── Immutability ─────────────────────────────────────────────────────


class TestImmutability:
    def test_graph_file_unchanged_after_analyze(self, tmp_path: Path) -> None:
        from pharabius.core.analyzer import analyze_evidence

        cycle = ArchitectureCycle(
            cycle_id="ARCH-CYCLE-001",
            node_ids=["N1", "N2"],
            evidence_ids=["EVD-001"],
            severity_hint="Medium",
        )
        n1 = _make_node("N1")
        n2 = _make_node("N2")
        graph = _make_graph(nodes=[n1, n2], cycles=[cycle])
        _setup_repo(tmp_path, graph=graph, with_evidence=True)

        graph_path = tmp_path / ".ai-debt" / "architecture-graph.json"
        before = _sha256(graph_path)
        analyze_evidence(tmp_path)
        after = _sha256(graph_path)
        assert before == after

    def test_evidence_unchanged(self, tmp_path: Path) -> None:
        from pharabius.core.analyzer import analyze_evidence

        graph = _make_graph()
        _setup_repo(tmp_path, graph=graph, with_evidence=True)
        ev_path = tmp_path / ".ai-debt" / "evidence.json"
        before = _sha256(ev_path)
        analyze_evidence(tmp_path)
        after = _sha256(ev_path)
        assert before == after
