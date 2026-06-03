""".NET runtime evidence parser.

Sources: global.json, *.csproj (TargetFramework/TargetFrameworks),
.tool-versions, GitHub Actions setup-dotnet, Dockerfile FROM dotnet.
"""
from __future__ import annotations

import re
from pathlib import Path

from pharabius.core.io_helpers import read_json, read_text
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

_CSProj_EXCLUDED_DIRS = {"bin", "obj", ".git", "node_modules", "dist", "build", "coverage"}


def detect_dotnet_sources(root: Path) -> list[RuntimeEvidence]:
    """Detect .NET runtime version sources."""
    evidence: list[RuntimeEvidence] = []

    # global.json — exact SDK pin
    fpath = root / "global.json"
    if fpath.exists():
        data = read_json(fpath)
        if isinstance(data, dict):
            sdk = data.get("sdk", {})
            version = sdk.get("version") if isinstance(sdk, dict) else None
            if version:
                constraint = parse_constraint(".NET", str(version))
                evidence.append(RuntimeEvidence(
                    runtime_evidence_id=_make_id(".NET", "global.json", "sdk", str(version)),
                    ecosystem=RuntimeEcosystem.DOTNET,
                    runtime_name=".NET",
                    constraint=constraint,
                    source_type=RuntimeSourceType.MANIFEST,
                    source_path="global.json",
                    source_grade=RuntimeSourceGrade.MANIFEST_PIN,
                    source_detail="sdk",
                    confidence=Confidence.HIGH,
                    raw_version=str(version),
                ))

    # .csproj files — bounded recursive, excluding build artifacts
    for csproj in _find_csproj_files(root):
        evidence.extend(_parse_csproj(root, csproj))

    return evidence


def _find_csproj_files(root: Path) -> list[Path]:
    """Find .csproj files with bounded recursion, excluding build dirs."""
    results: list[Path] = []
    for p in root.rglob("*.csproj"):
        # Check if any path component is excluded
        parts = p.relative_to(root).parts
        if any(part in _CSProj_EXCLUDED_DIRS for part in parts):
            continue
        results.append(p)
    return sorted(results)


def _parse_csproj(root: Path, csproj: Path) -> list[RuntimeEvidence]:
    """Parse TargetFramework(s) from a .csproj file."""
    text = read_text(csproj)
    if not text:
        return []

    rel_path = str(csproj.relative_to(root)).replace("\\", "/")
    evidence: list[RuntimeEvidence] = []

    # TargetFrameworks (plural) — multiple targets
    m = re.search(r"<TargetFrameworks>\s*([^<]+)\s*</TargetFrameworks>", text)
    if m:
        targets = [t.strip() for t in m.group(1).split(";") if t.strip()]
        for target in targets:
            evidence.append(_target_framework_evidence(target, rel_path))
        return evidence

    # TargetFramework (singular)
    m = re.search(r"<TargetFramework>\s*([^<]+)\s*</TargetFramework>", text)
    if m:
        target = m.group(1).strip()
        evidence.append(_target_framework_evidence(target, rel_path))

    return evidence


def _target_framework_evidence(target: str, source_path: str) -> RuntimeEvidence:
    """Create evidence for a .NET target framework."""
    # Extract version from net8.0, net9.0, netcoreapp3.1, etc.
    version = re.sub(r"^(net|netcoreapp|netframework)", "", target, flags=re.IGNORECASE)
    # Only set bounds for modern netX.Y monikers (Correction 4)
    m_ver = re.match(r'(\d+)\.(\d+)', version)
    if m_ver:
        major_v, minor_v = int(m_ver.group(1)), int(m_ver.group(2))
        constraint = RuntimeConstraint(
            kind=RuntimeConstraintKind.RANGE,
            value=version,
            lower_bound=f"{major_v}.{minor_v}",
            upper_bound=f"{major_v + 1}.0",
            raw=target,
        )
    else:
        # Legacy monikers: netstandard2.0, netcoreapp3.1, net48 — no bounds
        constraint = RuntimeConstraint(
            kind=RuntimeConstraintKind.RANGE,
            value=version if version else target,
            raw=target,
        )
    return RuntimeEvidence(
        runtime_evidence_id=_make_id(".NET", source_path, "target-framework", target),
        ecosystem=RuntimeEcosystem.DOTNET,
        runtime_name=".NET",
        constraint=constraint,
        source_type=RuntimeSourceType.MANIFEST,
        source_path=source_path,
        source_grade=RuntimeSourceGrade.MANIFEST_RANGE,
        source_detail="target-framework",
        confidence=Confidence.MEDIUM,
        raw_version=target,
    )
