"""v3.10.0 S06 — Runtime coverage benchmark fixture tests.

Validates expected behavior for each ecosystem across 5 fixture types:
clean_pinned, missing_pin, conflict_ci, conflict_docker, unknown_dynamic.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pharabius.core.runtime.conflict import detect_conflicts
from pharabius.core.runtime.detector import detect_runtime_version_pins
from pharabius.core.runtime.policy import is_runtime_pin
from pharabius.schemas.evidence import EvidenceBuilder

FIXTURES = Path(__file__).parent / "fixtures" / "runtime"


def _fixture_path(ecosystem: str, fixture: str) -> Path:
    return FIXTURES / ecosystem / fixture


def _scan(path: Path) -> tuple[list, list]:
    """Scan fixture and return (conflicts, all_evidence)."""
    from pharabius.core.runtime.detector import (
        detect_python_sources, detect_node_sources, detect_ruby_sources,
        detect_java_sources, detect_go_sources, detect_rust_sources,
        detect_dotnet_sources, detect_php_sources,
        detect_tool_versions_sources, detect_dockerfile_sources,
        detect_ci_sources,
    )
    all_ev = []
    all_ev.extend(detect_python_sources(path))
    all_ev.extend(detect_node_sources(path))
    all_ev.extend(detect_ruby_sources(path))
    all_ev.extend(detect_java_sources(path))
    all_ev.extend(detect_go_sources(path))
    all_ev.extend(detect_rust_sources(path))
    all_ev.extend(detect_dotnet_sources(path))
    all_ev.extend(detect_php_sources(path))
    all_ev.extend(detect_tool_versions_sources(path))
    all_ev.extend(detect_dockerfile_sources(path))
    all_ev.extend(detect_ci_sources(path))
    conflicts = detect_conflicts(all_ev)
    return conflicts, all_ev


# ── Go fixtures ──────────────────────────────────────────────────────


class TestGoFixtures:
    def test_clean_pinned_no_conflict(self) -> None:
        conflicts, _ = _scan(_fixture_path("go", "clean_pinned"))
        go_conflicts = [c for c in conflicts if c.runtime_name == "Go"]
        assert len(go_conflicts) == 0, "Clean pinned should have no conflict"

    def test_clean_pinned_has_pin(self) -> None:
        _, evidence = _scan(_fixture_path("go", "clean_pinned"))
        go_pins = [e for e in evidence if e.runtime_name == "Go" and is_runtime_pin(e)]
        assert len(go_pins) >= 1, "Clean pinned should have at least one pin"

    def test_missing_pin_no_conflict(self) -> None:
        conflicts, _ = _scan(_fixture_path("go", "missing_pin"))
        go_conflicts = [c for c in conflicts if c.runtime_name == "Go"]
        assert len(go_conflicts) == 0, "Missing pin should not produce conflict"

    def test_missing_pin_no_real_pin(self) -> None:
        _, evidence = _scan(_fixture_path("go", "missing_pin"))
        go_pins = [e for e in evidence if e.runtime_name == "Go" and is_runtime_pin(e)]
        assert len(go_pins) == 0, "go directive alone should not count as pin"

    def test_conflict_ci_produces_conflict(self) -> None:
        conflicts, _ = _scan(_fixture_path("go", "conflict_ci"))
        go_conflicts = [c for c in conflicts if c.runtime_name == "Go"]
        assert len(go_conflicts) >= 1, "CI conflict should produce finding"

    def test_conflict_docker_produces_conflict(self) -> None:
        conflicts, _ = _scan(_fixture_path("go", "conflict_docker"))
        go_conflicts = [c for c in conflicts if c.runtime_name == "Go"]
        assert len(go_conflicts) >= 1, "Docker conflict should produce finding"

    def test_unknown_dynamic_no_conflict(self) -> None:
        conflicts, _ = _scan(_fixture_path("go", "unknown_dynamic"))
        go_conflicts = [c for c in conflicts if c.runtime_name == "Go"]
        assert len(go_conflicts) == 0, "ARG-based should not produce conflict"


# ── Rust fixtures ────────────────────────────────────────────────────


class TestRustFixtures:
    def test_clean_pinned_no_conflict(self) -> None:
        conflicts, _ = _scan(_fixture_path("rust", "clean_pinned"))
        rust_conflicts = [c for c in conflicts if c.runtime_name == "Rust"]
        assert len(rust_conflicts) == 0

    def test_clean_pinned_has_pin(self) -> None:
        _, evidence = _scan(_fixture_path("rust", "clean_pinned"))
        rust_pins = [e for e in evidence if e.runtime_name == "Rust" and is_runtime_pin(e)]
        assert len(rust_pins) >= 1

    def test_missing_pin_no_conflict(self) -> None:
        conflicts, _ = _scan(_fixture_path("rust", "missing_pin"))
        rust_conflicts = [c for c in conflicts if c.runtime_name == "Rust"]
        assert len(rust_conflicts) == 0

    def test_missing_pin_rust_version_not_pin(self) -> None:
        _, evidence = _scan(_fixture_path("rust", "missing_pin"))
        rust_pins = [e for e in evidence if e.runtime_name == "Rust" and is_runtime_pin(e)]
        assert len(rust_pins) == 0, "rust-version should not count as pin"

    def test_conflict_docker_produces_conflict(self) -> None:
        conflicts, _ = _scan(_fixture_path("rust", "conflict_docker"))
        rust_conflicts = [c for c in conflicts if c.runtime_name == "Rust"]
        assert len(rust_conflicts) >= 1

    def test_unknown_dynamic_stable_is_not_pin(self) -> None:
        _, evidence = _scan(_fixture_path("rust", "unknown_dynamic"))
        rust_pins = [e for e in evidence if e.runtime_name == "Rust" and is_runtime_pin(e)]
        assert len(rust_pins) == 0, "stable channel should not count as pin"


# ── .NET fixtures ────────────────────────────────────────────────────


class TestDotnetFixtures:
    def test_clean_pinned_no_conflict(self) -> None:
        conflicts, _ = _scan(_fixture_path("dotnet", "clean_pinned"))
        dotnet_conflicts = [c for c in conflicts if c.runtime_name == ".NET"]
        assert len(dotnet_conflicts) == 0

    def test_clean_pinned_has_pin(self) -> None:
        _, evidence = _scan(_fixture_path("dotnet", "clean_pinned"))
        dotnet_pins = [e for e in evidence if e.runtime_name == ".NET" and is_runtime_pin(e)]
        assert len(dotnet_pins) >= 1

    def test_missing_pin_no_conflict(self) -> None:
        conflicts, _ = _scan(_fixture_path("dotnet", "missing_pin"))
        dotnet_conflicts = [c for c in conflicts if c.runtime_name == ".NET"]
        assert len(dotnet_conflicts) == 0

    def test_missing_pin_target_framework_not_pin(self) -> None:
        _, evidence = _scan(_fixture_path("dotnet", "missing_pin"))
        dotnet_pins = [e for e in evidence if e.runtime_name == ".NET" and is_runtime_pin(e)]
        assert len(dotnet_pins) == 0, "TargetFramework should not count as pin"

    def test_conflict_ci_produces_conflict(self) -> None:
        conflicts, _ = _scan(_fixture_path("dotnet", "conflict_ci"))
        dotnet_conflicts = [c for c in conflicts if c.runtime_name == ".NET"]
        assert len(dotnet_conflicts) >= 1

    def test_conflict_docker_produces_conflict(self) -> None:
        conflicts, _ = _scan(_fixture_path("dotnet", "conflict_docker"))
        dotnet_conflicts = [c for c in conflicts if c.runtime_name == ".NET"]
        assert len(dotnet_conflicts) >= 1

    def test_unknown_dynamic_no_conflict(self) -> None:
        conflicts, _ = _scan(_fixture_path("dotnet", "unknown_dynamic"))
        dotnet_conflicts = [c for c in conflicts if c.runtime_name == ".NET"]
        assert len(dotnet_conflicts) == 0


# ── PHP fixtures ─────────────────────────────────────────────────────


class TestPhpFixtures:
    def test_clean_pinned_no_conflict(self) -> None:
        conflicts, _ = _scan(_fixture_path("php", "clean_pinned"))
        php_conflicts = [c for c in conflicts if c.runtime_name == "PHP"]
        assert len(php_conflicts) == 0

    def test_clean_pinned_has_pin(self) -> None:
        _, evidence = _scan(_fixture_path("php", "clean_pinned"))
        php_pins = [e for e in evidence if e.runtime_name == "PHP" and is_runtime_pin(e)]
        assert len(php_pins) >= 1

    def test_missing_pin_no_conflict(self) -> None:
        conflicts, _ = _scan(_fixture_path("php", "missing_pin"))
        php_conflicts = [c for c in conflicts if c.runtime_name == "PHP"]
        assert len(php_conflicts) == 0

    def test_conflict_ci_produces_conflict(self) -> None:
        conflicts, _ = _scan(_fixture_path("php", "conflict_ci"))
        php_conflicts = [c for c in conflicts if c.runtime_name == "PHP"]
        assert len(php_conflicts) >= 1

    def test_conflict_docker_produces_conflict(self) -> None:
        conflicts, _ = _scan(_fixture_path("php", "conflict_docker"))
        php_conflicts = [c for c in conflicts if c.runtime_name == "PHP"]
        assert len(php_conflicts) >= 1

    def test_unknown_dynamic_no_conflict(self) -> None:
        conflicts, _ = _scan(_fixture_path("php", "unknown_dynamic"))
        php_conflicts = [c for c in conflicts if c.runtime_name == "PHP"]
        assert len(php_conflicts) == 0
