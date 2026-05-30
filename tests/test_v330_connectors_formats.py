"""v3.3.0 Evidence Connectors & Format Expansion Regression Tests.

Tests verify path normalization, coverage format expansion, dependency
signal deepening, runtime version pinning, and traceability trend.
Zero placeholders.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pharabius.core.constants import (
    EVIDENCE_BROAD_EXCEPTION,
    EVIDENCE_COVERAGE_METRIC,
    EVIDENCE_COVERAGE_REPORT,
    EVIDENCE_DEPENDENCY_SIGNAL,
    EVIDENCE_RUNTIME_VERSION_SIGNAL,
)
from pharabius.core.dependency_utils import classify_python_specifier
from pharabius.core.path_utils import (
    normalize_repo_path,
    path_matches_exact_or_suffix,
    path_matches_root_pattern,
    relative_repo_path,
)
from pharabius.core.run_metadata import execute_run
from pharabius.core.scanner import scan_repository
from pharabius.core.traceability import (
    append_quality_snapshot,
    compute_traceability_quality_trend,
    load_quality_history,
)


# ---------------------------------------------------------------------------
# S01: Path normalization
# ---------------------------------------------------------------------------


class TestS01PathNormalization:
    def test_windows_backslash_to_posix(self) -> None:
        assert normalize_repo_path("a\\b\\c.txt") == "a/b/c.txt"

    def test_coverage_pattern_matches_backslash_path(self) -> None:
        assert path_matches_exact_or_suffix(
            "coverage\\coverage-summary.json",
            "coverage/coverage-summary.json",
        )

    def test_relative_repo_path_uses_posix(self, tmp_path: Path) -> None:
        child = tmp_path / "sub" / "file.py"
        child.parent.mkdir(parents=True)
        child.write_text("pass")
        result = relative_repo_path(child, tmp_path)
        assert "\\" not in result
        assert result == "sub/file.py"

    def test_empty_and_dot_normalize(self) -> None:
        assert normalize_repo_path("") == "."
        assert normalize_repo_path(".") == "."

    def test_root_pattern_rejects_subdirectory_match(self) -> None:
        assert not path_matches_root_pattern("sub/package.json", "package.json")

    def test_suffix_pattern_accepts_subdirectory_match(self) -> None:
        assert path_matches_exact_or_suffix("sub/lcov.info", "lcov.info")

    def test_directory_pattern_does_not_match_same_filename_elsewhere(
        self,
    ) -> None:
        assert not path_matches_exact_or_suffix(
            "other/jacoco.xml",
            "target/site/jacoco/jacoco.xml",
        )


# ---------------------------------------------------------------------------
# S02: Cobertura XML coverage ingestion
# ---------------------------------------------------------------------------


class TestS02Cobertura:
    def test_cobertura_xml_line_branch_parsed(self, tmp_path: Path) -> None:
        xml = (
            '<?xml version="1.0" ?>'
            '<coverage line-rate="0.82" branch-rate="0.64">'
            "<packages/>"
            "</coverage>"
        )
        (tmp_path / "coverage.xml").write_text(xml)
        store = scan_repository(tmp_path)
        metrics = [e for e in store.evidence if e.type == EVIDENCE_COVERAGE_METRIC]
        assert len(metrics) >= 2
        line_m = next(m for m in metrics if m.metadata["metric"] == "lines")
        assert line_m.metadata["percent"] == 82.0
        branch_m = next(m for m in metrics if m.metadata["metric"] == "branches")
        assert branch_m.metadata["percent"] == 64.0

    def test_cobertura_malformed_xml_limitation(self, tmp_path: Path) -> None:
        (tmp_path / "coverage.xml").write_text("NOT VALID XML {{{")
        store = scan_repository(tmp_path)
        report = [e for e in store.evidence if e.type == EVIDENCE_COVERAGE_REPORT]
        assert len(report) >= 1  # Report detected even if malformed

    def test_cobertura_missing_no_finding(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
        execute_run(tmp_path)
        register = json.loads(
            (tmp_path / ".ai-debt" / "debt-register.json").read_text()
        )
        cov_findings = [
            f
            for f in register["findings"]
            if f["category"] == "TD-TEST" and "coverage" in f["title"].lower()
        ]
        assert len(cov_findings) == 0

    def test_cobertura_low_coverage_triggers_td_test(self, tmp_path: Path) -> None:
        xml = (
            '<?xml version="1.0" ?>'
            '<coverage line-rate="0.25" branch-rate="0.15">'
            "<packages/>"
            "</coverage>"
        )
        (tmp_path / "coverage.xml").write_text(xml)
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
        execute_run(tmp_path)
        register = json.loads(
            (tmp_path / ".ai-debt" / "debt-register.json").read_text()
        )
        td_test = [
            f
            for f in register["findings"]
            if f["category"] == "TD-TEST" and "coverage" in f["title"].lower()
        ]
        assert len(td_test) >= 1


# ---------------------------------------------------------------------------
# S03: JaCoCo XML coverage ingestion
# ---------------------------------------------------------------------------


class TestS03JaCoCo:
    def test_jacoco_line_branch_method_parsed(self, tmp_path: Path) -> None:
        xml = (
            '<?xml version="1.0" ?>'
            "<report>"
            '<counter type="LINE" missed="20" covered="80"/>'
            '<counter type="BRANCH" missed="10" covered="40"/>'
            '<counter type="METHOD" missed="5" covered="45"/>'
            "</report>"
        )
        (tmp_path / "jacoco.xml").write_text(xml)
        store = scan_repository(tmp_path)
        metrics = [e for e in store.evidence if e.type == EVIDENCE_COVERAGE_METRIC]
        assert len(metrics) >= 3
        line_m = next(m for m in metrics if m.metadata["metric"] == "lines")
        assert line_m.metadata["percent"] == 80.0
        branch_m = next(m for m in metrics if m.metadata["metric"] == "branches")
        assert branch_m.metadata["percent"] == 80.0
        method_m = next(m for m in metrics if m.metadata["metric"] == "methods")
        assert method_m.metadata["percent"] == 90.0

    def test_jacoco_malformed_xml_limitation(self, tmp_path: Path) -> None:
        (tmp_path / "jacoco.xml").write_text("BROKEN XML <<<")
        store = scan_repository(tmp_path)
        report = [e for e in store.evidence if e.type == EVIDENCE_COVERAGE_REPORT]
        assert len(report) >= 1

    def test_jacoco_prefers_report_level_counters(self, tmp_path: Path) -> None:
        """Report-level counters present -> package counters ignored."""
        xml = (
            '<?xml version="1.0" ?>'
            "<report>"
            '<counter type="LINE" missed="10" covered="90"/>'
            "<package name=\"com/example\">"
            '<counter type="LINE" missed="50" covered="50"/>'
            "</package>"
            "</report>"
        )
        (tmp_path / "jacoco.xml").write_text(xml)
        store = scan_repository(tmp_path)
        metrics = [e for e in store.evidence if e.type == EVIDENCE_COVERAGE_METRIC]
        line_m = next(m for m in metrics if m.metadata["metric"] == "lines")
        assert line_m.metadata["percent"] == 90.0  # Report-level, not package
        assert line_m.metadata["source"] == "report_level"

    def test_jacoco_falls_back_to_package_level(self, tmp_path: Path) -> None:
        """No report counters -> package counters aggregated."""
        xml = (
            '<?xml version="1.0" ?>'
            "<report>"
            "<package name=\"com/example\">"
            '<counter type="LINE" missed="20" covered="80"/>'
            "</package>"
            "</report>"
        )
        (tmp_path / "jacoco.xml").write_text(xml)
        store = scan_repository(tmp_path)
        metrics = [e for e in store.evidence if e.type == EVIDENCE_COVERAGE_METRIC]
        line_m = next(m for m in metrics if m.metadata["metric"] == "lines")
        assert line_m.metadata["percent"] == 80.0
        assert line_m.metadata["source"] == "package_level"


# ---------------------------------------------------------------------------
# S04: pyproject.toml dependency parsing
# ---------------------------------------------------------------------------


class TestS04PyprojectDeps:
    def test_pyproject_pep621_dependencies_parsed(self, tmp_path: Path) -> None:
        pyproject = """
