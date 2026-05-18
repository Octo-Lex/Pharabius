"""Tests for Rust graph resolution enhancements."""

import json
from pathlib import Path

from pharabius.core.grapher import (
    _derive_rust_node_path,
    _discover_rust_crates,
    _normalize_rust_crate_name,
    build_graph,
)


class TestNormalizeRustCrateName:
    def test_kebab_to_snake(self):
        assert _normalize_rust_crate_name("symbiot-core") == "symbiot_core"

    def test_already_snake(self):
        assert _normalize_rust_crate_name("engine_core") == "engine_core"

    def test_multiple_hyphens(self):
        assert _normalize_rust_crate_name("my-cool-crate") == "my_cool_crate"

    def test_no_hyphens(self):
        assert _normalize_rust_crate_name("cli") == "cli"


class TestDeriveRustNodePath:
    def _make_crates(self) -> dict:
        return {
            "rust:symbiot-cli:crates/symbiot-cli": {
                "name": "symbiot-cli",
                "path": "crates/symbiot-cli",
            },
            "rust:symbiot-core:crates/symbiot-core": {
                "name": "symbiot-core",
                "path": "crates/symbiot-core",
            },
        }

    def test_file_in_crate(self):
        crates = self._make_crates()
        result = _derive_rust_node_path("crates/symbiot-cli/src/main.rs", crates)
        assert result == ("symbiot-cli", "crates/symbiot-cli")

    def test_file_in_core_crate(self):
        crates = self._make_crates()
        result = _derive_rust_node_path("crates/symbiot-core/src/lib.rs", crates)
        assert result == ("symbiot-core", "crates/symbiot-core")

    def test_file_in_tests(self):
        crates = self._make_crates()
        result = _derive_rust_node_path("crates/symbiot-cli/tests/integration.rs", crates)
        assert result == ("symbiot-cli", "crates/symbiot-cli")

    def test_file_in_examples(self):
        crates = self._make_crates()
        result = _derive_rust_node_path("crates/symbiot-cli/examples/demo.rs", crates)
        assert result == ("symbiot-cli", "crates/symbiot-cli")

    def test_file_not_in_any_crate(self):
        crates = self._make_crates()
        result = _derive_rust_node_path("src/main.rs", crates)
        assert result is None

    def test_empty_crates(self):
        result = _derive_rust_node_path("crates/foo/src/lib.rs", {})
        assert result is None


