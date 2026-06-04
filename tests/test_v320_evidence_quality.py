"""v3.2.0 Evidence Quality & Analyzer Depth Regression Tests.

Tests verify the specific analyzer-depth and evidence-quality improvements
from the v3.2.0 release. Zero placeholders.
"""

from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.constants import (
    EVIDENCE_BROAD_EXCEPTION,
    EVIDENCE_COVERAGE_METRIC,
    EVIDENCE_COVERAGE_REPORT,
    EVIDENCE_DEPENDENCY_SIGNAL,
    EVIDENCE_LONG_FUNCTION,
    EVIDENCE_SOURCE_FILE_SKIPPED,
    LONG_FUNCTION_LINE_THRESHOLD,
)
from pharabius.core.run_metadata import execute_run
from pharabius.core.scanner import scan_repository
from pharabius.core.traceability import compute_traceability_quality
from pharabius.schemas.claims import OperationalClaim

# ---------------------------------------------------------------------------
# S01: Shared constants module
# ---------------------------------------------------------------------------


class TestS01Constants:
    def test_constants_module_no_circular_imports(self) -> None:
        """Importing constants must not create circular dependencies."""
        from pharabius.core.constants import LARGE_FILE_LINE_THRESHOLD

        assert LARGE_FILE_LINE_THRESHOLD == 1000


# ---------------------------------------------------------------------------
# S02: max_file_size_kb
# ---------------------------------------------------------------------------


class TestS02MaxFileSize:
    def test_max_file_size_kb_skips_oversized(self, tmp_path: Path) -> None:
        big = tmp_path / "big.py"
        big.write_bytes(b"x" * (600 * 1024))  # 600 KB > 500 KB
        store = scan_repository(tmp_path, max_file_size_kb=500)
        skipped = [e for e in store.evidence if e.type == EVIDENCE_SOURCE_FILE_SKIPPED]
        assert len(skipped) >= 1
        assert skipped[0].metadata["reason"] == "file_size_limit"
        assert skipped[0].metadata["observation_strength"] == "limitation"
        assert skipped[0].metadata["completeness"] == "skipped"
        assert skipped[0].metadata["parser"] == "filesystem"
        assert skipped[0].metadata["read_mode"] == "skipped"

    def test_max_file_size_kb_allows_normal_files(self, tmp_path: Path) -> None:
        small = tmp_path / "small.py"
        small.write_text("print('hello')")
        store = scan_repository(tmp_path, max_file_size_kb=500)
        skipped = [e for e in store.evidence if e.type == EVIDENCE_SOURCE_FILE_SKIPPED]
        assert len(skipped) == 0

    def test_max_file_size_kb_none_means_no_limit(self, tmp_path: Path) -> None:
        big = tmp_path / "big.py"
        big.write_bytes(b"x" * (600 * 1024))
        store = scan_repository(tmp_path, max_file_size_kb=None)
        skipped = [e for e in store.evidence if e.type == EVIDENCE_SOURCE_FILE_SKIPPED]
        assert len(skipped) == 0


# ---------------------------------------------------------------------------
# S04: Deeper TD-CODE analyzers
# ---------------------------------------------------------------------------


class TestS04LongFunctions:
    def test_long_python_function_evidence(self, tmp_path: Path) -> None:
        src = tmp_path / "long_func.py"
        lines = ["def big_function():"]
        lines.extend([f"    x = {i}" for i in range(100)])
        src.write_text("\n".join(lines))
        store = scan_repository(tmp_path)
        long_funcs = [e for e in store.evidence if e.type == EVIDENCE_LONG_FUNCTION]
        assert len(long_funcs) >= 1
        assert long_funcs[0].metadata["function_name"] == "big_function"
        assert long_funcs[0].metadata["line_count"] >= LONG_FUNCTION_LINE_THRESHOLD
        assert long_funcs[0].metadata["language"] == "python"
        assert long_funcs[0].metadata["observation_strength"] == "heuristic"

    def test_long_function_produces_td_code(self, tmp_path: Path) -> None:
        src = tmp_path / "long_func.py"
        lines = ["def big_function():"]
        lines.extend([f"    x = {i}" for i in range(100)])
        src.write_text("\n".join(lines))
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
        execute_run(tmp_path)
        register = json.loads((tmp_path / ".ai-debt" / "debt-register.json").read_text())
        td_code = [
            f
            for f in register["findings"]
            if f["category"] == "TD-CODE" and "long function" in f["title"].lower()
        ]
        assert len(td_code) >= 1

    def test_long_function_not_detected_for_js(self, tmp_path: Path) -> None:
        """Long-function detection is Python-only for v3.2.0."""
        src = tmp_path / "long.js"
        lines = ["function bigFunction() {"]
        lines.extend([f"  var x = {i};" for i in range(100)])
        lines.append("}")
        src.write_text("\n".join(lines))
        store = scan_repository(tmp_path)
        long_funcs = [e for e in store.evidence if e.type == EVIDENCE_LONG_FUNCTION]
        assert len(long_funcs) == 0


