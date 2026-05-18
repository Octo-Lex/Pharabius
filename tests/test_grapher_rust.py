"""Tests for Rust graph resolution enhancements."""

import json
from pathlib import Path

from pharabius.core.grapher import (
    _discover_rust_crates,
    build_graph,
)


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


class TestRustGraphIntegration:
    def _setup_rust_repo(self, tmp_path: Path) -> None:
        """Create a minimal Rust workspace with evidence."""
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()

        (ai_debt / "project-profile.json").write_text(
            json.dumps({"project_name": "test-rust", "languages": ["Rust"]}),
            encoding="utf-8",
        )

        evidence = {
            "schema_version": "1.0",
            "evidence": [
                {
                    "evidence_id": "EVD-001",
                    "type": "imports_detected",
                    "location": {"file": "crates/cli/src/main.rs"},
                    "raw_observation": "mylib, serde",
                    "metadata": {"imports": ["mylib", "serde::Serialize"]},
                },
                {
                    "evidence_id": "EVD-002",
                    "type": "imports_detected",
                    "location": {"file": "crates/cli/src/main.rs"},
                    "raw_observation": "crate::config",
                    "metadata": {"imports": ["crate::config"]},
                },
            ],
        }
        (ai_debt / "evidence.json").write_text(json.dumps(evidence), encoding="utf-8")

        # Create Cargo.toml files
        (tmp_path / "Cargo.toml").write_text(
            '[workspace]\nmembers = ["crates/*"]\n', encoding="utf-8"
        )
        (tmp_path / "crates" / "cli").mkdir(parents=True)
        (tmp_path / "crates" / "cli" / "Cargo.toml").write_text(
            '[package]\nname = "cli"\nversion = "0.1.0"\n', encoding="utf-8"
        )
        (tmp_path / "crates" / "mylib").mkdir(parents=True)
        (tmp_path / "crates" / "mylib" / "Cargo.toml").write_text(
            '[package]\nname = "mylib"\nversion = "0.1.0"\n', encoding="utf-8"
        )

    def test_rust_produces_imports_evidence(self, tmp_path):
        self._setup_rust_repo(tmp_path)
        result = build_graph(tmp_path, scope="package")
        graph = result.graph
        # Should have nodes from the evidence
        assert len(graph.nodes) >= 1

    def test_external_crate_no_edge(self, tmp_path):
        self._setup_rust_repo(tmp_path)
        result = build_graph(tmp_path, scope="package")
        graph = result.graph

        node_map = {n.node_id: n.name for n in graph.nodes}
        for edge in graph.edges:
            tgt = node_map[edge.target_node_id]
            assert "serde" not in tgt
