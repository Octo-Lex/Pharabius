"""v3.10.0 S05 — Shared ecosystem parser contract tests.

Proves v3.9.0 architecture is real by validating that every runtime parser
produces well-formed RuntimeEvidence with all required fields.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest

from pharabius.core.runtime.models import RuntimeEvidence, RuntimeSourceGrade


# ── Contract helper ──────────────────────────────────────────────────


def assert_runtime_parser_contract(evidence: list[RuntimeEvidence]) -> None:
    """Validate that all evidence items satisfy the runtime parser contract."""
    assert len(evidence) > 0, "Parser must produce at least one evidence item"
    for item in evidence:
        assert isinstance(item, RuntimeEvidence), f"Expected RuntimeEvidence, got {type(item)}"
        assert item.runtime_evidence_id, "Every evidence item must have a deterministic ID"
        assert item.ecosystem, "Every evidence item must have an ecosystem"
        assert item.runtime_name, "Every evidence item must have a runtime_name"
        assert item.constraint.kind, "Every evidence item must have a constraint kind"
        assert item.source_path, "Every evidence item must have a source_path"
        assert item.source_grade != RuntimeSourceGrade.UNKNOWN, (
            f"source_grade must be explicitly set (got UNKNOWN for {item.source_path})"
        )


# ── Fixture helpers ──────────────────────────────────────────────────


@pytest.fixture()
def python_repo(tmp_path: Path) -> Path:
    (tmp_path / ".python-version").write_text("3.11.5\n")
    (tmp_path / "pyproject.toml").write_text('requires-python = ">=3.11"\n')
    return tmp_path


@pytest.fixture()
def node_repo(tmp_path: Path) -> Path:
    (tmp_path / ".nvmrc").write_text("20.11.0\n")
    (tmp_path / "package.json").write_text('{"engines": {"node": ">=20"}}\n')
    return tmp_path


@pytest.fixture()
def ruby_repo(tmp_path: Path) -> Path:
    (tmp_path / ".ruby-version").write_text("3.3.0\n")
    (tmp_path / "Gemfile").write_text('ruby "3.3.0"\n')
    return tmp_path


@pytest.fixture()
def java_repo(tmp_path: Path) -> Path:
    (tmp_path / ".java-version").write_text("21\n")
    (tmp_path / "pom.xml").write_text(
        "<project><properties><maven.compiler.release>21</maven.compiler.release></properties></project>"
    )
    return tmp_path


@pytest.fixture()
def docker_repo(tmp_path: Path) -> Path:
    (tmp_path / "Dockerfile").write_text("FROM python:3.11\n")
    return tmp_path


@pytest.fixture()
def ci_repo(tmp_path: Path) -> Path:
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "ci.yml").write_text(
        "jobs:\n  build:\n    steps:\n"
        "      - uses: actions/setup-python@v5\n"
        "        with:\n          python-version: '3.11'\n"
    )
    return tmp_path


@pytest.fixture()
def tool_versions_repo(tmp_path: Path) -> Path:
    (tmp_path / ".tool-versions").write_text("python 3.11.5\nnodejs 20.11.0\n")
    return tmp_path


# ── Contract tests for existing parsers ──────────────────────────────


class TestPythonParserContract:
    def test_python_sources_pass_contract(self, python_repo: Path) -> None:
        from pharabius.core.runtime.ecosystems import detect_python_sources
        evidence = detect_python_sources(python_repo)
        assert_runtime_parser_contract(evidence)


class TestNodeParserContract:
    def test_node_sources_pass_contract(self, node_repo: Path) -> None:
        from pharabius.core.runtime.ecosystems import detect_node_sources
        evidence = detect_node_sources(node_repo)
        assert_runtime_parser_contract(evidence)


class TestRubyParserContract:
    def test_ruby_sources_pass_contract(self, ruby_repo: Path) -> None:
        from pharabius.core.runtime.ecosystems import detect_ruby_sources
        evidence = detect_ruby_sources(ruby_repo)
        assert_runtime_parser_contract(evidence)


class TestJavaParserContract:
    def test_java_sources_pass_contract(self, java_repo: Path) -> None:
        from pharabius.core.runtime.ecosystems import detect_java_sources
        evidence = detect_java_sources(java_repo)
        assert_runtime_parser_contract(evidence)


class TestDockerParserContract:
    def test_dockerfile_sources_pass_contract(self, docker_repo: Path) -> None:
        from pharabius.core.runtime.docker import detect_dockerfile_sources
        evidence = detect_dockerfile_sources(docker_repo)
        assert_runtime_parser_contract(evidence)


class TestCIParserContract:
    def test_ci_sources_pass_contract(self, ci_repo: Path) -> None:
        from pharabius.core.runtime.github_actions import detect_ci_sources
        evidence = detect_ci_sources(ci_repo)
        assert_runtime_parser_contract(evidence)


class TestToolVersionsContract:
    def test_tool_versions_pass_contract(self, tool_versions_repo: Path) -> None:
        from pharabius.core.runtime.tool_versions import detect_tool_versions_sources
        evidence = detect_tool_versions_sources(tool_versions_repo)
        assert_runtime_parser_contract(evidence)


# ── Boundary tests ───────────────────────────────────────────────────


class TestParserBoundary:
    """No parser may import detector.py or EvidenceBuilder."""

    def test_ecosystems_does_not_import_detector(self) -> None:
        import importlib
        mod = importlib.import_module("pharabius.core.runtime.ecosystems")
        source = inspect_getsource(mod)
        assert "detector" not in source
        assert "EvidenceBuilder" not in source

    def test_docker_does_not_import_detector(self) -> None:
        import importlib
        mod = importlib.import_module("pharabius.core.runtime.docker")
        source = inspect_getsource(mod)
        assert "detector" not in source
        assert "EvidenceBuilder" not in source

    def test_github_actions_does_not_import_detector(self) -> None:
        import importlib
        mod = importlib.import_module("pharabius.core.runtime.github_actions")
        source = inspect_getsource(mod)
        assert "detector" not in source
        assert "EvidenceBuilder" not in source


def inspect_getsource(mod) -> str:
    import inspect
    return inspect.getsource(mod)


# ── Deterministic ID tests ───────────────────────────────────────────


class TestDeterministicIDs:
    """Evidence IDs must be deterministic (stable, unique, source-detail-aware)."""

    def test_ids_are_unique_within_single_scan(self, python_repo: Path) -> None:
        from pharabius.core.runtime.ecosystems import detect_python_sources
        evidence = detect_python_sources(python_repo)
        ids = [e.runtime_evidence_id for e in evidence]
        assert len(ids) == len(set(ids)), "Evidence IDs must be unique"

    def test_ids_are_stable_across_runs(self, python_repo: Path) -> None:
        from pharabius.core.runtime.ecosystems import detect_python_sources
        run1 = detect_python_sources(python_repo)
        run2 = detect_python_sources(python_repo)
        ids1 = sorted(e.runtime_evidence_id for e in run1)
        ids2 = sorted(e.runtime_evidence_id for e in run2)
        assert ids1 == ids2, "Evidence IDs must be stable across repeated scans"

    def test_ids_distinguish_source_detail(self, tmp_path: Path) -> None:
        """Two sources with same ecosystem but different source_detail produce different IDs."""
        from pharabius.core.runtime.ecosystems import detect_python_sources
        (tmp_path / ".python-version").write_text("3.11.5\n")
        (tmp_path / "pyproject.toml").write_text('requires-python = "3.11.5"\n')
        evidence = detect_python_sources(tmp_path)
        ids = [e.runtime_evidence_id for e in evidence]
        assert len(ids) == len(set(ids)), "IDs must distinguish source_detail"
        # Verify different source paths
        paths = set(e.source_path for e in evidence)
        assert len(paths) >= 2, "Should have evidence from multiple sources"