class TestS04BroadExceptions:
    def test_broad_exception_evidence(self, tmp_path: Path) -> None:
        src = tmp_path / "exceptions.py"
        src.write_text(
            "try:\n    pass\nexcept:\n    pass\n"
            "try:\n    pass\nexcept Exception:\n    pass\n"
            "try:\n    pass\nexcept BaseException:\n    pass\n"
        )
        store = scan_repository(tmp_path)
        broad = [e for e in store.evidence if e.type == EVIDENCE_BROAD_EXCEPTION]
        assert len(broad) >= 3

    def test_broad_exception_produces_td_code(self, tmp_path: Path) -> None:
        """3+ broad exceptions in one file should produce TD-CODE finding."""
        src = tmp_path / "many_exceptions.py"
        lines: list[str] = []
        for i in range(4):
            lines.extend(["try:", f"    x = {i}", "except:", "    pass", ""])
        src.write_text("\n".join(lines))
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
        execute_run(tmp_path)
        register = json.loads((tmp_path / ".ai-debt" / "debt-register.json").read_text())
        td_code = [
            f
            for f in register["findings"]
            if f["category"] == "TD-CODE" and "exception" in f["title"].lower()
        ]
        assert len(td_code) >= 1

    def test_broad_exception_below_threshold_no_finding(self, tmp_path: Path) -> None:
        """< 3 broad exceptions should not produce TD-CODE finding."""
        src = tmp_path / "few_exceptions.py"
        src.write_text("try:\n    pass\nexcept:\n    pass\n")
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
        execute_run(tmp_path)
        register = json.loads((tmp_path / ".ai-debt" / "debt-register.json").read_text())
        td_code = [
            f
            for f in register["findings"]
            if f["category"] == "TD-CODE" and "exception" in f["title"].lower()
        ]
        assert len(td_code) == 0


# ---------------------------------------------------------------------------
# S05: Richer dependency health signals
# ---------------------------------------------------------------------------


class TestS05DependencySignals:
    def test_unpinned_node_dependency_detected(self, tmp_path: Path) -> None:
        pkg = tmp_path / "package.json"
        pkg.write_text(
            json.dumps(
                {
                    "dependencies": {
                        "lodash": "*",
                        "express": "^4.17.0",
                        "pinned-dep": "1.2.3",
                    }
                }
            )
        )
        store = scan_repository(tmp_path)
        signals = [
            e
            for e in store.evidence
            if e.type == EVIDENCE_DEPENDENCY_SIGNAL
            and e.metadata.get("signal") == "unpinned_dependency"
            and e.metadata.get("ecosystem") == "Node.js"
        ]
        assert len(signals) >= 1
        assert signals[0].metadata["observation_strength"] == "direct"

    def test_unpinned_python_dependency_detected(self, tmp_path: Path) -> None:
        req = tmp_path / "requirements.txt"
        req.write_text("requests>=2.0\nflask\npinned-pkg==1.2.3\n# comment\n")
        store = scan_repository(tmp_path)
        signals = [
            e
            for e in store.evidence
            if e.type == EVIDENCE_DEPENDENCY_SIGNAL
            and e.metadata.get("signal") == "unpinned_dependency"
            and e.metadata.get("ecosystem") == "Python"
        ]
        assert len(signals) >= 1
        examples = signals[0].metadata["examples"]
        names = [e["name"] for e in examples]
        assert "flask" in names or "requests" in names

    def test_multiple_node_lockfiles_detected(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "package-lock.json").write_text("{}")
        (tmp_path / "yarn.lock").write_text("# yarn lockfile\n")
        store = scan_repository(tmp_path)
        signals = [
            e
            for e in store.evidence
            if e.type == EVIDENCE_DEPENDENCY_SIGNAL
            and e.metadata.get("signal") == "lockfile_conflict"
        ]
        assert len(signals) >= 1


# ---------------------------------------------------------------------------
# S06: Coverage-report ingestion
# ---------------------------------------------------------------------------


