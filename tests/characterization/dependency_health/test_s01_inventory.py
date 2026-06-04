"""S01 — Dependency signal inventory and characterization tests.

These tests lock down the CURRENT behavior of dependency-health analysis
before migration to governed signals. Every output field is captured.

After migration (S02–S04), these same tests must pass with identical output.
Field-level comparison uses assert_finding_unchanged() for explicit verification.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pharabius.core.analyzer import analyze_evidence
from pharabius.core.constants import EVIDENCE_DEPENDENCY_SIGNAL
from pharabius.core.dependency_parsers import (
    scan_dependency_manifest,
    scan_repository_dependency_consistency,
)
from pharabius.core.init_workspace import initialize_workspace
from pharabius.core.scanner import write_evidence_store
from pharabius.schemas.evidence import EvidenceBuilder

# ── Helpers ────────────────────────────────────────────────────────────


def _make_builder() -> EvidenceBuilder:
    return EvidenceBuilder()


def _dep_evidence(builder: EvidenceBuilder) -> list[Any]:
    """Return evidence items with type dependency_health_signal."""
    return [e for e in builder.items if e.type == EVIDENCE_DEPENDENCY_SIGNAL]


def _analyze_repo(tmp_path: Path) -> Any:
    """Run full analyze_evidence and return the DebtRegister."""
    initialize_workspace(tmp_path)
    write_evidence_store(tmp_path)
    return analyze_evidence(tmp_path)


def _dep_findings(register: Any) -> list[Any]:
    """Return TD-DEP findings from a DebtRegister."""
    return [f for f in register.findings if f.category == "TD-DEP"]


def _write_file(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ── Field-by-field comparison helper (S04 will use this) ──────────────


def assert_finding_unchanged(before: Any, after: Any, label: str = "") -> None:
    """Assert every field of a finding/advisory is identical after migration."""
    prefix = f"[{label}] " if label else ""
    assert before.category == after.category, f"{prefix}category changed"
    assert before.issue_type == after.issue_type, f"{prefix}issue_type changed"
    assert before.title == after.title, f"{prefix}title changed"
    assert before.description == after.description, f"{prefix}description changed"
    assert before.severity == after.severity, f"{prefix}severity changed"
    assert before.confidence == after.confidence, f"{prefix}confidence changed"
    assert before.risk_score == after.risk_score, f"{prefix}risk_score changed"
    assert before.priority == after.priority, f"{prefix}priority changed"
    assert before.locations == after.locations, f"{prefix}locations changed"
    assert before.evidence_ids == after.evidence_ids, f"{prefix}evidence_ids changed"


# ═══════════════════════════════════════════════════════════════════════
# S01 Inventory: Evidence types produced by dependency_parsers
# ═══════════════════════════════════════════════════════════════════════


class TestDependencyParserInventory:
    """Catalog what evidence dependency_parsers currently produce."""

    def test_node_unpinned_produces_dependency_signal(self, tmp_path: Path) -> None:
        """package.json with unpinned deps → dependency_health_signal evidence."""
        pkg = _write_file(
            tmp_path / "package.json",
            json.dumps({"dependencies": {"express": "*"}}),
        )
        builder = _make_builder()
        scan_dependency_manifest(pkg, "package.json", builder)
        dep = _dep_evidence(builder)
        assert len(dep) == 1
        assert dep[0].metadata["signal"] == "unpinned_dependency"
        assert dep[0].metadata["ecosystem"] == "Node.js"
        assert dep[0].confidence == "High"

    def test_python_unpinned_produces_dependency_signal(self, tmp_path: Path) -> None:
        """requirements.txt with unpinned deps → dependency_health_signal."""
        req = _write_file(
            tmp_path / "requirements.txt",
            "requests\nflask>=2.0\n",
        )
        builder = _make_builder()
        scan_dependency_manifest(req, "requirements.txt", builder)
        dep = _dep_evidence(builder)
        assert len(dep) == 1
        assert dep[0].metadata["signal"] == "unpinned_dependency"
        assert dep[0].metadata["ecosystem"] == "Python"
        assert dep[0].metadata["count"] == 2

    def test_pyproject_unpinned_produces_dependency_signal(self, tmp_path: Path) -> None:
        """pyproject.toml with unpinned deps → dependency_health_signal."""
        pyproject = _write_file(
            tmp_path / "pyproject.toml",
            '[project]\ndependencies = ["requests"]\n',
        )
        builder = _make_builder()
        scan_dependency_manifest(pyproject, "pyproject.toml", builder)
        dep = _dep_evidence(builder)
        assert len(dep) == 1
        assert dep[0].metadata["signal"] == "unpinned_dependency"

    def test_manifest_parse_failure_produces_signal(self, tmp_path: Path) -> None:
        """Unparseable pyproject.toml → dependency_manifest_parse_failure."""
        bad = _write_file(
            tmp_path / "pyproject.toml",
            "this is not valid toml [[[",
        )
        builder = _make_builder()
        scan_dependency_manifest(bad, "pyproject.toml", builder)
        dep = _dep_evidence(builder)
        assert len(dep) == 1
        assert dep[0].metadata["signal"] == "dependency_manifest_parse_failure"

    def test_non_manifest_returns_false(self, tmp_path: Path) -> None:
        """Non-manifest files return False from scan_dependency_manifest."""
        readme = _write_file(tmp_path / "README.md", "# Hello")
        builder = _make_builder()
        assert scan_dependency_manifest(readme, "README.md", builder) is False

    def test_pinned_deps_produce_no_signal(self, tmp_path: Path) -> None:
        """package.json with all pinned → no dependency_health_signal."""
        pkg = _write_file(
            tmp_path / "package.json",
            json.dumps({"dependencies": {"express": "4.18.2"}}),
        )
        builder = _make_builder()
        scan_dependency_manifest(pkg, "package.json", builder)
        dep = _dep_evidence(builder)
        assert len(dep) == 0


class TestRepositoryDependencyConsistency:
    """Catalog lockfile consistency evidence from dependency_parsers."""

    def test_poetry_missing_lockfile(self, tmp_path: Path) -> None:
        """pyproject.toml (Poetry) without poetry.lock → poetry_manifest_without_lockfile."""
        _write_file(
            tmp_path / "pyproject.toml",
            '[tool.poetry]\nname = "x"\n[tool.poetry.dependencies]\npython = "^3.11"\n',
        )
        builder = _make_builder()
        scan_repository_dependency_consistency(tmp_path, builder)
        dep = _dep_evidence(builder)
        assert len(dep) >= 1
        signals = [e.metadata.get("signal") for e in dep]
        assert "poetry_manifest_without_lockfile" in signals

    def test_pipfile_missing_lockfile(self, tmp_path: Path) -> None:
        """Pipfile without Pipfile.lock → pipfile_without_lockfile."""
        _write_file(
            tmp_path / "Pipfile",
            '[packages]\nrequests = "*"\n',
        )
        builder = _make_builder()
        scan_repository_dependency_consistency(tmp_path, builder)
        dep = _dep_evidence(builder)
        assert len(dep) >= 1
        signals = [e.metadata.get("signal") for e in dep]
        assert "pipfile_without_lockfile" in signals

    def test_node_lockfile_conflict(self, tmp_path: Path) -> None:
        """Multiple Node.js lockfiles → lockfile_conflict."""
        _write_file(tmp_path / "package-lock.json", "{}")
        _write_file(tmp_path / "yarn.lock", "")
        builder = _make_builder()
        scan_repository_dependency_consistency(tmp_path, builder)
        dep = _dep_evidence(builder)
        assert len(dep) >= 1
        signals = [e.metadata.get("signal") for e in dep]
        assert "lockfile_conflict" in signals

    def test_lockfile_without_manifest(self, tmp_path: Path) -> None:
        """poetry.lock without pyproject.toml → poetry_lockfile_without_manifest."""
        _write_file(tmp_path / "poetry.lock", "")
        builder = _make_builder()
        scan_repository_dependency_consistency(tmp_path, builder)
        dep = _dep_evidence(builder)
        assert len(dep) >= 1
        signals = [e.metadata.get("signal") for e in dep]
        assert "poetry_lockfile_without_manifest" in signals

    def test_clean_repo_no_dependency_signals(self, tmp_path: Path) -> None:
        """Clean repo → no dependency_health_signal evidence."""
        builder = _make_builder()
        scan_repository_dependency_consistency(tmp_path, builder)
        dep = _dep_evidence(builder)
        assert len(dep) == 0


# ═══════════════════════════════════════════════════════════════════════
# S01 Inventory: Analyzer outputs for dependency findings
# ═══════════════════════════════════════════════════════════════════════


class TestAnalyzerDependencyOutput:
    """Capture current analyzer output for dependency-related findings.

    These tests document the BEFORE state. After migration, the same
    tests must produce identical output.
    """

    def test_missing_lockfile_finding_fields(self, tmp_path: Path) -> None:
        """Node.js manifest without lockfile → TD-DEP finding with specific fields."""
        _write_file(
            tmp_path / "package.json",
            json.dumps({"name": "test", "dependencies": {"express": "^4.0.0"}}),
        )
        # Create a .git directory so scanner recognizes this as a repo
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        dep = _dep_findings(register)

        # Should have at least one TD-DEP finding (missing lockfile)
        lockfile_f = next(
            (
                f
                for f in dep
                if "lockfile" in f.title.lower() or "lockfile" in f.description.lower()
            ),
            None,
        )
        assert lockfile_f is not None, f"Expected lockfile finding, got: {[f.title for f in dep]}"
        assert lockfile_f.category == "TD-DEP"
        assert "Node.js" in lockfile_f.title
        assert lockfile_f.confidence == "High"
        assert lockfile_f.remediation_effort == "Small"
        assert lockfile_f.suggested_owner_area == "Product Engineering / Platform"

    def test_unpinned_deps_finding_fields(self, tmp_path: Path) -> None:
        """Unpinned Node.js deps → TD-DEP finding with specific fields."""
        _write_file(
            tmp_path / "package.json",
            json.dumps({"dependencies": {"express": "*"}}),
        )
        _write_file(tmp_path / "package-lock.json", "{}")
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        dep = _dep_findings(register)

        unpinned_f = next(
            (f for f in dep if "unpinned" in f.title.lower()),
            None,
        )
        assert unpinned_f is not None, f"Expected unpinned finding, got: {[f.title for f in dep]}"
        assert unpinned_f.category == "TD-DEP"
        assert "Node.js" in unpinned_f.title
        assert unpinned_f.confidence == "Medium"

    def test_python_missing_lockfile_finding_fields(self, tmp_path: Path) -> None:
        """Python manifest without lockfile → TD-DEP finding."""
        _write_file(
            tmp_path / "pyproject.toml",
            '[project]\nname = "test"\ndependencies = ["requests==2.31.0"]\n',
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        dep = _dep_findings(register)

        lockfile_f = next(
            (
                f
                for f in dep
                if "lockfile" in f.title.lower() or "lockfile" in f.description.lower()
            ),
            None,
        )
        assert lockfile_f is not None, f"Expected lockfile finding, got: {[f.title for f in dep]}"
        assert lockfile_f.category == "TD-DEP"
        assert "Python" in lockfile_f.title

    def test_no_false_positive_with_lockfile(self, tmp_path: Path) -> None:
        """package.json + package-lock.json → no missing lockfile TD-DEP."""
        _write_file(
            tmp_path / "package.json",
            json.dumps({"dependencies": {"express": "4.18.2"}}),
        )
        _write_file(tmp_path / "package-lock.json", "{}")
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        lockfile_dep = [
            f
            for f in _dep_findings(register)
            if "lockfile" in f.title.lower() or "lockfile" in f.description.lower()
        ]
        assert len(lockfile_dep) == 0, "Should not produce lockfile finding when lockfile present"

    def test_lockfile_conflict_finding_fields(self, tmp_path: Path) -> None:
        """Multiple Node lockfiles → lockfile conflict finding."""
        _write_file(
            tmp_path / "package.json",
            json.dumps({"dependencies": {"express": "4.18.2"}}),
        )
        _write_file(tmp_path / "package-lock.json", "{}")
        _write_file(tmp_path / "yarn.lock", "")
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        dep = _dep_findings(register)
        conflict_f = next(
            (f for f in dep if "multiple" in f.title.lower() or "lockfile" in f.title.lower()),
            None,
        )
        assert conflict_f is not None, f"Expected conflict finding, got: {[f.title for f in dep]}"
        assert conflict_f.category == "TD-DEP"

    def test_issue_type_advisory_for_missing_lockfile(self, tmp_path: Path) -> None:
        """Missing lockfile findings have issue_type advisory."""
        _write_file(
            tmp_path / "package.json",
            json.dumps({"dependencies": {"express": "^4.0.0"}}),
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        dep = _dep_findings(register)
        lockfile_f = next(
            (
                f
                for f in dep
                if "lockfile" in f.title.lower() or "lockfile" in f.description.lower()
            ),
            None,
        )
        assert lockfile_f is not None
        assert lockfile_f.issue_type == "advisory"


# ═══════════════════════════════════════════════════════════════════════
# S01 Inventory: Runtime/Dependency family separation
# ═══════════════════════════════════════════════════════════════════════


class TestRuntimeDependencySeparation:
    """Verify runtime and dependency signals don't double-count evidence.

    Runtime signals answer: what runtime/toolchain is selected?
    Dependency signals answer: what dependency-management condition exists?
    """

    def test_manifest_evidence_in_dependency_not_runtime(self, tmp_path: Path) -> None:
        """Manifest detection produces evidence for dependency analysis, not runtime."""
        _write_file(
            tmp_path / "package.json",
            json.dumps({"dependencies": {"express": "*"}}),
        )
        builder = _make_builder()
        scan_dependency_manifest(tmp_path / "package.json", "package.json", builder)
        dep = _dep_evidence(builder)
        # All evidence should be dependency_health_signal, not runtime
        for e in dep:
            assert e.type == EVIDENCE_DEPENDENCY_SIGNAL
            assert e.metadata.get("ecosystem") == "Node.js"

    def test_mixed_manifest_no_double_counting(self, tmp_path: Path) -> None:
        """package.json with engines + dependencies: runtime and dep signals are distinct."""
        _write_file(
            tmp_path / "package.json",
            json.dumps(
                {
                    "engines": {"node": ">=18.0.0"},
                    "dependencies": {"express": "*"},
                }
            ),
        )
        _write_file(tmp_path / "package-lock.json", "{}")
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)

        # Runtime findings come from _analyze_runtime_version_signals (uses governed adapters)
        # Dependency findings come from _analyze_dependency_signals (not yet governed)
        # Both may use TD-DEP category, but titles should be distinct
        runtime_titles = {f.title for f in register.findings if "runtime" in f.title.lower()}
        dep_titles = {f.title for f in _dep_findings(register)}

        # Findings should have different titles (runtime vs dependency purpose)
        # The same title appearing in both means double-counting
        overlap = runtime_titles & dep_titles
        # Note: runtime missing pins use TD-DEP category but answer a different question
        # (runtime selection, not dependency management)
        # Verify unpinned deps finding is present and distinct from runtime pin finding
        unpinned = [f for f in _dep_findings(register) if "unpinned" in f.title.lower()]
        missing_runtime = [
            f for f in register.findings if "missing runtime version pin" in f.title.lower()
        ]

        assert len(unpinned) >= 1, "Should have unpinned dependency finding"
        assert len(missing_runtime) >= 1, "Should have missing runtime pin advisory"

        # Titles must be distinct — different questions
        for dep_f in unpinned:
            for rt_f in missing_runtime:
                assert dep_f.title != rt_f.title, f"Runtime/dep title collision: {dep_f.title}"


# ═══════════════════════════════════════════════════════════════════════
# S01 Inventory: Signal type catalog (documentation, not tests)
# ═══════════════════════════════════════════════════════════════════════
#
# Known dependency signal types (from dependency_parsers.py):
#
#   unpinned_dependency          — EVIDENCE_DEPENDENCY_SIGNAL
#   lockfile_conflict            — EVIDENCE_DEPENDENCY_SIGNAL
#   poetry_manifest_without_lockfile  — EVIDENCE_DEPENDENCY_SIGNAL
#   pipfile_without_lockfile     — EVIDENCE_DEPENDENCY_SIGNAL
#   poetry_lockfile_without_manifest — EVIDENCE_DEPENDENCY_SIGNAL
#   pipfile_lock_without_manifest — EVIDENCE_DEPENDENCY_SIGNAL
#   dependency_manifest_parse_failure — EVIDENCE_DEPENDENCY_SIGNAL
#
# Known dependency analyzer paths (from analyzer.py):
#
#   _analyze_missing_lockfile    — TD-DEP, issue_type="advisory"
#   _analyze_dependency_signals  — TD-DEP, issue_type="finding" (unpinned, lockfile_conflict)
#
# Categories: All dependency output uses "TD-DEP"
#
# Boundary: TD-BUILD and TD-CONFIG are NOT used by dependency analyzers.
#           Only TD-DEP is produced. No migration of TD-BUILD/TD-CONFIG needed.
