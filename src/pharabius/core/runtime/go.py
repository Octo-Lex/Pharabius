"""Go runtime evidence parser.

Sources: go.mod (go directive + toolchain directive), .tool-versions,
GitHub Actions setup-go, Dockerfile FROM golang.
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
    RuntimeSourceGrade,
    RuntimeSourceType,
)


def detect_go_sources(root: Path) -> list[RuntimeEvidence]:
    """Detect Go runtime version sources."""
    evidence: list[RuntimeEvidence] = []

    # go.mod
    go_mod = root / "go.mod"
    if go_mod.exists():
        text = read_text(go_mod)
        if text:
            evidence.extend(_parse_go_mod(text))

    return evidence


def _parse_go_mod(text: str) -> list[RuntimeEvidence]:
    """Parse go.mod for go and toolchain directives."""
    evidence: list[RuntimeEvidence] = []

    # go directive: compatibility baseline, NOT a full pin
    m = re.search(r"^go\s+(\S+)\s*$", text, re.MULTILINE)
    if m:
        version = m.group(1)
        # go directive is always a compatibility baseline (RANGE)
        # regardless of whether it looks like an exact version
        # go 1.22 means >=1.22 (minimum version), not [1.22, 1.23)
        constraint = RuntimeConstraint(
            kind=RuntimeConstraintKind.RANGE,
            value=version,
            lower_bound=version,
            raw=version,
        )
        evidence.append(RuntimeEvidence(
            runtime_evidence_id=_make_id("Go", "go.mod", "go-directive", version),
            ecosystem=RuntimeEcosystem.GO,
            runtime_name="Go",
            constraint=constraint,
            source_type=RuntimeSourceType.MANIFEST,
            source_path="go.mod",
            source_grade=RuntimeSourceGrade.MANIFEST_RANGE,
            source_detail="go-directive",
            confidence=Confidence.HIGH,
            raw_version=version,
        ))

    # toolchain directive: EXACT pin
    m = re.search(r"^toolchain\s+(go\S+)\s*$", text, re.MULTILINE)
    if m:
        raw = m.group(1)
        # Extract version from "go1.22.4"
        version = re.sub(r"^go", "", raw)
        constraint = parse_constraint("Go", version)
        evidence.append(RuntimeEvidence(
            runtime_evidence_id=_make_id("Go", "go.mod", "toolchain", raw),
            ecosystem=RuntimeEcosystem.GO,
            runtime_name="Go",
            constraint=constraint,
            source_type=RuntimeSourceType.MANIFEST,
            source_path="go.mod",
            source_grade=RuntimeSourceGrade.MANIFEST_PIN,
            source_detail="toolchain",
            confidence=Confidence.HIGH,
            raw_version=raw,
        ))

    return evidence
