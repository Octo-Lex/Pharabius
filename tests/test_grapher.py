"""Tests for the graph builder (core/grapher.py)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pharabius.core.grapher import (
    _build_edges,
    _build_package_nodes,
    _check_boundary_violations,
    _compute_coupling_metrics,
    _detect_cycles,
    _extract_imports_from_evidence,
    _is_external_import,
    _is_python_stdlib,
    build_graph,
)
from pharabius.schemas.architecture_graph import (
    ArchitectureEdge,
    ArchitectureNode,
    ArchitecturePolicy,
    PolicyLayer,
    stable_node_id,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _setup_repo(
    tmp_path: Path,
    *,
    evidence_items: list[dict] | None = None,
    with_units: bool = False,
    with_profile: bool = False,
    with_policy: bool = False,
    with_importlinter: bool = False,
) -> Path:
    """Create a minimal .ai-debt workspace for graph testing."""
    ai_debt = tmp_path / ".ai-debt"
    ai_debt.mkdir(parents=True, exist_ok=True)

    if evidence_items is None:
        evidence_items = [
            {
                "evidence_id": "EVD-001",
                "type": "imports_detected",
                "category": "code_structure",
                "location": {"file": "src/myapp/core.py"},
                "subject": "src/myapp/core.py",
                "raw_observation": "os, json, myapp.utils",
                "metadata": {"imports": ["os", "json", "myapp.utils"]},
            },
        ]

    evidence_data = {
        "schema_version": "1.0",
        "repository": "test",
        "generated_at": "2026-01-01",
        "evidence": evidence_items,
    }
    (ai_debt / "evidence.json").write_text(json.dumps(evidence_data), encoding="utf-8")

    if with_units:
        units_data = {
            "schema_version": "1.0",
            "units": [
                {
                    "analysis_unit_id": "AU-PKG-TEST",
                    "unit_type": "package",
                    "name": "core",
                    "root_path": "src/myapp",
                    "files": ["src/myapp/core.py"],
                }
            ],
        }
        (ai_debt / "analysis-units.json").write_text(json.dumps(units_data), encoding="utf-8")

    if with_profile:
        profile_data = {
            "schema_version": "1.0",
            "project_name": "test-project",
            "detected_languages": ["Python"],
            "package_managers": ["python"],
        }
        (ai_debt / "project-profile.json").write_text(json.dumps(profile_data), encoding="utf-8")

    if with_policy:
        policy_yaml = """schema_version: "1.0"