class TestS06CoverageIngestion:
    def test_istanbul_coverage_parsed(self, tmp_path: Path) -> None:
        cov_dir = tmp_path / "coverage"
        cov_dir.mkdir()
        (cov_dir / "coverage-summary.json").write_text(
            json.dumps(
                {
                    "total": {
                        "lines": {"pct": 45.2},
                        "branches": {"pct": 30.1},
                        "functions": {"pct": 55.0},
                        "statements": {"pct": 48.3},
                    }
                }
            )
        )
        store = scan_repository(tmp_path)
        metrics = [e for e in store.evidence if e.type == EVIDENCE_COVERAGE_METRIC]
        assert len(metrics) >= 4
        line_metric = next(m for m in metrics if m.metadata["metric"] == "lines")
        assert line_metric.metadata["percent"] == 45.2
        assert line_metric.metadata["parser"] == "coverage_parser"

    def test_python_coverage_json_parsed(self, tmp_path: Path) -> None:
        (tmp_path / "coverage.json").write_text(
            json.dumps(
                {
                    "meta": {"version": "5.0"},
                    "totals": {
                        "covered_lines": 62,
                        "num_statements": 100,
                        "percent_covered": 62.0,
                        "missing_lines": 38,
                    },
                }
            )
        )
        store = scan_repository(tmp_path)
        metrics = [e for e in store.evidence if e.type == EVIDENCE_COVERAGE_METRIC]
        assert len(metrics) >= 1
        assert metrics[0].metadata["percent"] == 62.0
        assert metrics[0].metadata["format"] == "python_coverage_json"

    def test_lcov_coverage_parsed(self, tmp_path: Path) -> None:
        lcov_content = (
            "TN:test\n"
            "SF:src/main.py\n"
            "FN:1,10,hello\n"
            "FNDA:1,hello\n"
            "FNF:10\n"
            "FNH:8\n"
            "DA:1,1\n"
            "LF:100\n"
            "LH:62\n"
            "end_of_record\n"
        )
        (tmp_path / "lcov.info").write_text(lcov_content)
        store = scan_repository(tmp_path)
        metrics = [e for e in store.evidence if e.type == EVIDENCE_COVERAGE_METRIC]
        assert len(metrics) >= 2  # line + function
        line_m = next(m for m in metrics if m.metadata["metric"] == "lines")
        assert line_m.metadata["percent"] == 62.0
        func_m = next(m for m in metrics if m.metadata["metric"] == "functions")
        assert func_m.metadata["percent"] == 80.0

    def test_malformed_coverage_emits_limitation_not_crash(self, tmp_path: Path) -> None:
        cov_dir = tmp_path / "coverage"
        cov_dir.mkdir()
        (cov_dir / "coverage-summary.json").write_text("NOT VALID JSON{{{")
        store = scan_repository(tmp_path)
        report = [e for e in store.evidence if e.type == EVIDENCE_COVERAGE_REPORT]
        assert len(report) >= 1  # Report detected even if malformed

    def test_no_coverage_report_no_false_finding(self, tmp_path: Path) -> None:
        """Missing coverage report must NOT produce a low-coverage finding."""
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
        execute_run(tmp_path)
        register = json.loads((tmp_path / ".ai-debt" / "debt-register.json").read_text())
        low_cov = [
            f
            for f in register["findings"]
            if f["category"] == "TD-TEST" and "coverage" in f["title"].lower()
        ]
        assert len(low_cov) == 0

    def test_low_coverage_produces_td_test(self, tmp_path: Path) -> None:
        cov_dir = tmp_path / "coverage"
        cov_dir.mkdir()
        (cov_dir / "coverage-summary.json").write_text(
            json.dumps({"total": {"lines": {"pct": 25.0}, "branches": {"pct": 15.0}}})
        )
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
        execute_run(tmp_path)
        register = json.loads((tmp_path / ".ai-debt" / "debt-register.json").read_text())
        td_test = [
            f
            for f in register["findings"]
            if f["category"] == "TD-TEST" and "coverage" in f["title"].lower()
        ]
        assert len(td_test) >= 1


# ---------------------------------------------------------------------------
# S07: Traceability quality
# ---------------------------------------------------------------------------


class TestS07TraceabilityQuality:
    def test_traceability_quality_summary_generated(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
        execute_run(tmp_path)
        quality_path = tmp_path / ".ai-debt" / "traceability" / "traceability-quality.json"
        assert quality_path.exists()
        quality = json.loads(quality_path.read_text())
        assert "traceability_grade" in quality
        assert quality["traceability_grade"] in (
            "complete",
            "usable",
            "partial",
            "weak",
        )
        assert "broken_reference_count" in quality
        assert "orphan_finding_count" in quality

    def test_broken_reference_detected(self) -> None:
        """A claim referencing a non-existent finding should be counted."""
        quality = compute_traceability_quality(
            evidence_ids={"EVD-001"},
            findings=[{"id": "F-001", "evidence_ids": ["EVD-001"]}],
            claims=[
                OperationalClaim(
                    claim_id="CLM-001",
                    claim_type="behavior",
                    statement="test",
                    status="gap",
                    confidence="Low",
                    evidence_ids=["EVD-001"],
                    linked_findings=["F-001", "F-NONEXISTENT"],
                    linked_work_packages=["WP-NONEXISTENT"],
                    source="finding",
                    validation_question="Is this a broken reference test?",
                ),
            ],
            work_packages=[{"package_id": "WP-001", "linked_debt_items": ["F-001"]}],
        )
        assert quality["broken_reference_count"] >= 2

    def test_orphan_evidence_detected(self) -> None:
        """Evidence not referenced by any finding should be counted."""
        quality = compute_traceability_quality(
            evidence_ids={"EVD-001", "EVD-002", "EVD-ORPHAN"},
            findings=[{"id": "F-001", "evidence_ids": ["EVD-001", "EVD-002"]}],
            claims=[],
            work_packages=[],
        )
        assert quality["orphan_evidence_count"] == 1  # EVD-ORPHAN
