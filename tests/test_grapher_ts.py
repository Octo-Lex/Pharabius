"""Tests for TypeScript/JavaScript monorepo graph enhancements."""

import json
from pathlib import Path

from pharabius.core.grapher import (
    _derive_ts_node_path,
    _discover_ts_packages,
    _match_ts_workspace_import,
    build_graph,
)


class TestDiscoverTSPackages:
    def test_discovers_packages_dir(self, tmp_path):
        (tmp_path / "packages" / "core" / "package.json").parent.mkdir(parents=True)
        (tmp_path / "packages" / "core" / "package.json").write_text(
            json.dumps({"name": "@repo/core"}), encoding="utf-8"
        )
        (tmp_path / "packages" / "api" / "package.json").parent.mkdir(parents=True)
        (tmp_path / "packages" / "api" / "package.json").write_text(
            json.dumps({"name": "@repo/api"}), encoding="utf-8"
        )
        pkgs = _discover_ts_packages(tmp_path)
        assert len(pkgs) == 2
        names = {p["name"] for p in pkgs.values()}
        assert "@repo/core" in names
        assert "@repo/api" in names

    def test_discovers_apps_dir(self, tmp_path):
        (tmp_path / "apps" / "web" / "package.json").parent.mkdir(parents=True)
        (tmp_path / "apps" / "web" / "package.json").write_text(
            json.dumps({"name": "web"}), encoding="utf-8"
        )
        pkgs = _discover_ts_packages(tmp_path)
        assert len(pkgs) == 1
        assert next(iter(pkgs.values()))["name"] == "web"

    def test_ignores_no_package_json(self, tmp_path):
        (tmp_path / "packages" / "utils").mkdir(parents=True)
        # No package.json
        pkgs = _discover_ts_packages(tmp_path)
        assert len(pkgs) == 0

    def test_fallback_to_dir_name(self, tmp_path):
        (tmp_path / "packages" / "core" / "package.json").parent.mkdir(parents=True)
        (tmp_path / "packages" / "core" / "package.json").write_text("{}", encoding="utf-8")
        pkgs = _discover_ts_packages(tmp_path)
        assert len(pkgs) == 1
        assert next(iter(pkgs.values()))["name"] == "core"


class TestWorkspaceImportMatching:
    def test_exact_match(self):
        result = _match_ts_workspace_import("@repo/core", {"@repo/core", "@repo/api"})
        assert result == "@repo/core"

    def test_subpath_match(self):
        result = _match_ts_workspace_import("@repo/core/foo", {"@repo/core", "@repo/api"})
        assert result == "@repo/core"

    def test_no_false_prefix(self):
        result = _match_ts_workspace_import("@repo/core-extra", {"@repo/core", "@repo/api"})
        assert result is None

    def test_longest_prefix(self):
        result = _match_ts_workspace_import("@repo/core/utils", {"@repo/core", "@repo/core/utils"})
        assert result == "@repo/core/utils"

    def test_no_match(self):
        result = _match_ts_workspace_import("react", {"@repo/core", "@repo/api"})
        assert result is None

    def test_empty_set(self):
        result = _match_ts_workspace_import("@repo/core", set())
        assert result is None

    def test_unscoped_match(self):
        result = _match_ts_workspace_import("my-lib", {"my-lib", "other-lib"})
        assert result == "my-lib"

    def test_unscoped_no_prefix_collision(self):
        result = _match_ts_workspace_import("my-lib-extra", {"my-lib", "other-lib"})
        assert result is None


class TestDeriveTSNodePath:
    def test_file_in_package(self):
        pkgs = {
            "ts:@repo/core:packages/core": {
                "name": "@repo/core",
                "path": "packages/core",
                "dir": "core",
            }
        }
        result = _derive_ts_node_path("packages/core/src/index.ts", pkgs)
        assert result == ("@repo/core", "packages/core")

    def test_file_not_in_package(self):
        pkgs = {
            "ts:@repo/core:packages/core": {
                "name": "@repo/core",
                "path": "packages/core",
                "dir": "core",
            }
        }
        result = _derive_ts_node_path("src/utils.ts", pkgs)
        assert result is None


