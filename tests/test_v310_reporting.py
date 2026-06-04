"""v3.10.0 S07 — Runtime summary/reporting expansion tests.

Verifies that new ecosystems (Go, Rust, .NET, PHP) appear correctly
in runtime evidence summaries and reports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pharabius.core.runtime.conflict import detect_conflicts
from pharabius.core.runtime.detector import (
    detect_ci_sources,
    detect_dockerfile_sources,
    detect_dotnet_sources,
    detect_go_sources,
    detect_php_sources,
    detect_rust_sources,
)


def _all_evidence(root: Path) -> list:
    """Collect all runtime evidence from new ecosystem parsers."""
    all_ev = []
    all_ev.extend(detect_go_sources(root))
    all_ev.extend(detect_rust_sources(root))
    all_ev.extend(detect_dotnet_sources(root))
    all_ev.extend(detect_php_sources(root))
    all_ev.extend(detect_dockerfile_sources(root))
    all_ev.extend(detect_ci_sources(root))
    return all_ev


class TestRuntimeSummaryExpansion:
    def test_go_ecosystem_detected(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text("module ex\ngo 1.22\n")
        ev = _all_evidence(tmp_path)
        names = {e.runtime_name for e in ev}
        assert "Go" in names

    def test_rust_ecosystem_detected(self, tmp_path: Path) -> None:
        (tmp_path / "rust-toolchain").write_text("1.76.0\n")
        ev = _all_evidence(tmp_path)
        names = {e.runtime_name for e in ev}
        assert "Rust" in names

    def test_dotnet_ecosystem_detected(self, tmp_path: Path) -> None:
        (tmp_path / "global.json").write_text('{"sdk": {"version": "8.0.100"}}\n')
        ev = _all_evidence(tmp_path)
        names = {e.runtime_name for e in ev}
        assert ".NET" in names

    def test_php_ecosystem_detected(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text('{"require": {"php": "8.2.12"}}\n')
        ev = _all_evidence(tmp_path)
        names = {e.runtime_name for e in ev}
        assert "PHP" in names
