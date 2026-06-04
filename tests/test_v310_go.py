"""v3.10.0 S01 — Go runtime evidence tests."""

from __future__ import annotations

from pathlib import Path

from pharabius.core.runtime.go import detect_go_sources
from pharabius.core.runtime.models import (
    RuntimeConstraintKind,
    RuntimeEcosystem,
)


class TestGoSources:
    def test_go_mod_go_directive(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text("module example.com/m\n\ngo 1.22.0\n")
        evidence = detect_go_sources(tmp_path)
        go_ev = [e for e in evidence if e.source_detail == "go-directive"]
        assert len(go_ev) == 1
        assert go_ev[0].ecosystem == RuntimeEcosystem.GO
        assert go_ev[0].source_path == "go.mod"

    def test_go_mod_toolchain_directive(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text(
            "module example.com/m\n\ngo 1.22.0\n\ntoolchain go1.22.4\n"
        )
        evidence = detect_go_sources(tmp_path)
        tc_ev = [e for e in evidence if e.source_detail == "toolchain"]
        assert len(tc_ev) == 1
        assert tc_ev[0].raw_version == "go1.22.4"

    def test_go_directive_is_range(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text("module example.com/m\n\ngo 1.22.0\n")
        evidence = detect_go_sources(tmp_path)
        go_ev = [e for e in evidence if e.source_detail == "go-directive"]
        assert go_ev[0].constraint.kind == RuntimeConstraintKind.RANGE

    def test_toolchain_is_exact(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text(
            "module example.com/m\n\ngo 1.22.0\n\ntoolchain go1.22.4\n"
        )
        evidence = detect_go_sources(tmp_path)
        tc_ev = [e for e in evidence if e.source_detail == "toolchain"]
        assert tc_ev[0].constraint.kind == RuntimeConstraintKind.EXACT

    def test_no_go_mod_returns_empty(self, tmp_path: Path) -> None:
        evidence = detect_go_sources(tmp_path)
        assert evidence == []

    def test_go_mod_empty_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text("")
        evidence = detect_go_sources(tmp_path)
        assert evidence == []
