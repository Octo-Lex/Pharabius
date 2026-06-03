"""v3.10.0 S04 — Rust runtime evidence tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from pharabius.core.runtime.rust import detect_rust_sources
from pharabius.core.runtime.models import RuntimeConstraintKind, RuntimeEcosystem


class TestRustSources:
    def test_rust_toolchain_exact(self, tmp_path: Path) -> None:
        (tmp_path / "rust-toolchain").write_text("1.76.0\n")
        evidence = detect_rust_sources(tmp_path)
        assert len(evidence) == 1
        assert evidence[0].constraint.kind == RuntimeConstraintKind.EXACT
        assert evidence[0].raw_version == "1.76.0"

    def test_rust_toolchain_toml_exact(self, tmp_path: Path) -> None:
        (tmp_path / "rust-toolchain.toml").write_text('[toolchain]\nchannel = "1.76.0"\n')
        evidence = detect_rust_sources(tmp_path)
        assert len(evidence) == 1
        assert evidence[0].constraint.kind == RuntimeConstraintKind.EXACT

    def test_rust_toolchain_toml_stable_is_unknown(self, tmp_path: Path) -> None:
        (tmp_path / "rust-toolchain.toml").write_text('[toolchain]\nchannel = "stable"\n')
        evidence = detect_rust_sources(tmp_path)
        assert len(evidence) == 1
        assert evidence[0].constraint.kind == RuntimeConstraintKind.UNKNOWN

    def test_cargo_toml_rust_version_is_range(self, tmp_path: Path) -> None:
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "test"\nrust-version = "1.76"\n')
        evidence = detect_rust_sources(tmp_path)
        assert len(evidence) == 1
        assert evidence[0].constraint.kind == RuntimeConstraintKind.RANGE
        assert evidence[0].source_detail == "rust-version"

    def test_beta_is_unknown(self, tmp_path: Path) -> None:
        (tmp_path / "rust-toolchain").write_text("beta\n")
        evidence = detect_rust_sources(tmp_path)
        assert len(evidence) == 1
        assert evidence[0].constraint.kind == RuntimeConstraintKind.UNKNOWN

    def test_nightly_is_unknown(self, tmp_path: Path) -> None:
        (tmp_path / "rust-toolchain").write_text("nightly\n")
        evidence = detect_rust_sources(tmp_path)
        assert evidence[0].constraint.kind == RuntimeConstraintKind.UNKNOWN

    def test_no_rust_files_returns_empty(self, tmp_path: Path) -> None:
        evidence = detect_rust_sources(tmp_path)
        assert evidence == []