[project]
name = "myapp"
dependencies = [
    "requests>=2.0",
    "flask",
    "pinned-pkg==1.2.3",
]
"""
        (tmp_path / "pyproject.toml").write_text(pyproject)
        store = scan_repository(tmp_path)
        signals = [
            e
            for e in store.evidence
            if e.type == EVIDENCE_DEPENDENCY_SIGNAL
            and e.metadata.get("signal") == "unpinned_dependency"
            and "pyproject" in str(e.location.file)
        ]
        assert len(signals) >= 1
        names = [ex["name"] for ex in signals[0].metadata["examples"]]
        assert "flask" in names or "requests" in names

    def test_pyproject_poetry_dependencies_parsed(self, tmp_path: Path) -> None:
        pyproject = """
[tool.poetry]
name = "myapp"
[tool.poetry.dependencies]
python = "^3.11"
requests = "^2.31"
pytest = "*"
pinned = "1.2.3"
"""
        (tmp_path / "pyproject.toml").write_text(pyproject)
        store = scan_repository(tmp_path)
        signals = [
            e
            for e in store.evidence
            if e.type == EVIDENCE_DEPENDENCY_SIGNAL
            and e.metadata.get("signal") == "unpinned_dependency"
        ]
        assert len(signals) >= 1
        names = [ex["name"] for ex in signals[0].metadata["examples"]]
        assert "requests" in names or "pytest" in names

    def test_pyproject_optional_groups_parsed(self, tmp_path: Path) -> None:
        pyproject = """
