"""v3.8.0 — Runtime Reproducibility & Conflict Signals.

Tests cover:
- Python/Node conflict detection
- Ruby runtime pin evidence
- Java runtime pin evidence
- Dockerfile runtime evidence
- GitHub Actions runtime evidence
- Constraint kind model (exact/range/partial)
- Missing runtime pin advisory classification
- Conflict finding classification
- Planner/claims exclusion of advisories
- Run-history regression
- Clean-baseline quietness preservation
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.fixture_builder import BenchmarkFixture
from pharabius.core.constants import (
    EVIDENCE_RUNTIME_VERSION_SIGNAL,
    RUNTIME_SIGNAL_CONFLICT,
    RUNTIME_SIGNAL_FROM_CI,
    RUNTIME_SIGNAL_FROM_CONTAINER,
    RUNTIME_SIGNAL_MISSING,
    RUNTIME_SIGNAL_PARTIAL,
    RUNTIME_SIGNAL_PINNED,
)
from pharabius.core.run_metadata import execute_run
from pharabius.core.runtime_parsers import detect_runtime_version_pins
from pharabius.schemas.evidence import EvidenceBuilder


# ── Helpers ──────────────────────────────────────────────────────────


def _detect(root: Path) -> list:
    """Run runtime detection and return evidence items."""
    builder = EvidenceBuilder()
    detect_runtime_version_pins(root, builder)
    return builder.items


def _signals(items: list, signal: str) -> list:
    """Filter evidence items by signal type."""
    return [i for i in items if i.metadata.get("signal") == signal]


def _run_pipeline(repo_path: Path) -> dict:
    """Run the full pipeline and return debt-register."""
    execute_run(repo_path)
    reg_path = repo_path / ".ai-debt" / "debt-register.json"
    return json.loads(reg_path.read_text(encoding="utf-8"))


# ── S01: Python/Node conflicts ───────────────────────────────────────


class TestPythonNodeConflicts:
    def test_python_runtime_conflict_detected(self, tmp_path):
        """`.python-version=3.11` vs `.tool-versions python=3.12` → conflict."""
        (tmp_path / ".python-version").write_text("3.11\n")
        (tmp_path / ".tool-versions").write_text("python 3.12\n")
        (tmp_path / "pyproject.toml").write_text("[project]\n")

        items = _detect(tmp_path)
        conflicts = _signals(items, RUNTIME_SIGNAL_CONFLICT)
        assert len(conflicts) == 1
        assert conflicts[0].metadata["runtime"] == "Python"
        assert conflicts[0].metadata["conflict_reason"] == "exact_vs_exact_disagreement"

    def test_node_runtime_conflict_detected(self, tmp_path):
        """`.nvmrc=18` vs `.node-version=20` → conflict."""
        (tmp_path / ".nvmrc").write_text("18\n")
        (tmp_path / ".node-version").write_text("20\n")
        (tmp_path / "package.json").write_text('{"name":"test"}\n')

        items = _detect(tmp_path)
        conflicts = _signals(items, RUNTIME_SIGNAL_CONFLICT)
        assert len(conflicts) == 1
        assert conflicts[0].metadata["runtime"] == "Node.js"

    def test_package_json_engines_compatible_range_not_conflict(self, tmp_path):
        """`engines.node >= 18` + `.nvmrc=20` → compatible, no conflict."""
        (tmp_path / ".nvmrc").write_text("20\n")
        (tmp_path / "package.json").write_text('{"engines":{"node":">=18"}}\n')

        items = _detect(tmp_path)
        conflicts = _signals(items, RUNTIME_SIGNAL_CONFLICT)
        assert len(conflicts) == 0

    def test_requires_python_range_not_conflict_with_pin(self, tmp_path):
        """`requires-python >= 3.11` + `.python-version=3.12` → compatible."""
        (tmp_path / ".python-version").write_text("3.12\n")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\nrequires-python = ">=3.11"\n'
        )

        items = _detect(tmp_path)
        conflicts = _signals(items, RUNTIME_SIGNAL_CONFLICT)
        assert len(conflicts) == 0

    def test_requires_python_excludes_pin_conflict(self, tmp_path):
        """`requires-python >= 3.12` + `.python-version=3.11` → conflict."""
        (tmp_path / ".python-version").write_text("3.11\n")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\nrequires-python = ">=3.12"\n'
        )

        items = _detect(tmp_path)
        conflicts = _signals(items, RUNTIME_SIGNAL_CONFLICT)
        assert len(conflicts) == 1
        assert conflicts[0].metadata["conflict_reason"] == "range_excludes_exact"


# ── S02: Ruby runtime ───────────────────────────────────────────────


class TestRubyRuntime:
    def test_ruby_version_file_detected(self, tmp_path):
        (tmp_path / ".ruby-version").write_text("3.3.0\n")
        (tmp_path / "Gemfile").write_text('source "https://rubygems.org"\n')

        items = _detect(tmp_path)
        pinned = _signals(items, RUNTIME_SIGNAL_PINNED)
        ruby_pins = [i for i in pinned if i.metadata.get("runtime") == "Ruby"]
        assert len(ruby_pins) >= 1
        assert any(i.metadata["version"] == "3.3.0" for i in ruby_pins)

    def test_gemfile_ruby_version_detected(self, tmp_path):
        (tmp_path / "Gemfile").write_text(
            'source "https://rubygems.org"\nruby "3.3.0"\n'
        )

        items = _detect(tmp_path)
        pinned = _signals(items, RUNTIME_SIGNAL_PINNED)
        ruby_pins = [i for i in pinned if i.metadata.get("runtime") == "Ruby"]
        assert len(ruby_pins) >= 1

    def test_gemfile_broad_range_is_range_constraint(self, tmp_path):
        (tmp_path / "Gemfile").write_text(
            'source "https://rubygems.org"\nruby "~> 3.2"\n'
        )

        items = _detect(tmp_path)
        pinned = _signals(items, RUNTIME_SIGNAL_PINNED)
        ruby_pins = [i for i in pinned if i.metadata.get("runtime") == "Ruby"]
        assert len(ruby_pins) >= 1
        assert ruby_pins[0].metadata["constraint_kind"] == "range"


# ── S03: Java runtime ───────────────────────────────────────────────


class TestJavaRuntime:
    def test_java_version_file_detected(self, tmp_path):
        (tmp_path / ".java-version").write_text("17\n")
        (tmp_path / "pom.xml").write_text("<project></project>")

        items = _detect(tmp_path)
        pinned = _signals(items, RUNTIME_SIGNAL_PINNED)
        java_pins = [i for i in pinned if i.metadata.get("runtime") == "Java"]
        assert len(java_pins) >= 1
        assert java_pins[0].metadata["version"] == "17"

    def test_maven_compiler_release_detected(self, tmp_path):
        (tmp_path / "pom.xml").write_text(
            "<project><properties>"
            "<maven.compiler.release>17</maven.compiler.release>"
            "</properties></project>"
        )

        items = _detect(tmp_path)
        pinned = _signals(items, RUNTIME_SIGNAL_PINNED)
        java_pins = [i for i in pinned if i.metadata.get("runtime") == "Java"]
        assert len(java_pins) >= 1
        assert java_pins[0].metadata["source_file"] == "pom.xml"

    def test_gradle_java_version_detected(self, tmp_path):
        (tmp_path / "build.gradle").write_text(
            "sourceCompatibility = JavaVersion.VERSION_17\n"
        )

        items = _detect(tmp_path)
        pinned = _signals(items, RUNTIME_SIGNAL_PINNED)
        java_pins = [i for i in pinned if i.metadata.get("runtime") == "Java"]
        assert len(java_pins) >= 1
        assert java_pins[0].metadata["version"] == "17"


# ── S04: Dockerfile runtime ─────────────────────────────────────────


class TestDockerfileRuntime:
    def test_dockerfile_python_runtime_detected(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM python:3.12\nRUN pip install .\n")

        items = _detect(tmp_path)
        container = _signals(items, RUNTIME_SIGNAL_FROM_CONTAINER)
        python = [i for i in container if i.metadata.get("runtime") == "Python"]
        assert len(python) >= 1
        assert python[0].metadata["version"] == "3.12"

    def test_multistage_dockerfile_runtime_detected(self, tmp_path):
        (tmp_path / "Dockerfile").write_text(
            "FROM node:20 AS build\nRUN npm build\n"
            "FROM python:3.12 AS runtime\nCOPY . .\n"
        )

        items = _detect(tmp_path)
        container = _signals(items, RUNTIME_SIGNAL_FROM_CONTAINER)
        runtimes = {i.metadata["runtime"] for i in container}
        assert "Python" in runtimes
        assert "Node.js" in runtimes
        # Multi-stage with different runtimes is NOT a conflict
        conflicts = _signals(items, RUNTIME_SIGNAL_CONFLICT)
        assert len(conflicts) == 0

    def test_dockerfile_arg_runtime_partial(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM python:${VERSION}\n")

        items = _detect(tmp_path)
        partial = _signals(items, RUNTIME_SIGNAL_PARTIAL)
        assert len(partial) >= 1


# ── S05: GitHub Actions runtime ──────────────────────────────────────


class TestGitHubActionsRuntime:
    def test_github_actions_python_runtime_detected(self, tmp_path):
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text(
            "name: CI\non: [push]\njobs:\n  test:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@v4\n"
            '      - uses: actions/setup-python@v5\n'
            "        with:\n"
            '          python-version: "3.12"\n'
        )

        items = _detect(tmp_path)
        ci = _signals(items, RUNTIME_SIGNAL_FROM_CI)
        python = [i for i in ci if i.metadata.get("runtime") == "Python"]
        assert len(python) >= 1
        assert python[0].metadata["version"] == "3.12"

    def test_github_actions_node_runtime_detected(self, tmp_path):
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text(
            "name: CI\non: [push]\njobs:\n  test:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - uses: actions/setup-node@v4\n"
            "        with:\n"
            '          node-version: "20"\n'
        )

        items = _detect(tmp_path)
        ci = _signals(items, RUNTIME_SIGNAL_FROM_CI)
        node = [i for i in ci if i.metadata.get("runtime") == "Node.js"]
        assert len(node) >= 1

    def test_ci_runtime_conflict_detected(self, tmp_path):
        """CI setup-python=3.10 vs .python-version=3.12 → conflict."""
        (tmp_path / ".python-version").write_text("3.12\n")
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yml").write_text(
            "name: CI\non: [push]\njobs:\n  test:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@v4\n"
            '      - uses: actions/setup-python@v5\n'
            "        with:\n"
            '          python-version: "3.10"\n'
        )

        items = _detect(tmp_path)
        conflicts = _signals(items, RUNTIME_SIGNAL_CONFLICT)
        assert len(conflicts) >= 1

    def test_malformed_github_actions_workflow_does_not_crash(self, tmp_path):
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "bad.yml").write_text("{{{{invalid yaml:::\n")

        items = _detect(tmp_path)
        # Should not crash; should produce partial evidence
        partial = _signals(items, RUNTIME_SIGNAL_PARTIAL)
        assert len(partial) >= 1


# ── S06: Analyzer behavior ───────────────────────────────────────────


class TestRuntimeAnalyzerBehavior:
    def test_runtime_conflict_generates_finding(self, tmp_path):
        """Runtime conflict → technical_debt finding."""
        builder = BenchmarkFixture("rt-conflict", tmp_path)
        (builder
         .add_file(".python-version", "3.11\n")
         .add_file(".tool-versions", "python 3.12\n")
         .add_file("pyproject.toml", "[project]\nname='x'\n"))
        builder.build()
        reg = _run_pipeline(tmp_path / "rt-conflict")

        conflict_findings = [
            f for f in reg["findings"]
            if f["category"] == "TD-DEP"
            and "conflict" in f.get("title", "").lower()
        ]
        assert len(conflict_findings) >= 1
        assert conflict_findings[0]["issue_type"] == "technical_debt"

    def test_missing_runtime_pin_is_advisory(self, tmp_path):
        """Missing runtime pin → advisory, not technical_debt finding."""
        builder = BenchmarkFixture("rt-missing", tmp_path)
        (builder
         .add_pyproject(name="test")
         .add_python_file("src/app.py", "x = 1\n"))
        builder.build()
        reg = _run_pipeline(tmp_path / "rt-missing")

        missing_findings = [
            f for f in reg["findings"]
            if f["category"] == "TD-DEP"
            and "missing runtime" in f.get("title", "").lower()
        ]
        assert len(missing_findings) >= 1
        for f in missing_findings:
            assert f["issue_type"] == "advisory"

    def test_runtime_advisories_do_not_generate_work_packages(self, tmp_path):
        builder = BenchmarkFixture("rt-missing", tmp_path)
        (builder
         .add_pyproject(name="test")
         .add_python_file("src/app.py", "x = 1\n"))
        builder.build()
        execute_run(tmp_path / "rt-missing")

        wp_dir = tmp_path / "rt-missing" / ".ai-debt" / "work-packages"
        wp_files = list(wp_dir.glob("WP-*.md"))
        # Runtime missing-pin advisories should NOT generate WPs
        for wp in wp_files:
            text = wp.read_text(encoding="utf-8")
            assert "runtime version pin" not in text.lower()

    def test_runtime_advisories_do_not_generate_claims(self, tmp_path):
        builder = BenchmarkFixture("rt-missing", tmp_path)
        (builder
         .add_pyproject(name="test")
         .add_python_file("src/app.py", "x = 1\n"))
        builder.build()
        execute_run(tmp_path / "rt-missing")

        claims_path = tmp_path / "rt-missing" / ".ai-debt" / "claims" / "operational-claims.json"
        claims = json.loads(claims_path.read_text(encoding="utf-8"))
        for c in claims.get("claims", []):
            assert "runtime version pin" not in c.get("statement", "").lower()


# ── Regression ───────────────────────────────────────────────────────


class TestRegression:
    def test_clean_baseline_remains_quiet(self, tmp_path):
        """Clean-baseline should not have runtime-related findings."""
        builder = BenchmarkFixture("clean", tmp_path)
        (builder
         .add_requirements_txt(["flask==3.0.0", "requests==2.31.0"])
         .add_runtime_pin("python", "3.12.0")
         .add_coverage_json(92.0)
         .add_python_file("src/app.py", "def hello():\n    return 1\n"))
        builder.build()
        reg = _run_pipeline(tmp_path / "clean")

        summary = reg["summary"]
        assert summary["high"] == 0
        assert summary["critical"] == 0
        # No conflict findings
        conflict_findings = [
            f for f in reg["findings"]
            if "conflict" in f.get("title", "").lower()
        ]
        assert len(conflict_findings) == 0

    def test_runtime_conflict_evidence_metadata_shape(self, tmp_path):
        """Conflict evidence must have standardized metadata."""
        (tmp_path / ".python-version").write_text("3.11\n")
        (tmp_path / ".tool-versions").write_text("python 3.12\n")
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")

        items = _detect(tmp_path)
        conflicts = _signals(items, RUNTIME_SIGNAL_CONFLICT)
        assert len(conflicts) == 1

        meta = conflicts[0].metadata
        assert meta["signal"] == RUNTIME_SIGNAL_CONFLICT
        assert meta["runtime"] == "Python"
        assert "sources" in meta
        assert len(meta["sources"]) == 2
        for s in meta["sources"]:
            assert "source_file" in s
            assert "version" in s
            assert "constraint_kind" in s
            assert "normalized" in s
        assert meta["conflict_reason"] == "exact_vs_exact_disagreement"

    def test_runtime_missing_pin_advisory_counted_separately_in_run_history(
        self, tmp_path
    ):
        """Missing-pin advisory should be in advisory_count, not technical_debt_count."""
        builder = BenchmarkFixture("rt-adv", tmp_path)
        (builder
         .add_pyproject(name="test")
         .add_python_file("src/app.py", "x = 1\n"))
        builder.build()
        execute_run(tmp_path / "rt-adv")

        snaps = list(
            (tmp_path / "rt-adv" / ".ai-debt" / "runs").glob("*-history-snapshot.json")
        )
        assert len(snaps) >= 1
        snap = json.loads(snaps[0].read_text(encoding="utf-8"))
        assert snap["advisory_count"] >= 1
        assert snap["technical_debt_count"] < snap.get("total_findings", 999)