class TestTSMonorepoGraph:
    def _setup_monorepo(self, tmp_path: Path) -> None:
        """Create a minimal TS monorepo with evidence."""
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()

        # Profile
        (ai_debt / "project-profile.json").write_text(
            json.dumps({"project_name": "test-monorepo", "languages": ["TypeScript"]}),
            encoding="utf-8",
        )

        # Evidence with imports
        evidence = {
            "schema_version": "1.0",
            "evidence": [
                {
                    "evidence_id": "EVD-001",
                    "type": "imports_detected",
                    "location": {"file": "packages/api/src/app.ts"},
                    "raw_observation": "@repo/core, vitest",
                    "metadata": {"imports": ["@repo/core", "vitest"]},
                },
                {
                    "evidence_id": "EVD-002",
                    "type": "imports_detected",
                    "location": {"file": "packages/api/src/utils.ts"},
                    "raw_observation": "@repo/core",
                    "metadata": {"imports": ["@repo/core"]},
                },
                {
                    "evidence_id": "EVD-003",
                    "type": "imports_detected",
                    "location": {"file": "packages/core/src/index.ts"},
                    "raw_observation": "lodash",
                    "metadata": {"imports": ["lodash"]},
                },
            ],
        }
        (ai_debt / "evidence.json").write_text(json.dumps(evidence), encoding="utf-8")

        # Package jsons
        (tmp_path / "packages" / "api" / "package.json").parent.mkdir(parents=True)
        (tmp_path / "packages" / "api" / "package.json").write_text(
            json.dumps({"name": "@repo/api"}), encoding="utf-8"
        )
        (tmp_path / "packages" / "core" / "package.json").parent.mkdir(parents=True)
        (tmp_path / "packages" / "core" / "package.json").write_text(
            json.dumps({"name": "@repo/core"}), encoding="utf-8"
        )

    def test_separate_package_nodes(self, tmp_path):
        self._setup_monorepo(tmp_path)
        result = build_graph(tmp_path, scope="package")
        graph = result.graph

        node_names = {n.name for n in graph.nodes if n.node_type != "analysis_unit"}
        assert "@repo/api" in node_names
        assert "@repo/core" in node_names

    def test_workspace_import_creates_edge(self, tmp_path):
        self._setup_monorepo(tmp_path)
        result = build_graph(tmp_path, scope="package")
        graph = result.graph

        assert len(graph.edges) >= 1
        # api -> core edge
        node_map = {n.node_id: n.name for n in graph.nodes}
        edge_pairs = {(node_map[e.source_node_id], node_map[e.target_node_id]) for e in graph.edges}
        assert ("@repo/api", "@repo/core") in edge_pairs

    def test_external_import_no_edge(self, tmp_path):
        self._setup_monorepo(tmp_path)
        result = build_graph(tmp_path, scope="package")
        graph = result.graph

        node_map = {n.node_id: n.name for n in graph.nodes}
        for edge in graph.edges:
            src = node_map[edge.source_node_id]
            tgt = node_map[edge.target_node_id]
            assert "lodash" not in src and "lodash" not in tgt
            assert "vitest" not in src and "vitest" not in tgt

    def test_root_package_json_not_collapsing(self, tmp_path):
        self._setup_monorepo(tmp_path)
        # Add root package.json (workspace root)
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "monorepo-root", "workspaces": ["packages/*"]}),
            encoding="utf-8",
        )
        result = build_graph(tmp_path, scope="package")
        graph = result.graph

        node_names = {n.name for n in graph.nodes if n.node_type != "analysis_unit"}
        # Workspace packages should still be separate
        assert "@repo/api" in node_names
        assert "@repo/core" in node_names


class TestTSNoFalsePrefix:
    def _setup_with_extra(self, tmp_path: Path) -> None:
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()

        (ai_debt / "project-profile.json").write_text(
            json.dumps({"project_name": "test-prefix", "languages": ["TypeScript"]}),
            encoding="utf-8",
        )

        evidence = {
            "schema_version": "1.0",
            "evidence": [
                {
                    "evidence_id": "EVD-001",
                    "type": "imports_detected",
                    "location": {"file": "packages/api/src/app.ts"},
                    "raw_observation": "@repo/core-extra",
                    "metadata": {"imports": ["@repo/core-extra"]},
                },
            ],
        }
        (ai_debt / "evidence.json").write_text(json.dumps(evidence), encoding="utf-8")

        (tmp_path / "packages" / "api" / "package.json").parent.mkdir(parents=True)
        (tmp_path / "packages" / "api" / "package.json").write_text(
            json.dumps({"name": "@repo/api"}), encoding="utf-8"
        )
        (tmp_path / "packages" / "core" / "package.json").parent.mkdir(parents=True)
        (tmp_path / "packages" / "core" / "package.json").write_text(
            json.dumps({"name": "@repo/core"}), encoding="utf-8"
        )

    def test_core_extra_not_matching_core(self, tmp_path):
        self._setup_with_extra(tmp_path)
        result = build_graph(tmp_path, scope="package")
        graph = result.graph

        # No edge should be created because @repo/core-extra doesn't match
        node_map = {n.node_id: n.name for n in graph.nodes}
        for edge in graph.edges:
            tgt = node_map[edge.target_node_id]
            assert tgt != "@repo/core", "@repo/core-extra should not match @repo/core"