[project]
name = "myapp"
[project.optional-dependencies]
dev = ["pytest>=7.0"]
"""
        (tmp_path / "pyproject.toml").write_text(pyproject)
        store = scan_repository(tmp_path)
        signals = [
            e
            for e in store.evidence
            if e.type == EVIDENCE_DEPENDENCY_SIGNAL
            and e.metadata.get("signal") == "unpinned_dependency"
        ]
        assert len(signals) >= 1

    def test_malformed_pyproject_emits_parse_failure(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("NOT VALID TOML [[[\n")
        store = scan_repository(tmp_path)
        failures = [
            e
            for e in store.evidence
            if e.type == EVIDENCE_DEPENDENCY_SIGNAL
            and e.metadata.get("signal") == "dependency_manifest_parse_failure"
        ]
        assert len(failures) >= 1
        assert failures[0].metadata["manifest"] == "pyproject.toml"


# ---------------------------------------------------------------------------
# S04: classify_python_specifier consistency (parametrized)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "specifier,source_format,expected",
    [
        ("requests==2.31.0", "pep508", "pinned"),
        ("requests===2.31.0", "pep508", "pinned"),
        ("package @ file://...", "pep508", "pinned"),
        ("requests", "pep508", "broad"),
        ("requests>=2.0", "pep508", "broad"),
        ("requests~=2.0", "pep508", "broad"),
        ("requests<3", "pep508", "broad"),
        ("requests>=2,<3", "pep508", "broad"),
        ("*", "poetry", "broad"),
        ("^3.11", "poetry", "broad"),
        ("~2.0", "poetry", "broad"),
        ("1.2.3", "poetry", "pinned"),
        ("*", "pipfile", "broad"),
        ("==1.2.3", "pipfile", "pinned"),
    ],
)
def test_classify_python_specifier_consistency(
    specifier: str, source_format: str, expected: str
) -> None:
    assert classify_python_specifier(specifier, source_format) == expected


# ---------------------------------------------------------------------------
# S05: Poetry/Pipfile dependency signals
# ---------------------------------------------------------------------------


class TestS05PoetryPipfile:
    def test_pipfile_unpinned_deps(self, tmp_path: Path) -> None:
        pipfile = """
