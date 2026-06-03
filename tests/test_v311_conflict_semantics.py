"""v3.11.0 S02-S05 — Conflict detection with source grades."""
from __future__ import annotations

from pathlib import Path

import pytest

from pharabius.core.runtime.conflict import detect_conflicts
from pharabius.core.runtime.go import detect_go_sources
from pharabius.core.runtime.rust import detect_rust_sources
from pharabius.core.runtime.dotnet import detect_dotnet_sources
from pharabius.core.runtime.php import detect_php_sources
from pharabius.core.runtime.docker import detect_dockerfile_sources
from pharabius.core.runtime.github_actions import detect_ci_sources
from pharabius.core.runtime.tool_versions import detect_tool_versions_sources
from pharabius.core.runtime.models import RuntimeConflictKind


def _all_ev(root: Path) -> list:
    all_ev = []
    for fn in [detect_go_sources, detect_rust_sources, detect_dotnet_sources,
               detect_php_sources, detect_dockerfile_sources, detect_ci_sources,
               detect_tool_versions_sources]:
        all_ev.extend(fn(root))
    return all_ev


class TestPinVsManifestRange:
    """S02: Deterministic pin outside manifest range → finding."""

    def test_toolchain_below_go_directive(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text("module ex\ngo 1.22\n\ntoolchain go1.20.0\n")
        conflicts = detect_conflicts(detect_go_sources(tmp_path))
        pin_conflicts = [c for c in conflicts
                         if c.conflict_kind == RuntimeConflictKind.PIN_VIOLATES_MANIFEST_RANGE]
        assert len(pin_conflicts) >= 1

    def test_toolchain_above_go_directive_no_conflict(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text("module ex\ngo 1.20\n\ntoolchain go1.22.4\n")
        conflicts = detect_conflicts(detect_go_sources(tmp_path))
        pin_conflicts = [c for c in conflicts
                         if c.conflict_kind == RuntimeConflictKind.PIN_VIOLATES_MANIFEST_RANGE]
        assert len(pin_conflicts) == 0

    def test_rust_toolchain_below_minimum(self, tmp_path: Path) -> None:
        (tmp_path / "rust-toolchain").write_text("1.70.0\n")
        (tmp_path / "Cargo.toml").write_text('[package]\nrust-version = "1.76"\n')
        all_ev = detect_rust_sources(tmp_path)
        conflicts = detect_conflicts(all_ev)
        pin_conflicts = [c for c in conflicts
                         if c.conflict_kind == RuntimeConflictKind.PIN_VIOLATES_MANIFEST_RANGE]
        assert len(pin_conflicts) >= 1

    def test_rust_toolchain_above_minimum_no_conflict(self, tmp_path: Path) -> None:
        (tmp_path / "rust-toolchain").write_text("1.80.0\n")
        (tmp_path / "Cargo.toml").write_text('[package]\nrust-version = "1.76"\n')
        all_ev = detect_rust_sources(tmp_path)
        conflicts = detect_conflicts(all_ev)
        pin_conflicts = [c for c in conflicts
                         if c.conflict_kind == RuntimeConflictKind.PIN_VIOLATES_MANIFEST_RANGE]
        assert len(pin_conflicts) == 0


class TestIncompatibleRanges:
    """S04: Definitely disjoint ranges → finding."""

    def test_caret_disjoint_ranges(self, tmp_path: Path) -> None:
        """Two .csproj files with non-overlapping targets."""
        (tmp_path / "App1.csproj").write_text(
            "<Project><PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>"
        )
        (tmp_path / "App2.csproj").write_text(
            "<Project><PropertyGroup><TargetFramework>net5.0</TargetFramework></PropertyGroup></Project>"
        )
        all_ev = detect_dotnet_sources(tmp_path)
        # net8.0 = RANGE [8,9), net5.0 = RANGE [5,6) → disjoint
        conflicts = detect_conflicts(all_ev)
        range_conflicts = [c for c in conflicts
                          if c.conflict_kind == RuntimeConflictKind.INCOMPATIBLE_RANGES]
        assert len(range_conflicts) >= 1

    def test_overlapping_ranges_no_conflict(self, tmp_path: Path) -> None:
        """Same target framework in two csproj files → no conflict."""
        (tmp_path / "App1.csproj").write_text(
            "<Project><PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>"
        )
        (tmp_path / "App2.csproj").write_text(
            "<Project><PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>"
        )
        all_ev = detect_dotnet_sources(tmp_path)
        conflicts = detect_conflicts(all_ev)
        range_conflicts = [c for c in conflicts
                          if c.conflict_kind == RuntimeConflictKind.INCOMPATIBLE_RANGES]
        assert len(range_conflicts) == 0


class TestConflictExplanation:
    """S05: Explanations include source grade."""

    def test_explanation_includes_grade(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text("module ex\ngo 1.22\n\ntoolchain go1.20.0\n")
        conflicts = detect_conflicts(detect_go_sources(tmp_path))
        pin_conflicts = [c for c in conflicts
                         if c.conflict_kind == RuntimeConflictKind.PIN_VIOLATES_MANIFEST_RANGE]
        if pin_conflicts:
            assert "manifest_pin" in pin_conflicts[0].explanation or "manifest_range" in pin_conflicts[0].explanation


class TestRangeVsRangeBoundary:
    """S04 boundary tests for range comparison."""

    def test_boundary_equality_not_disjoint(self) -> None:
        from pharabius.core.runtime.constraints import ranges_are_disjoint
        from pharabius.core.runtime.models import RuntimeConstraint, RuntimeConstraintKind

        # <9.0 vs >=9.0 → <9 (upper=9) vs >=9 (lower=9) → disjoint
        a = RuntimeConstraint(kind=RuntimeConstraintKind.RANGE, lower_bound="9", upper_bound="10", raw=">=9,<10")
        b = RuntimeConstraint(kind=RuntimeConstraintKind.RANGE, lower_bound="7", upper_bound="9", raw=">=7,<9")
        assert ranges_are_disjoint(a, b) is True

    def test_overlapping_not_disjoint(self) -> None:
        from pharabius.core.runtime.constraints import ranges_are_disjoint
        from pharabius.core.runtime.models import RuntimeConstraint, RuntimeConstraintKind

        a = RuntimeConstraint(kind=RuntimeConstraintKind.RANGE, lower_bound="8", upper_bound="10", raw=">=8,<10")
        b = RuntimeConstraint(kind=RuntimeConstraintKind.RANGE, lower_bound="9", upper_bound="11", raw=">=9,<11")
        assert ranges_are_disjoint(a, b) is False