layers:
  - name: core
    paths:
      - src/myapp/**
    may_import:
      - utils
  - name: utils
    paths:
      - src/utils/**
    may_import: []
"""
        (ai_debt / "architecture-policy.yaml").write_text(policy_yaml, encoding="utf-8")

    if with_importlinter:
        (tmp_path / ".importlinter").write_text(
            "[importlinter]\nroot_package = myapp\n", encoding="utf-8"
        )

    return tmp_path


def _make_node(
    node_type: str = "package",
    name: str = "test",
    path: str = "src/test",
    node_id: str | None = None,
) -> ArchitectureNode:
    if node_id is None:
        node_id = stable_node_id(node_type, name, path)
    return ArchitectureNode(
        node_id=node_id,
        node_type=node_type,
        name=name,
        path=path,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── Import extraction ────────────────────────────────────────────────


class TestExtractImportsFromEvidence:
    def test_metadata_imports(self) -> None:
        item = {"metadata": {"imports": ["os", "json", "myapp.core"]}}
        result = _extract_imports_from_evidence(item)
        assert result == ["os", "json", "myapp.core"]

    def test_raw_observation_fallback(self) -> None:
        item = {"raw_observation": "os, json, myapp.core", "metadata": {}}
        result = _extract_imports_from_evidence(item)
        assert result == ["os", "json", "myapp.core"]

    def test_no_metadata_no_raw(self) -> None:
        item = {}
        result = _extract_imports_from_evidence(item)
        assert result == []

    def test_empty_metadata_imports(self) -> None:
        item = {"metadata": {"imports": []}, "raw_observation": "os, sys"}
        result = _extract_imports_from_evidence(item)
        assert result == ["os", "sys"]

    def test_whitespace_stripped(self) -> None:
        item = {"raw_observation": "  os ,  json , sys  "}
        result = _extract_imports_from_evidence(item)
        assert result == ["os", "json", "sys"]


# ── Stdlib / external detection ──────────────────────────────────────


class TestStdlibDetection:
    def test_python_stdlib(self) -> None:
        assert _is_python_stdlib("os") is True
        assert _is_python_stdlib("json") is True
        assert _is_python_stdlib("collections") is True
        assert _is_python_stdlib("pathlib") is True
        assert _is_python_stdlib("myapp.core") is False

    def test_python_stdlib_submodule(self) -> None:
        assert _is_python_stdlib("os.path") is True
        assert _is_python_stdlib("collections.abc") is True


class TestExternalImport:
    def test_internal_prefix(self) -> None:
        assert _is_external_import("myapp.core", {"myapp"}) is False

    def test_external(self) -> None:
        assert _is_external_import("requests", {"myapp"}) is True

    def test_stdlib_is_external(self) -> None:
        assert _is_external_import("os", {"myapp"}) is True


# ── Node construction ────────────────────────────────────────────────


class TestPackageNodeDerivation:
    def test_python_src_layout(self) -> None:
        evidence = [
            {
                "evidence_id": "EVD-001",
                "type": "imports_detected",
                "category": "code_structure",
                "location": {"file": "src/myapp/core.py"},
                "raw_observation": "myapp.utils",
                "metadata": {"imports": ["myapp.utils"]},
            },
        ]
        nodes = _build_package_nodes(evidence, None)
        assert len(nodes) >= 1
        # Should have a node for 'myapp'
        found = any(n.name == "myapp" for n in nodes.values())
        assert found

    def test_python_test_dir(self) -> None:
        evidence = [
            {
                "evidence_id": "EVD-001",
                "type": "imports_detected",
                "category": "code_structure",
                "location": {"file": "tests/test_core.py"},
                "raw_observation": "myapp.core",
                "metadata": {"imports": ["myapp.core"]},
            },
        ]
        nodes = _build_package_nodes(evidence, None)
        assert len(nodes) >= 1

    def test_files_collected(self) -> None:
        evidence = [
            {
                "evidence_id": "EVD-001",
                "type": "imports_detected",
                "category": "code_structure",
                "location": {"file": "src/myapp/core.py"},
                "raw_observation": "json",
                "metadata": {"imports": ["json"]},
            },
            {
                "evidence_id": "EVD-002",
                "type": "imports_detected",
                "category": "code_structure",
                "location": {"file": "src/myapp/utils.py"},
                "raw_observation": "os",
                "metadata": {"imports": ["os"]},
            },
        ]
        nodes = _build_package_nodes(evidence, None)
        # Both files should be under the same 'myapp' node
        for node in nodes.values():
            if node.name == "myapp":
                assert len(node.files) == 2


# ── Edge construction ────────────────────────────────────────────────


class TestEdgeConstruction:
    def test_internal_import_creates_edge(self) -> None:
        nodes = {
            "package:app:src/app": _make_node("package", "app", "src/app"),
            "package:utils:src/utils": _make_node("package", "utils", "src/utils"),
        }
        nodes["package:app:src/app"].files = ["src/app/main.py"]
        nodes["package:utils:src/utils"].files = ["src/utils/helper.py"]

        evidence = [
            {
                "evidence_id": "EVD-001",
                "type": "imports_detected",
                "category": "code_structure",
                "location": {"file": "src/app/main.py"},
                "raw_observation": "utils.helper",
                "metadata": {"imports": ["utils.helper"]},
            },
        ]
        limitations: list[str] = []
        edges = _build_edges(evidence, nodes, {"app", "utils"}, limitations)

        # Check that an edge was created from app to utils
        assert len(edges) == 1
        assert edges[0].edge_type == "internal_import"

    def test_stdlib_skipped(self) -> None:
        nodes = {
            "package:app:src/app": _make_node("package", "app", "src/app"),
        }
        nodes["package:app:src/app"].files = ["src/app/main.py"]

        evidence = [
            {
                "evidence_id": "EVD-001",
                "type": "imports_detected",
                "category": "code_structure",
                "location": {"file": "src/app/main.py"},
                "raw_observation": "os, json, sys",
                "metadata": {"imports": ["os", "json", "sys"]},
            },
        ]
        limitations: list[str] = []
        edges = _build_edges(evidence, nodes, {"app"}, limitations)
        assert len(edges) == 0

    def test_external_skipped(self) -> None:
        nodes = {
            "package:app:src/app": _make_node("package", "app", "src/app"),
        }
        nodes["package:app:src/app"].files = ["src/app/main.py"]

        evidence = [
            {
                "evidence_id": "EVD-001",
                "type": "imports_detected",
                "category": "code_structure",
                "location": {"file": "src/app/main.py"},
                "raw_observation": "requests, flask",
                "metadata": {"imports": ["requests", "flask"]},
            },
        ]
        limitations: list[str] = []
        edges = _build_edges(evidence, nodes, {"app"}, limitations)
        assert len(edges) == 0

    def test_unresolved_internal_becomes_limitation(self) -> None:
        nodes = {
            "package:myapp:src/myapp": _make_node("package", "myapp", "src/myapp"),
        }
        nodes["package:myapp:src/myapp"].files = ["src/myapp/main.py"]

        evidence = [
            {
                "evidence_id": "EVD-001",
                "type": "imports_detected",
                "category": "code_structure",
                "location": {"file": "src/myapp/main.py"},
                "raw_observation": "myapp.deep.nested.module",
                "metadata": {"imports": ["myapp.deep.nested.module"]},
            },
        ]
        # "myapp" is internal prefix but no node for myapp.deep.nested.module
        limitations: list[str] = []
        _build_edges(evidence, nodes, {"myapp"}, limitations)
        # Resolves to myapp node (top-level match) so it IS an edge
        # Let's use a truly unresolved scenario instead
        #
        # Actually, myapp.deep.nested.module resolves to myapp node (prefix match).
        # For unresolved we need a case where prefix matches but no node matches.
        # Since there's only one node 'myapp', any myapp.* import resolves to it.
        # Let's test with a different internal prefix that has no nodes.
        nodes2 = {
            "package:myapp:src/myapp": _make_node("package", "myapp", "src/myapp"),
        }
        nodes2["package:myapp:src/myapp"].files = ["src/myapp/main.py"]
        evidence2 = [
            {
                "evidence_id": "EVD-001",
                "type": "imports_detected",
                "category": "code_structure",
                "location": {"file": "src/myapp/main.py"},
                "raw_observation": "mylib.utils",
                "metadata": {"imports": ["mylib.utils"]},
            },
        ]
        limitations2: list[str] = []
        edges2 = _build_edges(evidence2, nodes2, {"myapp", "mylib"}, limitations2)
        assert len(edges2) == 0
        assert any("Unresolved" in lim for lim in limitations2)

    def test_duplicate_edges_aggregate(self) -> None:
        nodes = {
            "package:app:src/app": _make_node("package", "app", "src/app"),
            "package:utils:src/utils": _make_node("package", "utils", "src/utils"),
        }
        nodes["package:app:src/app"].files = ["src/app/main.py", "src/app/cli.py"]
        nodes["package:utils:src/utils"].files = ["src/utils/helper.py"]

        evidence = [
            {
                "evidence_id": "EVD-001",
                "type": "imports_detected",
                "category": "code_structure",
                "location": {"file": "src/app/main.py"},
                "raw_observation": "utils",
                "metadata": {"imports": ["utils"]},
            },
            {
                "evidence_id": "EVD-002",
                "type": "imports_detected",
                "category": "code_structure",
                "location": {"file": "src/app/cli.py"},
                "raw_observation": "utils",
                "metadata": {"imports": ["utils"]},
            },
        ]
        limitations: list[str] = []
        edges = _build_edges(evidence, nodes, {"app", "utils"}, limitations)
        # Should aggregate to one edge
        assert len(edges) == 1
        assert edges[0].import_count == 2
        assert len(edges[0].evidence_ids) == 2
        assert len(edges[0].files) == 2


# ── Cycle detection ──────────────────────────────────────────────────


class TestCycleDetection:
    def test_two_node_cycle(self) -> None:
        n1 = _make_node(name="a", path="a")
        n2 = _make_node(name="b", path="b")
        edges = [
            ArchitectureEdge(source_node_id=n1.node_id, target_node_id=n2.node_id),
            ArchitectureEdge(source_node_id=n2.node_id, target_node_id=n1.node_id),
        ]
        cycles = _detect_cycles([n1, n2], edges)
        assert len(cycles) == 1
        assert len(cycles[0].node_ids) == 2

    def test_three_node_cycle(self) -> None:
        n1 = _make_node(name="a", path="a")
        n2 = _make_node(name="b", path="b")
        n3 = _make_node(name="c", path="c")
        edges = [
            ArchitectureEdge(source_node_id=n1.node_id, target_node_id=n2.node_id),
            ArchitectureEdge(source_node_id=n2.node_id, target_node_id=n3.node_id),
            ArchitectureEdge(source_node_id=n3.node_id, target_node_id=n1.node_id),
        ]
        cycles = _detect_cycles([n1, n2, n3], edges)
        assert len(cycles) == 1
        assert len(cycles[0].node_ids) == 3

    def test_acyclic_no_cycles(self) -> None:
        n1 = _make_node(name="a", path="a")
        n2 = _make_node(name="b", path="b")
        edges = [
            ArchitectureEdge(source_node_id=n1.node_id, target_node_id=n2.node_id),
        ]
        cycles = _detect_cycles([n1, n2], edges)
        assert len(cycles) == 0

    def test_self_loop_ignored(self) -> None:
        n1 = _make_node(name="a", path="a")
        edges = [
            ArchitectureEdge(source_node_id=n1.node_id, target_node_id=n1.node_id),
        ]
        cycles = _detect_cycles([n1], edges)
        assert len(cycles) == 0

    def test_cycle_id_deterministic(self) -> None:
        n1 = _make_node(name="a", path="a")
        n2 = _make_node(name="b", path="b")
        edges = [
            ArchitectureEdge(source_node_id=n1.node_id, target_node_id=n2.node_id),
            ArchitectureEdge(source_node_id=n2.node_id, target_node_id=n1.node_id),
        ]
        c1 = _detect_cycles([n1, n2], edges)
        c2 = _detect_cycles([n2, n1], edges)
        assert c1[0].cycle_id == c2[0].cycle_id


# ── Coupling metrics ─────────────────────────────────────────────────


class TestCouplingMetrics:
    def test_fan_in_fan_out(self) -> None:
        n1 = _make_node(name="a", path="a")
        n2 = _make_node(name="b", path="b")
        n3 = _make_node(name="c", path="c")
        edges = [
            ArchitectureEdge(
                source_node_id=n1.node_id, target_node_id=n2.node_id, evidence_ids=["E1"]
            ),
            ArchitectureEdge(
                source_node_id=n3.node_id, target_node_id=n2.node_id, evidence_ids=["E2"]
            ),
            ArchitectureEdge(
                source_node_id=n2.node_id, target_node_id=n3.node_id, evidence_ids=["E3"]
            ),
        ]
        metrics = _compute_coupling_metrics([n1, n2, n3], edges)
        m_map = {m.node_id: m for m in metrics}

        # n1: fan_out=1, fan_in=0
        assert m_map[n1.node_id].fan_in == 0
        assert m_map[n1.node_id].fan_out == 1

        # n2: fan_in=2, fan_out=1
        assert m_map[n2.node_id].fan_in == 2
        assert m_map[n2.node_id].fan_out == 1
        assert m_map[n2.node_id].instability == pytest.approx(1 / 3, abs=0.01)

    def test_zero_degree_node(self) -> None:
        n1 = _make_node(name="a", path="a")
        metrics = _compute_coupling_metrics([n1], [])
        assert metrics[0].fan_in == 0
        assert metrics[0].fan_out == 0
        assert metrics[0].instability == 0.0


# ── Boundary violations ─────────────────────────────────────────────


class TestBoundaryViolations:
    def test_violation_detected(self) -> None:
        n1 = _make_node(name="cli", path="src/cli")
        n2 = _make_node(name="schemas", path="src/schemas")
        n1.files = ["src/cli/main.py"]
        n2.files = ["src/schemas/models.py"]
        edges = [
            ArchitectureEdge(
                source_node_id=n1.node_id,
                target_node_id=n2.node_id,
                evidence_ids=["EVD-001"],
            ),
        ]
        policy = ArchitecturePolicy(
            layers=[
                PolicyLayer(
                    name="cli",
                    paths=["src/cli/**"],
                    may_import=["core"],
                ),
                PolicyLayer(
                    name="schemas",
                    paths=["src/schemas/**"],
                    may_import=[],
                ),
            ]
        )
        violations = _check_boundary_violations(edges, [n1, n2], policy)
        assert len(violations) == 1
        assert violations[0].severity_hint == "High"

    def test_allowed_import_no_violation(self) -> None:
        n1 = _make_node(name="cli", path="src/cli")
        n2 = _make_node(name="core", path="src/core")
        n1.files = ["src/cli/main.py"]
        n2.files = ["src/core/engine.py"]
        edges = [
            ArchitectureEdge(
                source_node_id=n1.node_id,
                target_node_id=n2.node_id,
            ),
        ]
        policy = ArchitecturePolicy(
            layers=[
                PolicyLayer(
                    name="cli",
                    paths=["src/cli/**"],
                    may_import=["core"],
                ),
                PolicyLayer(
                    name="core",
                    paths=["src/core/**"],
                    may_import=[],
                ),
            ]
        )
        violations = _check_boundary_violations(edges, [n1, n2], policy)
        assert len(violations) == 0

    def test_source_not_in_policy(self) -> None:
        n1 = _make_node(name="external", path="ext")
        n2 = _make_node(name="core", path="src/core")
        n1.files = ["ext/main.py"]
        n2.files = ["src/core/engine.py"]
        edges = [
            ArchitectureEdge(
                source_node_id=n1.node_id,
                target_node_id=n2.node_id,
            ),
        ]
        policy = ArchitecturePolicy(
            layers=[
                PolicyLayer(
                    name="core",
                    paths=["src/core/**"],
                    may_import=[],
                ),
            ]
        )
        violations = _check_boundary_violations(edges, [n1, n2], policy)
        assert len(violations) == 0

    def test_same_layer_allowed(self) -> None:
        n1 = _make_node(name="a", path="src/core")
        n2 = _make_node(name="b", path="src/core")
        n1.files = ["src/core/a.py"]
        n2.files = ["src/core/b.py"]
        edges = [
            ArchitectureEdge(
                source_node_id=n1.node_id,
                target_node_id=n2.node_id,
            ),
        ]
        policy = ArchitecturePolicy(
            layers=[
                PolicyLayer(
                    name="core",
                    paths=["src/core/**"],
                    may_import=["schemas"],
                ),
            ]
        )
        violations = _check_boundary_violations(edges, [n1, n2], policy)
        assert len(violations) == 0


# ── Build graph integration ──────────────────────────────────────────


class TestBuildGraphFailureModes:
    def test_missing_evidence(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match=r"evidence\.json not found"):
            build_graph(tmp_path)

    def test_malformed_evidence(self, tmp_path: Path) -> None:
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir(parents=True)
        (ai_debt / "evidence.json").write_text("NOT JSON{{{{", encoding="utf-8")
        with pytest.raises(ValueError, match=r"Could not read evidence.json"):
            build_graph(tmp_path)

    def test_scope_analysis_unit_missing(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        with pytest.raises(
            FileNotFoundError,
            match=r"analysis-units\.json not found",
        ):
            build_graph(tmp_path, scope="analysis_unit")


class TestBuildGraphGracefulDegradation:
    def test_missing_units_scope_both(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        result = build_graph(tmp_path, scope="both")
        assert any("analysis-units.json not found" in lim for lim in result.graph.limitations)

    def test_missing_profile(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        result = build_graph(tmp_path)
        assert any("project-profile.json not found" in lim for lim in result.graph.limitations)

    def test_missing_policy(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        result = build_graph(tmp_path)
        assert any("No architecture policy found" in lim for lim in result.graph.limitations)

    def test_importlinter_limitation(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path, with_importlinter=True)
        result = build_graph(tmp_path)
        assert any(".importlinter" in lim for lim in result.graph.limitations)


class TestBuildGraphZeroImports:
    def test_zero_import_repo(self, tmp_path: Path) -> None:
        evidence_items = [
            {
                "evidence_id": "EVD-001",
                "type": "file_detected",
                "category": "code_structure",
                "location": {"file": "README.md"},
            },
        ]
        _setup_repo(tmp_path, evidence_items=evidence_items)
        result = build_graph(tmp_path)
        assert len(result.graph.nodes) == 0
        assert len(result.graph.edges) == 0
        assert any("No imports_detected evidence" in lim for lim in result.graph.limitations)


# ── Immutability tests ───────────────────────────────────────────────


class TestImmutability:
    def test_evidence_json_unchanged(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        ev_path = tmp_path / ".ai-debt" / "evidence.json"
        before = _sha256(ev_path)
        build_graph(tmp_path)
        after = _sha256(ev_path)
        assert before == after

    def test_analysis_units_unchanged(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path, with_units=True)
        units_path = tmp_path / ".ai-debt" / "analysis-units.json"
        before = _sha256(units_path)
        build_graph(tmp_path)
        after = _sha256(units_path)
        assert before == after

    def test_debt_register_unchanged(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        # Create a dummy debt-register.json
        register_path = tmp_path / ".ai-debt" / "debt-register.json"
        register_path.write_text('{"findings": []}', encoding="utf-8")
        before = _sha256(register_path)
        build_graph(tmp_path)
        after = _sha256(register_path)
        assert before == after

    def test_project_profile_unchanged(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path, with_profile=True)
        profile_path = tmp_path / ".ai-debt" / "project-profile.json"
        before = _sha256(profile_path)
        build_graph(tmp_path)
        after = _sha256(profile_path)
        assert before == after