class TestDiscoverRustCrates:
    def test_discovers_crate(self, tmp_path):
        cargo_dir = tmp_path / "crates" / "mylib"
        cargo_dir.mkdir(parents=True)
        (cargo_dir / "Cargo.toml").write_text(
            '[package]\nname = "mylib"\nversion = "0.1.0"\n', encoding="utf-8"
        )
        crates = _discover_rust_crates(tmp_path)
        assert len(crates) >= 1
        names = {c["name"] for c in crates.values()}
        assert "mylib" in names

    def test_skips_workspace_root(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text(
            '[package]\nname = "workspace"\nversion = "0.1.0"\n[workspace]\n',
            encoding="utf-8",
        )
        (tmp_path / "crates" / "lib").mkdir(parents=True)
        (tmp_path / "crates" / "lib" / "Cargo.toml").write_text(
            '[package]\nname = "lib"\nversion = "0.1.0"\n', encoding="utf-8"
        )
        crates = _discover_rust_crates(tmp_path)
        names = {c["name"] for c in crates.values()}
        assert "lib" in names
        assert "workspace" not in names

    def test_discovers_multiple_crates(self, tmp_path):
        for name in ["cli", "core", "utils"]:
            d = tmp_path / "crates" / name
            d.mkdir(parents=True)
            (d / "Cargo.toml").write_text(
                f'[package]\nname = "{name}"\nversion = "0.1.0"\n', encoding="utf-8"
            )
        crates = _discover_rust_crates(tmp_path)
        names = {c["name"] for c in crates.values()}
        assert names == {"cli", "core", "utils"}

    def test_package_name_differs_from_dir(self, tmp_path):
        d = tmp_path / "crates" / "my-crate-dir"
        d.mkdir(parents=True)
        (d / "Cargo.toml").write_text(
            '[package]\nname = "my-crate-name"\nversion = "0.1.0"\n',
            encoding="utf-8",
        )
        crates = _discover_rust_crates(tmp_path)
        assert len(crates) == 1
        crate = next(iter(crates.values()))
        assert crate["name"] == "my-crate-name"
        assert crate["path"] == "crates/my-crate-dir"


class TestRustWorkspaceGraph:
    def _setup_symbiot_style(self, tmp_path: Path) -> None:
        """Create a Symbiot-style Rust workspace with cross-crate imports."""
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()

        (ai_debt / "project-profile.json").write_text(
            json.dumps({"project_name": "test-rust-ws", "languages": ["Rust"]}),
            encoding="utf-8",
        )

        evidence = {
            "schema_version": "1.0",
            "evidence": [
                {
                    "evidence_id": "EVD-001",
                    "type": "imports_detected",
                    "location": {"file": "crates/symbiot-cli/src/main.rs"},
                    "raw_observation": "symbiot_core::task::Task, symbiot_core::Vault",
                    "metadata": {
                        "imports": [
                            "symbiot_core::task::Task",
                            "symbiot_core::Vault",
                            "anyhow::Result",
                            "serde::Deserialize",
                        ]
                    },
                },
                {
                    "evidence_id": "EVD-002",
                    "type": "imports_detected",
                    "location": {"file": "crates/symbiot-core/src/config.rs"},
                    "raw_observation": "std::path::Path",
                    "metadata": {"imports": ["std::path::Path"]},
                },
            ],
        }
        (ai_debt / "evidence.json").write_text(json.dumps(evidence), encoding="utf-8")

        # Cargo.toml files
        (tmp_path / "Cargo.toml").write_text(
            '[workspace]\nmembers = ["crates/*"]\n', encoding="utf-8"
        )
        for crate_name in ["symbiot-cli", "symbiot-core", "symbiot-mcp"]:
            d = tmp_path / "crates" / crate_name
            d.mkdir(parents=True)
            (d / "Cargo.toml").write_text(
                f'[package]\nname = "{crate_name}"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )

    def test_separate_crate_nodes(self, tmp_path):
        self._setup_symbiot_style(tmp_path)
        result = build_graph(tmp_path, scope="package")
        graph = result.graph

        node_names = {n.name for n in graph.nodes if n.node_type != "analysis_unit"}
        # Only crates with evidence get nodes (symbiot-cli, symbiot-core)
        assert "symbiot-cli" in node_names
        assert "symbiot-core" in node_names
        # symbiot-mcp has no evidence so no node
        assert "symbiot-mcp" not in node_names

    def test_cross_crate_edge(self, tmp_path):
        self._setup_symbiot_style(tmp_path)
        result = build_graph(tmp_path, scope="package")
        graph = result.graph

        assert len(graph.edges) >= 1
        node_map = {n.node_id: n.name for n in graph.nodes}
        edge_pairs = {(node_map[e.source_node_id], node_map[e.target_node_id]) for e in graph.edges}
        assert ("symbiot-cli", "symbiot-core") in edge_pairs

    def test_external_crate_no_edge(self, tmp_path):
        self._setup_symbiot_style(tmp_path)
        result = build_graph(tmp_path, scope="package")
        graph = result.graph

        node_map = {n.node_id: n.name for n in graph.nodes}
        for edge in graph.edges:
            src = node_map[edge.source_node_id]
            tgt = node_map[edge.target_node_id]
            assert "serde" not in src and "serde" not in tgt
            assert "anyhow" not in src and "anyhow" not in tgt

    def test_std_no_edge(self, tmp_path):
        self._setup_symbiot_style(tmp_path)
        result = build_graph(tmp_path, scope="package")
        graph = result.graph

        node_map = {n.node_id: n.name for n in graph.nodes}
        for edge in graph.edges:
            tgt = node_map[edge.target_node_id]
            assert "std" not in tgt

    def test_workspace_root_not_a_node(self, tmp_path):
        self._setup_symbiot_style(tmp_path)
        result = build_graph(tmp_path, scope="package")
        graph = result.graph

        node_names = {n.name for n in graph.nodes if n.node_type != "analysis_unit"}
        # Should not have a root "workspace" node
        assert "workspace" not in node_names

    def test_kebab_snake_normalization(self, tmp_path):
        """symbiot-core in Cargo.toml matches symbiot_core in use statements."""
        self._setup_symbiot_style(tmp_path)
        result = build_graph(tmp_path, scope="package")
        graph = result.graph

        # Verify edge exists with correct target
        node_map = {n.node_id: n.name for n in graph.nodes}
        has_core_edge = any(node_map.get(e.target_node_id) == "symbiot-core" for e in graph.edges)
        assert has_core_edge, "symbiot_core import should resolve to symbiot-core node"


class TestRustIntraCrateImports:
    def _setup_with_crate_local(self, tmp_path: Path) -> None:
        """Create Rust workspace with intra-crate imports."""
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()

        (ai_debt / "project-profile.json").write_text(
            json.dumps({"project_name": "test-rust-intra", "languages": ["Rust"]}),
            encoding="utf-8",
        )

        evidence = {
            "schema_version": "1.0",
            "evidence": [
                {
                    "evidence_id": "EVD-001",
                    "type": "imports_detected",
                    "location": {"file": "crates/mylib/src/main.rs"},
                    "raw_observation": "crate::config, super::utils, self::helpers",
                    "metadata": {"imports": ["crate::config", "super::utils", "self::helpers"]},
                },
            ],
        }
        (ai_debt / "evidence.json").write_text(json.dumps(evidence), encoding="utf-8")

        (tmp_path / "Cargo.toml").write_text(
            '[workspace]\nmembers = ["crates/*"]\n', encoding="utf-8"
        )
        d = tmp_path / "crates" / "mylib"
        d.mkdir(parents=True)
        (d / "Cargo.toml").write_text(
            '[package]\nname = "mylib"\nversion = "0.1.0"\n', encoding="utf-8"
        )

    def test_crate_self_no_edge(self, tmp_path):
        self._setup_with_crate_local(tmp_path)
        result = build_graph(tmp_path, scope="package")
        graph = result.graph
        assert len(graph.edges) == 0

    def test_super_no_edge(self, tmp_path):
        self._setup_with_crate_local(tmp_path)
        result = build_graph(tmp_path, scope="package")
        graph = result.graph
        assert len(graph.edges) == 0

    def test_self_no_edge(self, tmp_path):
        self._setup_with_crate_local(tmp_path)
        result = build_graph(tmp_path, scope="package")
        graph = result.graph
        assert len(graph.edges) == 0


class TestRustEdgeAggregation:
    def _setup_multi_import(self, tmp_path: Path) -> None:
        """Multiple cross-crate imports from different files."""
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()

        (ai_debt / "project-profile.json").write_text(
            json.dumps({"project_name": "test-rust-agg", "languages": ["Rust"]}),
            encoding="utf-8",
        )

        evidence = {
            "schema_version": "1.0",
            "evidence": [
                {
                    "evidence_id": "EVD-001",
                    "type": "imports_detected",
                    "location": {"file": "crates/cli/src/main.rs"},
                    "raw_observation": "core_lib::foo",
                    "metadata": {"imports": ["core_lib::foo"]},
                },
                {
                    "evidence_id": "EVD-002",
                    "type": "imports_detected",
                    "location": {"file": "crates/cli/src/app.rs"},
                    "raw_observation": "core_lib::bar",
                    "metadata": {"imports": ["core_lib::bar"]},
                },
            ],
        }
        (ai_debt / "evidence.json").write_text(json.dumps(evidence), encoding="utf-8")

        (tmp_path / "Cargo.toml").write_text(
            '[workspace]\nmembers = ["crates/*"]\n', encoding="utf-8"
        )
        for name in ["cli", "core-lib"]:
            d = tmp_path / "crates" / name
            d.mkdir(parents=True)
            (d / "Cargo.toml").write_text(
                f'[package]\nname = "{name}"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )

    def test_duplicate_imports_aggregate(self, tmp_path):
        self._setup_multi_import(tmp_path)
        result = build_graph(tmp_path, scope="package")
        graph = result.graph

        node_map = {n.node_id: n.name for n in graph.nodes}
        cli_core_edges = [
            e
            for e in graph.edges
            if node_map.get(e.source_node_id) == "cli"
            and node_map.get(e.target_node_id) == "core-lib"
        ]
        assert len(cli_core_edges) == 1  # Single aggregated edge
        assert cli_core_edges[0].import_count == 2  # Two imports aggregated


class TestRustNonWorkspace:
    def _setup_single_crate(self, tmp_path: Path) -> None:
        """Single crate repo (no workspace)."""
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()

        (ai_debt / "project-profile.json").write_text(
            json.dumps({"project_name": "test-rust-single", "languages": ["Rust"]}),
            encoding="utf-8",
        )

        evidence = {
            "schema_version": "1.0",
            "evidence": [
                {
                    "evidence_id": "EVD-001",
                    "type": "imports_detected",
                    "location": {"file": "src/main.rs"},
                    "raw_observation": "serde::Serialize",
                    "metadata": {"imports": ["serde::Serialize"]},
                },
            ],
        }
        (ai_debt / "evidence.json").write_text(json.dumps(evidence), encoding="utf-8")

        # Single crate with package but no workspace
        (tmp_path / "Cargo.toml").write_text(
            '[package]\nname = "myapp"\nversion = "0.1.0"\n', encoding="utf-8"
        )

    def test_single_crate_still_works(self, tmp_path):
        self._setup_single_crate(tmp_path)
        result = build_graph(tmp_path, scope="package")
        graph = result.graph
        # Should have at least one node (from default derivation)
        assert len(graph.nodes) >= 1


class TestRustNoHighCouplingFindings:
    def _setup_with_edge(self, tmp_path: Path) -> None:
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        (ai_debt / "project-profile.json").write_text(
            json.dumps({"project_name": "test-rust-hc", "languages": ["Rust"]}),
            encoding="utf-8",
        )
        evidence = {
            "schema_version": "1.0",
            "evidence": [
                {
                    "evidence_id": "EVD-001",
                    "type": "imports_detected",
                    "location": {"file": "crates/cli/src/main.rs"},
                    "raw_observation": "core_lib::foo",
                    "metadata": {"imports": ["core_lib::foo"]},
                },
            ],
        }
        (ai_debt / "evidence.json").write_text(json.dumps(evidence), encoding="utf-8")
        (tmp_path / "Cargo.toml").write_text(
            '[workspace]\nmembers = ["crates/*"]\n', encoding="utf-8"
        )
        for name in ["cli", "core-lib"]:
            d = tmp_path / "crates" / name
            d.mkdir(parents=True)
            (d / "Cargo.toml").write_text(
                f'[package]\nname = "{name}"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )

    def test_no_high_coupling_td_arch(self, tmp_path):
        self._setup_with_edge(tmp_path)
        result = build_graph(tmp_path, scope="package")
        graph = result.graph
        # Coupling metrics should exist but not produce findings
        assert len(graph.coupling_metrics) > 0
        # No cycles = no TD-ARCH findings from graph
        assert len(graph.cycles) == 0
