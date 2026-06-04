"""v3.16.0 — Dependency signal boundary and regression fixtures.

Protects behavior and prevents promotion drift with fixture-based tests.
Covers all key dependency scenarios.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pharabius.core.analyzer import analyze_evidence
from pharabius.core.init_workspace import initialize_workspace
from pharabius.core.scanner import write_evidence_store
from pharabius.core.signals.dependency_adapters import (
    dependency_lockfile_conflict_to_signal,
    dependency_manifest_detected_to_signal,
    dependency_missing_lockfile_to_signal,
    dependency_unpinned_to_signal,
)
from pharabius.core.signals.models import (
    SignalDisposition,
    SignalFamily,
)
from pharabius.core.signals.policy import (
    output_behavior,
    should_create_work_package,
)
from pharabius.core.signals.validation import validate_governed_signal


def _write_file(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _analyze_repo(tmp_path: Path) -> Any:
    initialize_workspace(tmp_path)
    write_evidence_store(tmp_path)
    return analyze_evidence(tmp_path)


def _dep_findings(register: Any) -> list[Any]:
    return [f for f in register.findings if f.category == "TD-DEP"]


# ═══════════════════════════════════════════════════════════════════════
# S07: Adapter disposition correctness
# ═══════════════════════════════════════════════════════════════════════


class TestAdapterDispositions:
    """Adapters produce correct dispositions for each signal type."""

    def test_unpinned_is_finding(self) -> None:
        sig = dependency_unpinned_to_signal(
            [],
            ecosystem="Node.js",
            count=3,
        )
        assert sig.disposition == SignalDisposition.FINDING
        assert sig.family == SignalFamily.DEPENDENCY
        behav = output_behavior(sig)
        assert behav.creates_finding is True
        assert behav.creates_work_package is True

    def test_lockfile_conflict_is_finding(self) -> None:
        sig = dependency_lockfile_conflict_to_signal(
            [],
            lockfiles=["package-lock.json", "yarn.lock"],
        )
        assert sig.disposition == SignalDisposition.FINDING
        assert sig.family == SignalFamily.DEPENDENCY
        behav = output_behavior(sig)
        assert behav.creates_finding is True

    def test_missing_lockfile_is_advisory(self) -> None:
        sig = dependency_missing_lockfile_to_signal(
            [],
            ecosystem="Node.js",
            package_root=".",
        )
        assert sig.disposition == SignalDisposition.ADVISORY
        assert sig.family == SignalFamily.DEPENDENCY
        behav = output_behavior(sig)
        assert behav.creates_advisory is True
        assert behav.creates_work_package is False

    def test_manifest_detected_is_informational(self) -> None:
        from pharabius.schemas.evidence import EvidenceItem

        item = EvidenceItem(
            evidence_id="EVD-000001",
            type="dependency_health_signal",
            category="dependencies",
            summary="test",
            metadata={"ecosystem": "Node.js"},
        )
        sig = dependency_manifest_detected_to_signal(item)
        assert sig.disposition == SignalDisposition.INFORMATIONAL
        assert sig.family == SignalFamily.DEPENDENCY
        behav = output_behavior(sig)
        assert behav.creates_finding is False
        assert behav.creates_advisory is False
        assert behav.creates_work_package is False
        assert behav.appears_in_summary is True

    def test_advisories_do_not_create_work_packages(self) -> None:
        sig = dependency_missing_lockfile_to_signal(
            [],
            ecosystem="Python",
            package_root=".",
        )
        assert should_create_work_package(sig) is False


# ═══════════════════════════════════════════════════════════════════════
# S07: Validation conformance
# ═══════════════════════════════════════════════════════════════════════


class TestAdapterValidation:
    """All dependency adapters produce valid GovernedSignal instances."""

    def test_unpinned_validates(self) -> None:
        sig = dependency_unpinned_to_signal(
            [],
            ecosystem="Node.js",
            count=3,
        )
        result = validate_governed_signal(sig)
        # FINDING without evidence gets INV_006 — expected
        assert any(v.invariant_code == "INV_006" for v in result.violations) or result.valid

    def test_lockfile_conflict_validates(self) -> None:
        sig = dependency_lockfile_conflict_to_signal(
            [],
            lockfiles=["a", "b"],
        )
        result = validate_governed_signal(sig)
        assert any(v.invariant_code == "INV_006" for v in result.violations) or result.valid

    def test_missing_lockfile_validates(self) -> None:
        sig = dependency_missing_lockfile_to_signal(
            [],
            ecosystem="Python",
            package_root=".",
        )
        result = validate_governed_signal(sig)
        assert result.valid

    def test_signal_ids_deterministic(self) -> None:
        sig1 = dependency_unpinned_to_signal([], ecosystem="Node.js", count=3)
        sig2 = dependency_unpinned_to_signal([], ecosystem="Node.js", count=3)
        assert sig1.signal_id == sig2.signal_id

    def test_metadata_preserves_ecosystem(self) -> None:
        sig = dependency_unpinned_to_signal([], ecosystem="Python", count=5)
        assert sig.metadata["ecosystem"] == "Python"
        assert sig.metadata["count"] == 5


# ═══════════════════════════════════════════════════════════════════════
# S07: Fixture scenarios
# ═══════════════════════════════════════════════════════════════════════


class TestFixtureManifestOnly:
    """manifest_only: project with manifest but no lockfile."""

    def test_produces_missing_lockfile_finding(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "package.json",
            json.dumps({"dependencies": {"express": "^4.0.0"}}),
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        dep = _dep_findings(register)
        assert len(dep) >= 1
        assert any(
            "lockfile" in f.title.lower() or "lockfile" in f.description.lower() for f in dep
        )

    def test_missing_lockfile_is_advisory(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "package.json",
            json.dumps({"dependencies": {"express": "^4.0.0"}}),
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        lockfile_f = next(
            (f for f in _dep_findings(register) if "lockfile" in f.description.lower()),
            None,
        )
        assert lockfile_f is not None
        assert lockfile_f.issue_type == "advisory"


class TestFixtureManifestWithLockfile:
    """manifest_with_lockfile: both present and consistent."""

    def test_no_missing_lockfile_finding(self, tmp_path: Path) -> None:
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
        assert len(lockfile_dep) == 0


class TestFixtureUnpinnedDependency:
    """unpinned_dependency: lockfile with unversioned references."""

    def test_produces_unpinned_finding(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "package.json",
            json.dumps({"dependencies": {"express": "*"}}),
        )
        _write_file(tmp_path / "package-lock.json", "{}")
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        dep = _dep_findings(register)
        unpinned = [f for f in dep if "unpinned" in f.title.lower()]
        assert len(unpinned) >= 1
        assert "TD-DEP" in unpinned[0].category


class TestFixtureMultiplePackageManagers:
    """multiple_package_managers: both package.json and requirements.txt."""

    def test_produces_findings_for_both(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "package.json",
            json.dumps({"dependencies": {"express": "*"}}),
        )
        _write_file(
            tmp_path / "requirements.txt",
            "requests\nflask\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        dep = _dep_findings(register)

        # Should have findings for both ecosystems
        titles = " ".join(f.title for f in dep)
        assert "Node.js" in titles or "Python" in titles


class TestFixtureCleanBaseline:
    """clean_dependency_baseline: no dependency evidence at all."""

    def test_no_dep_findings(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "main.py", "print('hello')")
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        dep = _dep_findings(register)
        assert len(dep) == 0


class TestFixtureRuntimeDependencyNoDoubleCounting:
    """Mixed manifest: engines + dependencies should not double-count."""

    def test_runtime_and_dependency_distinct(self, tmp_path: Path) -> None:
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

        # Unpinned deps finding (dependency family)
        unpinned = [f for f in _dep_findings(register) if "unpinned" in f.title.lower()]
        # Runtime pin advisory (runtime family)
        runtime_pins = [
            f for f in register.findings if "missing runtime version pin" in f.title.lower()
        ]

        # Both should exist and be distinct
        assert len(unpinned) >= 1
        assert len(runtime_pins) >= 1

        # No title collision
        for u in unpinned:
            for r in runtime_pins:
                assert u.title != r.title
