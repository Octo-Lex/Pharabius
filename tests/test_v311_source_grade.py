"""v3.11.0 S01 — RuntimeSourceGrade and helper predicate tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from pharabius.core.runtime.models import (
    RuntimeConstraint,
    RuntimeConstraintKind,
    RuntimeEcosystem,
    RuntimeEvidence,
    RuntimeSourceGrade,
    RuntimeSourceType,
)
from pharabius.core.runtime.policy import (
    is_deterministic_project_pin,
    is_manifest_compatibility_range,
)


def _ev(
    source_grade: RuntimeSourceGrade,
    kind: RuntimeConstraintKind = RuntimeConstraintKind.EXACT,
    source_type: RuntimeSourceType = RuntimeSourceType.VERSION_FILE,
) -> RuntimeEvidence:
    return RuntimeEvidence(
        runtime_evidence_id="test",
        ecosystem=RuntimeEcosystem.PYTHON,
        runtime_name="Test",
        constraint=RuntimeConstraint(kind=kind, value="1.0"),
        source_type=source_type,
        source_path="test",
        source_grade=source_grade,
    )


class TestSourceGradeClassification:
    """Verify each parser sets correct source_grade."""

    def test_python_version_file_is_version_file(self, tmp_path: Path) -> None:
        from pharabius.core.runtime.ecosystems import detect_python_sources
        (tmp_path / ".python-version").write_text("3.11\n")
        ev = detect_python_sources(tmp_path)
        assert all(e.source_grade == RuntimeSourceGrade.VERSION_FILE for e in ev)

    def test_go_directive_is_manifest_range(self, tmp_path: Path) -> None:
        from pharabius.core.runtime.go import detect_go_sources
        (tmp_path / "go.mod").write_text("module ex\ngo 1.22\n")
        ev = detect_go_sources(tmp_path)
        go_ev = [e for e in ev if e.source_detail == "go-directive"]
        assert len(go_ev) == 1
        assert go_ev[0].source_grade == RuntimeSourceGrade.MANIFEST_RANGE

    def test_go_toolchain_is_manifest_pin(self, tmp_path: Path) -> None:
        from pharabius.core.runtime.go import detect_go_sources
        (tmp_path / "go.mod").write_text("module ex\ngo 1.22\n\ntoolchain go1.22.4\n")
        ev = detect_go_sources(tmp_path)
        tc_ev = [e for e in ev if e.source_detail == "toolchain"]
        assert len(tc_ev) == 1
        assert tc_ev[0].source_grade == RuntimeSourceGrade.MANIFEST_PIN

    def test_rust_toolchain_is_lockfile(self, tmp_path: Path) -> None:
        from pharabius.core.runtime.rust import detect_rust_sources
        (tmp_path / "rust-toolchain").write_text("1.76.0\n")
        ev = detect_rust_sources(tmp_path)
        assert len(ev) == 1
        assert ev[0].source_grade == RuntimeSourceGrade.LOCKFILE

    def test_rust_cargo_rust_version_is_manifest_range(self, tmp_path: Path) -> None:
        from pharabius.core.runtime.rust import detect_rust_sources
        (tmp_path / "Cargo.toml").write_text('[package]\nrust-version = "1.76"\n')
        ev = detect_rust_sources(tmp_path)
        assert len(ev) == 1
        assert ev[0].source_grade == RuntimeSourceGrade.MANIFEST_RANGE

    def test_dotnet_global_json_is_manifest_pin(self, tmp_path: Path) -> None:
        from pharabius.core.runtime.dotnet import detect_dotnet_sources
        (tmp_path / "global.json").write_text('{"sdk": {"version": "8.0.100"}}\n')
        ev = detect_dotnet_sources(tmp_path)
        assert len(ev) == 1
        assert ev[0].source_grade == RuntimeSourceGrade.MANIFEST_PIN

    def test_dotnet_csproj_is_manifest_range(self, tmp_path: Path) -> None:
        from pharabius.core.runtime.dotnet import detect_dotnet_sources
        (tmp_path / "App.csproj").write_text(
            "<Project><PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>"
        )
        ev = detect_dotnet_sources(tmp_path)
        assert len(ev) == 1
        assert ev[0].source_grade == RuntimeSourceGrade.MANIFEST_RANGE

    def test_php_composer_is_manifest_pin(self, tmp_path: Path) -> None:
        from pharabius.core.runtime.php import detect_php_sources
        (tmp_path / "composer.json").write_text('{"require": {"php": "8.2.12"}}\n')
        ev = detect_php_sources(tmp_path)
        assert len(ev) == 1
        assert ev[0].source_grade == RuntimeSourceGrade.MANIFEST_PIN


class TestDeterministicProjectPin:
    """is_deterministic_project_pin tests."""

    def test_lockfile_exact_is_deterministic(self) -> None:
        assert is_deterministic_project_pin(_ev(RuntimeSourceGrade.LOCKFILE))

    def test_tool_pin_exact_is_deterministic(self) -> None:
        assert is_deterministic_project_pin(_ev(RuntimeSourceGrade.TOOL_PIN))

    def test_version_file_exact_is_deterministic(self) -> None:
        assert is_deterministic_project_pin(_ev(RuntimeSourceGrade.VERSION_FILE))

    def test_manifest_pin_exact_is_deterministic(self) -> None:
        assert is_deterministic_project_pin(_ev(RuntimeSourceGrade.MANIFEST_PIN))

    def test_manifest_range_is_not_deterministic(self) -> None:
        assert not is_deterministic_project_pin(_ev(RuntimeSourceGrade.MANIFEST_RANGE))

    def test_container_is_not_deterministic(self) -> None:
        assert not is_deterministic_project_pin(_ev(RuntimeSourceGrade.CONTAINER))

    def test_ci_is_not_deterministic(self) -> None:
        assert not is_deterministic_project_pin(_ev(RuntimeSourceGrade.CI))

    def test_range_constraint_is_not_deterministic(self) -> None:
        ev = _ev(RuntimeSourceGrade.VERSION_FILE, kind=RuntimeConstraintKind.RANGE)
        assert not is_deterministic_project_pin(ev)


class TestManifestCompatibilityRange:
    """is_manifest_compatibility_range tests."""

    def test_manifest_range_is_range(self) -> None:
        assert is_manifest_compatibility_range(_ev(RuntimeSourceGrade.MANIFEST_RANGE))

    def test_manifest_pin_is_not_range(self) -> None:
        assert not is_manifest_compatibility_range(_ev(RuntimeSourceGrade.MANIFEST_PIN))

    def test_lockfile_is_not_range(self) -> None:
        assert not is_manifest_compatibility_range(_ev(RuntimeSourceGrade.LOCKFILE))
