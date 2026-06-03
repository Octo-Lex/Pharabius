"""v3.10.0 S02 — .NET runtime evidence tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from pharabius.core.runtime.dotnet import detect_dotnet_sources
from pharabius.core.runtime.models import RuntimeConstraintKind, RuntimeEcosystem


class TestDotnetSources:
    def test_global_json_sdk_pin(self, tmp_path: Path) -> None:
        (tmp_path / "global.json").write_text('{"sdk": {"version": "8.0.100"}}\n')
        evidence = detect_dotnet_sources(tmp_path)
        sdk_ev = [e for e in evidence if e.source_detail == "sdk"]
        assert len(sdk_ev) == 1
        assert sdk_ev[0].constraint.kind == RuntimeConstraintKind.EXACT
        assert sdk_ev[0].raw_version == "8.0.100"

    def test_csproj_target_framework(self, tmp_path: Path) -> None:
        (tmp_path / "App.csproj").write_text(
            "<Project><PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>"
        )
        evidence = detect_dotnet_sources(tmp_path)
        tf_ev = [e for e in evidence if e.source_detail == "target-framework"]
        assert len(tf_ev) == 1
        assert tf_ev[0].constraint.kind == RuntimeConstraintKind.RANGE

    def test_csproj_multiple_targets(self, tmp_path: Path) -> None:
        (tmp_path / "App.csproj").write_text(
            "<Project><PropertyGroup><TargetFrameworks>net8.0;net9.0</TargetFrameworks></PropertyGroup></Project>"
        )
        evidence = detect_dotnet_sources(tmp_path)
        tf_ev = [e for e in evidence if e.source_detail == "target-framework"]
        assert len(tf_ev) == 2

    def test_nested_csproj_found(self, tmp_path: Path) -> None:
        src = tmp_path / "src" / "App"
        src.mkdir(parents=True)
        (src / "App.csproj").write_text(
            "<Project><PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>"
        )
        evidence = detect_dotnet_sources(tmp_path)
        assert any("src" in e.source_path for e in evidence)

    def test_bin_obj_excluded(self, tmp_path: Path) -> None:
        obj = tmp_path / "obj"
        obj.mkdir()
        (obj / "project.csproj").write_text(
            "<Project><PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>"
        )
        evidence = detect_dotnet_sources(tmp_path)
        assert len(evidence) == 0

    def test_no_dotnet_files_returns_empty(self, tmp_path: Path) -> None:
        evidence = detect_dotnet_sources(tmp_path)
        assert evidence == []
