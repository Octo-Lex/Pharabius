"""Regression tests for v3.4.0 modularization.

Verifies that extracting parser modules did not change any behavior:
- Coverage parsers produce identical evidence
- Dependency parsers produce identical evidence  
- Runtime parsers produce identical evidence
- io_helpers work correctly
- EvidenceBuilder moved to schemas.evidence
- scanner.py line count is under 1100
- All new modules are independently importable
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from pharabius.core.constants import (
    EVIDENCE_COVERAGE_METRIC,
    EVIDENCE_COVERAGE_REPORT,
    EVIDENCE_DEPENDENCY_SIGNAL,
    EVIDENCE_RUNTIME_VERSION_SIGNAL,
)
from pharabius.core.io_helpers import read_json, read_text
from pharabius.schemas.evidence import EvidenceBuilder, EvidenceItem, EvidenceStore


# ── S04: Module importability ─────────────────────────────────────────


class TestModuleImports:
    """Verify all extracted modules are importable."""

    def test_io_helpers_importable(self):
        from pharabius.core.io_helpers import read_json, read_text
        assert callable(read_json)
        assert callable(read_text)

    def test_coverage_parsers_importable(self):
        from pharabius.core.coverage_parsers import scan_coverage_artifact
        assert callable(scan_coverage_artifact)

    def test_dependency_parsers_importable(self):
        from pharabius.core.dependency_parsers import (
            scan_dependency_manifest,
            scan_repository_dependency_consistency,
        )
        assert callable(scan_dependency_manifest)
        assert callable(scan_repository_dependency_consistency)

    def test_runtime_parsers_importable(self):
        from pharabius.core.runtime_parsers import detect_runtime_version_pins
        assert callable(detect_runtime_version_pins)

    def test_evidence_builder_in_schemas(self):
        """EvidenceBuilder should be importable from schemas.evidence."""
        from pharabius.schemas.evidence import EvidenceBuilder
        builder = EvidenceBuilder()
        builder.add(
            type_="test",
            category="test",
            summary="test evidence",
        )
        assert len(builder.items) == 1
        assert builder.items[0].evidence_id == "EVD-000001"


# ── S04: io_helpers ───────────────────────────────────────────────────


class TestIoHelpers:
    """Verify io_helpers read_text/read_json work correctly."""

    def test_read_text_existing_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world", encoding="utf-8")
        assert read_text(f) == "hello world"

    def test_read_text_nonexistent_returns_empty(self, tmp_path):
        f = tmp_path / "nonexistent.txt"
        assert read_text(f) == ""

    def test_read_text_truncates(self, tmp_path):
        f = tmp_path / "big.txt"
        f.write_text("x" * 200, encoding="utf-8")
        result = read_text(f, max_chars=50)
        assert len(result) == 50

    def test_read_json_existing_file(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text(json.dumps({"key": "value"}), encoding="utf-8")
        assert read_json(f) == {"key": "value"}

    def test_read_json_nonexistent_returns_empty_dict(self, tmp_path):
        f = tmp_path / "nonexistent.json"
        assert read_json(f) == {}

    def test_read_json_non_dict_returns_empty_dict(self, tmp_path):
        f = tmp_path / "array.json"
        f.write_text("[1, 2, 3]", encoding="utf-8")
        assert read_json(f) == {}

    def test_read_json_malformed_returns_empty_dict(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not json at all", encoding="utf-8")
        assert read_json(f) == {}


# ── S04: Coverage parsers ─────────────────────────────────────────────


class TestCoverageParsers:
    """Verify coverage parsers produce correct evidence via extracted module."""

    def test_istanbul_coverage(self, tmp_path):
        from pharabius.core.coverage_parsers import scan_coverage_artifact

        istanbul_data = {
            "total": {
                "lines": {"pct": 85.5},
                "statements": {"pct": 80.0},
                "functions": {"pct": 75.0},
                "branches": {"pct": 60.0},
            }
        }
        f = tmp_path / "coverage.json"
        f.write_text(json.dumps(istanbul_data), encoding="utf-8")

        builder = EvidenceBuilder()
        result = scan_coverage_artifact(f, "coverage/coverage.json", "istanbul_json", builder)
        assert result is True

        reports = [e for e in builder.items if e.type == EVIDENCE_COVERAGE_REPORT]
        metrics = [e for e in builder.items if e.type == EVIDENCE_COVERAGE_METRIC]
        assert len(reports) == 1
        assert len(metrics) == 4

        line_metric = next(m for m in metrics if m.metadata["metric"] == "lines")
        assert line_metric.metadata["percent"] == 85.5

    def test_python_coverage(self, tmp_path):
        from pharabius.core.coverage_parsers import scan_coverage_artifact

        cov_data = {"totals": {"percent_covered": 92.3}}
        f = tmp_path / "coverage.json"
        f.write_text(json.dumps(cov_data), encoding="utf-8")

        builder = EvidenceBuilder()
        scan_coverage_artifact(f, "coverage.json", "python_coverage_json", builder)

        metrics = [e for e in builder.items if e.type == EVIDENCE_COVERAGE_METRIC]
        assert len(metrics) == 1
        assert metrics[0].metadata["percent"] == 92.3

    def test_lcov_coverage(self, tmp_path):
        from pharabius.core.coverage_parsers import scan_coverage_artifact

        lcov_text = "LF:100\nLH:80\nFNF:20\nFNH:15\n"
        f = tmp_path / "lcov.info"
        f.write_text(lcov_text, encoding="utf-8")

        builder = EvidenceBuilder()
        scan_coverage_artifact(f, "lcov.info", "lcov", builder)

        metrics = [e for e in builder.items if e.type == EVIDENCE_COVERAGE_METRIC]
        assert len(metrics) == 2  # lines + functions
        line_m = next(m for m in metrics if m.metadata["metric"] == "lines")
        assert line_m.metadata["percent"] == 80.0

    def test_cobertura_coverage(self, tmp_path):
        from pharabius.core.coverage_parsers import scan_coverage_artifact

        xml = '<?xml version="1.0" ?><coverage line-rate="0.82" branch-rate="0.65"></coverage>'
        f = tmp_path / "coverage.xml"
        f.write_text(xml, encoding="utf-8")

        builder = EvidenceBuilder()
        scan_coverage_artifact(f, "coverage.xml", "cobertura_xml", builder)

        metrics = [e for e in builder.items if e.type == EVIDENCE_COVERAGE_METRIC]
        assert len(metrics) == 2
        line_m = next(m for m in metrics if m.metadata["metric"] == "lines")
        assert line_m.metadata["percent"] == 82.0

    def test_jacoco_coverage(self, tmp_path):
        from pharabius.core.coverage_parsers import scan_coverage_artifact

        xml = textwrap.dedent("""\
            <?xml version="1.0" ?>
            <report>
                <counter type="LINE" missed="20" covered="80" />
                <counter type="BRANCH" missed="10" covered="30" />
            </report>
        """)
        f = tmp_path / "jacoco.xml"
        f.write_text(xml, encoding="utf-8")

        builder = EvidenceBuilder()
        scan_coverage_artifact(f, "jacoco.xml", "jacoco_xml", builder)

        metrics = [e for e in builder.items if e.type == EVIDENCE_COVERAGE_METRIC]
        assert len(metrics) == 2
        line_m = next(m for m in metrics if m.metadata["metric"] == "lines")
        assert line_m.metadata["percent"] == 80.0
        assert line_m.metadata["source"] == "report_level"


# ── S05: Dependency parsers ───────────────────────────────────────────


class TestDependencyParsers:
    """Verify dependency parsers via extracted module."""

    def test_node_unpinned(self, tmp_path):
        from pharabius.core.dependency_parsers import scan_dependency_manifest

        pkg = {"dependencies": {"lodash": "*", "express": ">=4.0.0"}}
        f = tmp_path / "package.json"
        f.write_text(json.dumps(pkg), encoding="utf-8")

        builder = EvidenceBuilder()
        result = scan_dependency_manifest(f, "package.json", builder)
        assert result is True

        dep_signals = [e for e in builder.items if e.type == EVIDENCE_DEPENDENCY_SIGNAL]
        assert len(dep_signals) == 1
        assert dep_signals[0].metadata["count"] == 2

    def test_python_unpinned(self, tmp_path):
        from pharabius.core.dependency_parsers import scan_dependency_manifest

        req = "requests\nflask>=2.0\npinned==1.0.0\n"
        f = tmp_path / "requirements.txt"
        f.write_text(req, encoding="utf-8")

        builder = EvidenceBuilder()
        result = scan_dependency_manifest(f, "requirements.txt", builder)
        assert result is True

        dep_signals = [e for e in builder.items if e.type == EVIDENCE_DEPENDENCY_SIGNAL]
        assert len(dep_signals) == 1
        assert dep_signals[0].metadata["count"] == 2  # requests + flask

    def test_unknown_manifest_returns_false(self, tmp_path):
        from pharabius.core.dependency_parsers import scan_dependency_manifest

        f = tmp_path / "Gemfile"
        f.write_text("source 'https://rubygems.org'", encoding="utf-8")

        builder = EvidenceBuilder()
        result = scan_dependency_manifest(f, "Gemfile", builder)
        assert result is False

    def test_node_lockfile_conflicts(self, tmp_path):
        from pharabius.core.dependency_parsers import scan_repository_dependency_consistency

        (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
        (tmp_path / "yarn.lock").write_text("", encoding="utf-8")

        builder = EvidenceBuilder()
        scan_repository_dependency_consistency(tmp_path, builder)

        conflicts = [e for e in builder.items if e.metadata.get("signal") == "lockfile_conflict"]
        assert len(conflicts) == 1
        assert "package-lock.json" in conflicts[0].raw_observation
        assert "yarn.lock" in conflicts[0].raw_observation

    def test_poetry_lockfile_without_manifest(self, tmp_path):
        from pharabius.core.dependency_parsers import scan_repository_dependency_consistency

        (tmp_path / "poetry.lock").write_text("", encoding="utf-8")

        builder = EvidenceBuilder()
        scan_repository_dependency_consistency(tmp_path, builder)

        signals = [e for e in builder.items if "poetry_lockfile_without_manifest" in e.raw_observation]
        assert len(signals) == 1


# ── S06: Runtime parsers ──────────────────────────────────────────────


class TestRuntimeParsers:
    """Verify runtime version pin detection via extracted module."""

    def test_python_version_file(self, tmp_path):
        from pharabius.core.runtime_parsers import detect_runtime_version_pins

        (tmp_path / ".python-version").write_text("3.11.5\n", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")

        builder = EvidenceBuilder()
        detect_runtime_version_pins(tmp_path, builder)

        pins = [e for e in builder.items if e.type == EVIDENCE_RUNTIME_VERSION_SIGNAL]
        assert len(pins) >= 1
        python_pins = [p for p in pins if p.metadata.get("runtime") == "Python"]
        assert any("3.11.5" in p.raw_observation for p in python_pins)

    def test_nvmrc(self, tmp_path):
        from pharabius.core.runtime_parsers import detect_runtime_version_pins

        (tmp_path / ".nvmrc").write_text("18.17.0\n", encoding="utf-8")
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")

        builder = EvidenceBuilder()
        detect_runtime_version_pins(tmp_path, builder)

        pins = [e for e in builder.items if e.type == EVIDENCE_RUNTIME_VERSION_SIGNAL]
        node_pins = [p for p in pins if p.metadata.get("runtime") == "Node.js"]
        assert any("18.17.0" in p.raw_observation for p in node_pins)

    def test_missing_python_pin_detected(self, tmp_path):
        from pharabius.core.runtime_parsers import detect_runtime_version_pins

        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")

        builder = EvidenceBuilder()
        detect_runtime_version_pins(tmp_path, builder)

        missing = [
            e for e in builder.items
            if "runtime_version_missing" in e.raw_observation and "Python" in e.raw_observation
        ]
        assert len(missing) == 1


# ── Scanner integration ───────────────────────────────────────────────


class TestScannerIntegration:
    """Verify scanner still works end-to-end after extraction."""

    def test_scan_repository_runs(self, tmp_path):
        from pharabius.core.scanner import scan_repository

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text(
            "def hello():\n    print('hello')\n", encoding="utf-8"
        )

        store = scan_repository(tmp_path)
        assert isinstance(store, EvidenceStore)
        assert len(store.evidence) > 0

    def test_scanner_line_count(self):
        """scanner.py should be under 1100 lines after extraction."""
        scanner_path = Path("src/pharabius/core/scanner.py")
        line_count = len(scanner_path.read_text(encoding="utf-8").splitlines())
        assert line_count < 1100, f"scanner.py has {line_count} lines, expected < 1100"

    def test_wrapper_read_text_delegates(self):
        """scanner._read_text should delegate to io_helpers.read_text."""
        from pharabius.core import scanner
        import inspect

        source = inspect.getsource(scanner._read_text)
        assert "read_text" in source
        assert len(source.strip().splitlines()) <= 4

    def test_wrapper_read_json_delegates(self):
        """scanner._read_json should delegate to io_helpers.read_json."""
        from pharabius.core import scanner
        import inspect

        source = inspect.getsource(scanner._read_json)
        assert "read_json" in source
        assert len(source.strip().splitlines()) <= 4
