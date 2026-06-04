"""v3.9.0 — Runtime Evidence Normalization & Signal Governance.

Tests cover:
- Package imports and backward compatibility
- RuntimeEvidence IR production
- Constraint model (EXACT, RANGE, UNPINNED, MISSING, UNKNOWN)
- Conflict group model
- Policy classification
- Runtime summary in history snapshot
- Reporter runtime section
- Advisory/finding boundary regression
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from benchmarks.fixture_builder import BenchmarkFixture

from pharabius.core.constants import (
    RUNTIME_SIGNAL_CONFLICT,
    RUNTIME_SIGNAL_FROM_CI,
    RUNTIME_SIGNAL_MISSING,
    RUNTIME_SIGNAL_PINNED,
)
from pharabius.core.run_metadata import execute_run
from pharabius.core.runtime import detect_runtime_version_pins
from pharabius.core.runtime.conflict import detect_conflicts
from pharabius.core.runtime.constraints import parse_constraint
from pharabius.core.runtime.detector import (
    detect_java_sources,
    detect_node_sources,
    detect_python_sources,
    detect_ruby_sources,
)
from pharabius.core.runtime.models import (
    Confidence,
    RuntimeConflictGroup,
    RuntimeConstraint,
    RuntimeConstraintKind,
    RuntimeEcosystem,
    RuntimeEvidence,
    RuntimeSignalClassification,
    RuntimeSourceGrade,
    RuntimeSourceType,
)
from pharabius.core.runtime.policy import (
    classify_conflict,
    classify_evidence,
    classify_missing_pin,
)
from pharabius.core.runtime_parsers import (
    detect_runtime_version_pins as compat_detect,
)
from pharabius.schemas.evidence import EvidenceBuilder

# ── S01: Package imports ────────────────────────────────────────────


class TestPackageImports:
    def test_canonical_import_works(self):
        from pharabius.core.runtime import detect_runtime_version_pins

        assert callable(detect_runtime_version_pins)

    def test_backward_compat_import_works(self):
        from pharabius.core.runtime_parsers import detect_runtime_version_pins

        assert callable(detect_runtime_version_pins)

    def test_same_function(self):
        from pharabius.core.runtime import detect_runtime_version_pins as canonical
        from pharabius.core.runtime_parsers import detect_runtime_version_pins as compat

        assert canonical is compat


# ── S02: RuntimeEvidence IR ─────────────────────────────────────────


class TestRuntimeEvidenceIR:
    def test_python_sources_produce_runtime_evidence(self, tmp_path):
        (tmp_path / ".python-version").write_text("3.12\n")
        (tmp_path / "pyproject.toml").write_text("[project]\n")

        evidence = detect_python_sources(tmp_path)
        assert len(evidence) >= 1
        assert all(isinstance(e, RuntimeEvidence) for e in evidence)
        assert all(e.ecosystem == RuntimeEcosystem.PYTHON for e in evidence)
        assert all(e.runtime_evidence_id for e in evidence)

    def test_node_sources_produce_runtime_evidence(self, tmp_path):
        (tmp_path / ".nvmrc").write_text("20\n")
        evidence = detect_node_sources(tmp_path)
        assert len(evidence) >= 1
        assert all(isinstance(e, RuntimeEvidence) for e in evidence)
        assert all(e.ecosystem == RuntimeEcosystem.NODE for e in evidence)

    def test_ruby_sources_produce_runtime_evidence(self, tmp_path):
        (tmp_path / ".ruby-version").write_text("3.3.0\n")
        (tmp_path / "Gemfile").write_text('source "https://rubygems.org"\nruby "3.3.0"\n')
        evidence = detect_ruby_sources(tmp_path)
        assert len(evidence) >= 1
        assert all(e.ecosystem == RuntimeEcosystem.RUBY for e in evidence)

    def test_java_sources_produce_runtime_evidence(self, tmp_path):
        (tmp_path / ".java-version").write_text("17\n")
        evidence = detect_java_sources(tmp_path)
        assert len(evidence) >= 1
        assert all(e.ecosystem == RuntimeEcosystem.JAVA for e in evidence)


# ── S03: Constraint model ───────────────────────────────────────────


class TestConstraintModel:
    def test_exact_constraint(self):
        c = parse_constraint("Python", "3.12")
        assert c.kind == RuntimeConstraintKind.EXACT
        assert c.value == "3.12"

    def test_range_constraint(self):
        c = parse_constraint("Python", ">=3.11")
        assert c.kind == RuntimeConstraintKind.RANGE
        assert c.lower_bound == "3.11"

    def test_unknown_constraint(self):
        c = parse_constraint("Python", "some-nonsense")
        assert c.kind == RuntimeConstraintKind.UNKNOWN

    def test_wildcard_x_constraint(self):
        c = parse_constraint("Node.js", "18.x")
        assert c.kind == RuntimeConstraintKind.RANGE
        assert c.lower_bound == "18"
        assert c.upper_bound == "19"

    def test_node_exact_by_major(self):
        c = parse_constraint("Node.js", "20")
        assert c.kind == RuntimeConstraintKind.EXACT
        assert c.value == "20"


# ── S04: Conflict group model ───────────────────────────────────────


class TestConflictGroup:
    def test_exact_exact_produces_conflict_group(self, tmp_path):
        (tmp_path / ".python-version").write_text("3.11\n")
        (tmp_path / ".tool-versions").write_text("python 3.12\n")
        (tmp_path / "pyproject.toml").write_text("[project]\n")

        evidence = detect_python_sources(tmp_path)
        from pharabius.core.runtime.tool_versions import detect_tool_versions_sources

        evidence.extend(detect_tool_versions_sources(tmp_path))

        conflicts = detect_conflicts(evidence)
        assert len(conflicts) >= 1
        assert isinstance(conflicts[0], RuntimeConflictGroup)
        assert conflicts[0].conflict_kind.value == "exact_vs_exact_disagreement"

    def test_conflict_group_has_explanation(self, tmp_path):
        (tmp_path / ".python-version").write_text("3.11\n")
        (tmp_path / ".tool-versions").write_text("python 3.12\n")
        (tmp_path / "pyproject.toml").write_text("[project]\n")

        evidence = detect_python_sources(tmp_path)
        from pharabius.core.runtime.tool_versions import detect_tool_versions_sources

        evidence.extend(detect_tool_versions_sources(tmp_path))

        conflicts = detect_conflicts(evidence)
        assert len(conflicts) >= 1
        assert conflicts[0].explanation
        assert "3.11" in conflicts[0].explanation or "3.12" in conflicts[0].explanation


# ── S05: Policy classification ──────────────────────────────────────


class TestPolicyClassification:
    def test_policy_classifies_conflict_as_finding(self):
        from pharabius.core.runtime.models import RuntimeConflictKind

        group = RuntimeConflictGroup(
            ecosystem=RuntimeEcosystem.PYTHON,
            runtime_name="Python",
            conflict_kind=RuntimeConflictKind.EXACT_EXACT_MISMATCH,
            evidence=[],
            explanation="test",
        )
        action = classify_conflict(group)
        assert action.classification == RuntimeSignalClassification.FINDING
        assert action.issue_type == "technical_debt"

    def test_policy_classifies_missing_pin_as_advisory(self):
        action = classify_missing_pin([])
        assert action.classification == RuntimeSignalClassification.ADVISORY
        assert action.issue_type == "advisory"

    def test_policy_classifies_pinned_as_informational(self):
        ev = RuntimeEvidence(
            runtime_evidence_id="test",
            ecosystem=RuntimeEcosystem.PYTHON,
            runtime_name="Python",
            constraint=RuntimeConstraint(kind=RuntimeConstraintKind.EXACT, value="3.12"),
            source_type=RuntimeSourceType.VERSION_FILE,
            source_path=".python-version",
            source_grade=RuntimeSourceGrade.VERSION_FILE,
        )
        result = classify_evidence(ev)
        assert result == RuntimeSignalClassification.INFORMATIONAL


# ── S06: Runtime summary ────────────────────────────────────────────


class TestRuntimeSummary:
    def test_runtime_summary_in_history_snapshot(self, tmp_path):
        builder = BenchmarkFixture("rt-test", tmp_path)
        (
            builder.add_pyproject(name="test")
            .add_runtime_pin("python", "3.12")
            .add_python_file("src/app.py", "x = 1\n")
        )
        builder.build()
        execute_run(tmp_path / "rt-test")

        snaps = list((tmp_path / "rt-test" / ".ai-debt" / "runs").glob("*-history-snapshot.json"))
        assert len(snaps) >= 1
        snap = json.loads(snaps[0].read_text(encoding="utf-8"))
        assert "runtime_evidence_summary" in snap
        summary = snap["runtime_evidence_summary"]
        assert "ecosystems_detected" in summary
        assert "Python" in summary["ecosystems_with_pins"]

    def test_reporter_runtime_section(self, tmp_path):
        builder = BenchmarkFixture("rt-report", tmp_path)
        (
            builder.add_pyproject(name="test")
            .add_runtime_pin("python", "3.12")
            .add_python_file("src/app.py", "x = 1\n")
        )
        builder.build()
        execute_run(tmp_path / "rt-report")

        report = tmp_path / "rt-report" / ".ai-debt" / "reports" / "foundation-audit-report.md"
        text = report.read_text(encoding="utf-8")
        assert "Runtime Reproducibility" in text


# ── S07: Regression ──────────────────────────────────────────────────


class TestRegression:
    def test_clean_baseline_remains_quiet(self, tmp_path):
        builder = BenchmarkFixture("clean", tmp_path)
        (
            builder.add_requirements_txt(["flask==3.0.0"])
            .add_runtime_pin("python", "3.12.0")
            .add_coverage_json(92.0)
            .add_python_file("src/app.py", "def hello():\n    return 1\n")
        )
        builder.build()
        execute_run(tmp_path / "clean")
        reg_path = tmp_path / "clean" / ".ai-debt" / "debt-register.json"
        assert reg_path.exists()
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
        assert reg["summary"]["high"] == 0
        assert reg["summary"]["critical"] == 0

    def test_missing_pin_does_not_generate_work_packages(self, tmp_path):
        builder = BenchmarkFixture("rt-missing", tmp_path)
        (builder.add_pyproject(name="test").add_python_file("src/app.py", "x = 1\n"))
        builder.build()
        execute_run(tmp_path / "rt-missing")

        wp_dir = tmp_path / "rt-missing" / ".ai-debt" / "work-packages"
        wp_files = list(wp_dir.glob("WP-*.md"))
        for wp in wp_files:
            text = wp.read_text(encoding="utf-8")
            assert "runtime version pin" not in text.lower()

    def test_conflict_does_generate_work_package(self, tmp_path):
        builder = BenchmarkFixture("rt-conflict", tmp_path)
        (
            builder.add_file(".python-version", "3.11\n")
            .add_file(".tool-versions", "python 3.12\n")
            .add_file("pyproject.toml", "[project]\nname='x'\n")
        )
        builder.build()
        execute_run(tmp_path / "rt-conflict")

        wp_dir = tmp_path / "rt-conflict" / ".ai-debt" / "work-packages"
        wp_files = list(wp_dir.glob("WP-*.md"))
        assert len(wp_files) >= 1
        # At least one WP should be about the conflict
        conflict_wp = [
            wp for wp in wp_files if "conflict" in wp.read_text(encoding="utf-8").lower()
        ]
        assert len(conflict_wp) >= 1
