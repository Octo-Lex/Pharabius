"""Rust runtime evidence parser.

Sources: rust-toolchain, rust-toolchain.toml, Cargo.toml rust-version,
.tool-versions, GitHub Actions dtolnay/rust-toolchain, Dockerfile FROM rust.
"""
from __future__ import annotations

import re
from pathlib import Path

from pharabius.core.io_helpers import read_text
from pharabius.core.runtime.constraints import parse_constraint
from pharabius.core.runtime.ecosystems import _make_id
from pharabius.core.runtime.models import (
    Confidence,
    RuntimeConstraint,
    RuntimeConstraintKind,
    RuntimeEcosystem,
    RuntimeEvidence,
    RuntimeSourceType,
)

_NAMED_CHANNELS = {"stable", "beta", "nightly"}


def detect_rust_sources(root: Path) -> list[RuntimeEvidence]:
    """Detect Rust runtime version sources."""
    evidence: list[RuntimeEvidence] = []

    # rust-toolchain (plain text file, no extension)
    fpath = root / "rust-toolchain"
    if fpath.exists() and not fpath.is_dir():
        text = read_text(fpath)
        if text:
            version = text.strip().split("\n")[0].strip()
            if version:
                evidence.append(_rust_toolchain_evidence(version, "rust-toolchain"))

    # rust-toolchain.toml
    fpath = root / "rust-toolchain.toml"
    if fpath.exists():
        text = read_text(fpath)
        if text:
            # Parse [toolchain] channel = "..." from TOML
            m = re.search(r'^\s*channel\s*=\s*"([^"]+)"', text, re.MULTILINE)
            if m:
                version = m.group(1)
                evidence.append(_rust_toolchain_evidence(version, "rust-toolchain.toml"))

    # Cargo.toml rust-version
    fpath = root / "Cargo.toml"
    if fpath.exists():
        text = read_text(fpath)
        if text:
            m = re.search(r'^\s*rust-version\s*=\s*"([^"]+)"', text, re.MULTILINE)
            if m:
                version = m.group(1)
                constraint = parse_constraint("Rust", version)
                # rust-version is a minimum, always RANGE
                constraint = RuntimeConstraint(
                    kind=RuntimeConstraintKind.RANGE,
                    lower_bound=constraint.value,
                    raw=version,
                )
                evidence.append(RuntimeEvidence(
                    runtime_evidence_id=_make_id("Rust", "Cargo.toml", "rust-version", version),
                    ecosystem=RuntimeEcosystem.RUST,
                    runtime_name="Rust",
                    constraint=constraint,
                    source_type=RuntimeSourceType.MANIFEST,
                    source_path="Cargo.toml",
                    source_detail="rust-version",
                    confidence=Confidence.MEDIUM,
                    raw_version=version,
                ))

    return evidence


def _rust_toolchain_evidence(version: str, source_path: str) -> RuntimeEvidence:
    """Create RuntimeEvidence for a rust-toolchain source."""
    if version.lower() in _NAMED_CHANNELS:
        # Named channels are UNKNOWN — informational, not a pin
        constraint = RuntimeConstraint(
            kind=RuntimeConstraintKind.UNKNOWN,
            raw=version,
        )
        confidence = Confidence.LOW
    else:
        constraint = parse_constraint("Rust", version)
        confidence = Confidence.HIGH

    return RuntimeEvidence(
        runtime_evidence_id=_make_id("Rust", source_path, "channel", version),
        ecosystem=RuntimeEcosystem.RUST,
        runtime_name="Rust",
        constraint=constraint,
        source_type=RuntimeSourceType.VERSION_FILE,
        source_path=source_path,
        confidence=confidence,
        raw_version=version,
    )