[packages]
flask = "*"
requests = "==2.31.0"

[dev-packages]
pytest = ">=7.0"
"""
        (tmp_path / "Pipfile").write_text(pipfile)
        store = scan_repository(tmp_path)
        signals = [
            e
            for e in store.evidence
            if e.type == EVIDENCE_DEPENDENCY_SIGNAL
            and e.metadata.get("signal") == "unpinned_dependency"
            and "Pipfile" in str(e.location.file)
        ]
        assert len(signals) >= 1
        names = [ex["name"] for ex in signals[0].metadata["examples"]]
        assert "flask" in names or "pytest" in names

    def test_pipfile_without_lockfile(self, tmp_path: Path) -> None:
        (tmp_path / "Pipfile").write_text("[packages]\nflask = '*'\n")
        store = scan_repository(tmp_path)
        signals = [
            e
            for e in store.evidence
            if e.type == EVIDENCE_DEPENDENCY_SIGNAL
            and e.metadata.get("signal") == "pipfile_without_lockfile"
        ]
        assert len(signals) >= 1

    def test_poetry_manifest_without_lockfile(self, tmp_path: Path) -> None:
        pyproject = """
[tool.poetry]
name = "myapp"
[tool.poetry.dependencies]
python = "^3.11"
"""
        (tmp_path / "pyproject.toml").write_text(pyproject)
        store = scan_repository(tmp_path)
        signals = [
            e
            for e in store.evidence
            if e.type == EVIDENCE_DEPENDENCY_SIGNAL
            and e.metadata.get("signal") == "poetry_manifest_without_lockfile"
        ]
        assert len(signals) >= 1

    def test_poetry_lock_without_pyproject_emits_signal(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "poetry.lock").write_text("# poetry lockfile\n")
        store = scan_repository(tmp_path)
        signals = [
            e
            for e in store.evidence
            if e.type == EVIDENCE_DEPENDENCY_SIGNAL
            and e.metadata.get("signal") == "poetry_lockfile_without_manifest"
        ]
        assert len(signals) >= 1

    def test_malformed_pipfile_emits_parse_failure(self, tmp_path: Path) -> None:
        (tmp_path / "Pipfile").write_text("NOT VALID TOML [[[\n")
        store = scan_repository(tmp_path)
        failures = [
            e
            for e in store.evidence
            if e.type == EVIDENCE_DEPENDENCY_SIGNAL
            and e.metadata.get("signal") == "dependency_manifest_parse_failure"
            and e.metadata.get("manifest") == "Pipfile"
        ]
        assert len(failures) >= 1


# ---------------------------------------------------------------------------
# S06: Runtime version pinning
# ---------------------------------------------------------------------------


class TestS06RuntimePinning:
    def test_nvmrc_runtime_pin_detected(self, tmp_path: Path) -> None:
        (tmp_path / ".nvmrc").write_text("18")
        (tmp_path / "package.json").write_text("{}")
        store = scan_repository(tmp_path)
        signals = [
            e
            for e in store.evidence
            if e.type == EVIDENCE_RUNTIME_VERSION_SIGNAL
            and e.metadata.get("signal") == "runtime_version_pinned"
            and e.metadata.get("runtime") == "Node.js"
        ]
        assert len(signals) >= 1
        assert signals[0].metadata["version"] == "18"

    def test_python_version_pin_detected(self, tmp_path: Path) -> None:
        (tmp_path / ".python-version").write_text("3.11")
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
        store = scan_repository(tmp_path)
        signals = [
            e
            for e in store.evidence
            if e.type == EVIDENCE_RUNTIME_VERSION_SIGNAL
            and e.metadata.get("signal") == "runtime_version_pinned"
            and e.metadata.get("runtime") == "Python"
        ]
        assert len(signals) >= 1
        assert signals[0].metadata["version"] == "3.11"

    def test_missing_runtime_pin_emits_conservative(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
        store = scan_repository(tmp_path)
        signals = [
            e
            for e in store.evidence
            if e.type == EVIDENCE_RUNTIME_VERSION_SIGNAL
            and e.metadata.get("signal") == "runtime_version_missing"
        ]
        assert len(signals) >= 1
        assert signals[0].metadata["runtime"] == "Python"

    def test_tool_versions_multi_runtime(self, tmp_path: Path) -> None:
        (tmp_path / ".tool-versions").write_text("python 3.11.4\nnodejs 18.17.0\n")
        (tmp_path / "package.json").write_text("{}")
        store = scan_repository(tmp_path)
        pinned = [
            e
            for e in store.evidence
            if e.type == EVIDENCE_RUNTIME_VERSION_SIGNAL
            and e.metadata.get("signal") == "runtime_version_pinned"
        ]
        runtimes = {s.metadata["runtime"] for s in pinned}
        assert "Python" in runtimes
        assert "Node.js" in runtimes

    def test_tool_versions_detects_ruby_java_v380(
        self, tmp_path: Path
    ) -> None:
        """v3.8.0: .tool-versions now detects Ruby and Java runtime entries."""
        (tmp_path / ".tool-versions").write_text(
            "ruby 3.2.2\njava temurin-17.0.8\n"
        )
        store = scan_repository(tmp_path)
        pinned = [
            e
            for e in store.evidence
            if e.type == EVIDENCE_RUNTIME_VERSION_SIGNAL
            and e.metadata.get("signal") == "runtime_version_pinned"
        ]
        runtimes = {s.metadata["runtime"] for s in pinned}
        assert "Ruby" in runtimes
        assert "Java" in runtimes


# ---------------------------------------------------------------------------
# S07: Traceability quality trend
# ---------------------------------------------------------------------------


class TestS07TraceabilityTrend:
    def test_trend_insufficient_with_one_snapshot(self) -> None:
        trend = compute_traceability_quality_trend(
            [{"traceability_grade": "usable", "broken_reference_count": 0}]
        )
        assert trend["trajectory"] == "insufficient_data"
        assert trend["snapshot_count"] == 1

    def test_trend_detects_grade_drop(self) -> None:
        trend = compute_traceability_quality_trend(
            [
                {"traceability_grade": "usable", "broken_reference_count": 0},
                {"traceability_grade": "partial", "broken_reference_count": 0},
            ]
        )
        assert trend["trajectory"] == "worsening"
        assert trend["baseline_grade"] == "usable"
        assert trend["latest_grade"] == "partial"

    def test_trend_detects_broken_reference_increase(self) -> None:
        trend = compute_traceability_quality_trend(
            [
                {"traceability_grade": "usable", "broken_reference_count": 0},
                {"traceability_grade": "usable", "broken_reference_count": 3},
            ]
        )
        assert trend["trajectory"] == "worsening"

    def test_traceability_history_appends_snapshot(
        self, tmp_path: Path
    ) -> None:
        from pharabius.core.traceability import append_quality_snapshot

        append_quality_snapshot(
            tmp_path,
            "RUN-001",
            {"traceability_grade": "partial", "broken_reference_count": 2},
        )
        append_quality_snapshot(
            tmp_path,
            "RUN-002",
            {"traceability_grade": "usable", "broken_reference_count": 0},
        )
        history = load_quality_history(tmp_path)
        assert len(history) == 2
        assert history[0]["run_id"] == "RUN-001"
        assert history[1]["run_id"] == "RUN-002"
