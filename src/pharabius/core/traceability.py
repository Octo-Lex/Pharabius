"""Traceability matrix generation and rendering.

Generates evidence→finding, finding→claim, and claim→work-package
traceability matrices. All outputs are deterministic Markdown tables.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from pharabius.schemas.claims import OperationalClaim


def render_evidence_finding_matrix(
    findings: list[dict[str, object]],
) -> str:
    """Render evidence → finding traceability matrix."""
    lines: list[str] = []
    lines.append("# Evidence → Finding Matrix")
    lines.append("")

    if not findings:
        lines.append("No findings to trace.")
        lines.append("")
        return "\n".join(lines)

    # Build evidence→findings map
    ev_map: dict[str, list[str]] = {}
    for f in findings:
        fid = str(f.get("id", ""))
        eids = cast("list[object]", f.get("evidence_ids") or [])
        for eid_raw in eids:
            eid = str(eid_raw)
            ev_map.setdefault(eid, []).append(fid)

    if not ev_map:
        lines.append("No evidence links found.")
        lines.append("")
        return "\n".join(lines)

    lines.append("| Evidence ID | Finding IDs |")
    lines.append("|---|---|")
    for eid in sorted(ev_map):
        fids = ", ".join(sorted(ev_map[eid]))
        lines.append(f"| {eid} | {fids} |")
    lines.append("")

    return "\n".join(lines)


def render_finding_claim_matrix(
    findings: list[dict[str, object]],
    claims: list[OperationalClaim],
) -> str:
    """Render finding → claim traceability matrix."""
    lines: list[str] = []
    lines.append("# Finding → Claim Matrix")
    lines.append("")

    if not findings:
        lines.append("No findings to trace.")
        lines.append("")
        return "\n".join(lines)

    # Build finding→claims map
    fc_map: dict[str, list[OperationalClaim]] = {}
    for c in claims:
        for fid in c.linked_findings:
            fc_map.setdefault(fid, []).append(c)

    # Check for findings without claims
    warnings: list[str] = []
    for f in findings:
        fid = str(f.get("id", ""))
        if fid not in fc_map:
            warnings.append(f"Finding {fid} has no generated claim")

    if fc_map:
        lines.append("| Finding ID | Claim IDs | Claim Statuses | Gap Count |")
        lines.append("|---|---|---|---:|")
        for fid in sorted(fc_map):
            cs = fc_map[fid]
            claim_ids = ", ".join(c.claim_id for c in sorted(cs, key=lambda x: x.claim_id))
            statuses = ", ".join(c.status for c in sorted(cs, key=lambda x: x.claim_id))
            gaps = sum(1 for c in cs if c.status == "gap")
            lines.append(f"| {fid} | {claim_ids} | {statuses} | {gaps} |")
        lines.append("")

    if warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in sorted(warnings):
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)


def render_claim_workpackage_matrix(
    claims: list[OperationalClaim],
) -> str:
    """Render claim → work package traceability matrix."""
    lines: list[str] = []
    lines.append("# Claim → Work Package Matrix")
    lines.append("")

    if not claims:
        lines.append("No claims to trace.")
        lines.append("")
        return "\n".join(lines)

    lines.append("| Claim ID | Work Package IDs | Status | Human Validation |")
    lines.append("|---|---|---|---|")
    for c in sorted(claims, key=lambda x: x.claim_id):
        wps = ", ".join(c.linked_work_packages) if c.linked_work_packages else "—"
        hv = "yes" if c.requires_human_validation else "no"
        lines.append(f"| {c.claim_id} | {wps} | {c.status} | {hv} |")
    lines.append("")

    # Warn about blocking gaps in work packages
    blocking = [c for c in claims if c.status == "gap" and c.linked_work_packages]
    if blocking:
        lines.append("## Warnings")
        lines.append("")
        for c in blocking:
            wps = ", ".join(c.linked_work_packages)
            lines.append(f"- {c.claim_id}: blocking gap linked to work package(s) {wps}")
        lines.append("")

    return "\n".join(lines)


def write_traceability_matrices(
    traceability_dir: Path,
    findings: list[dict[str, object]],
    claims: list[OperationalClaim],
) -> list[Path]:
    """Write all three traceability matrices to disk."""
    traceability_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    p1 = traceability_dir / "evidence-finding-matrix.md"
    p1.write_text(render_evidence_finding_matrix(findings), encoding="utf-8")
    paths.append(p1)

    p2 = traceability_dir / "finding-claim-matrix.md"
    p2.write_text(render_finding_claim_matrix(findings, claims), encoding="utf-8")
    paths.append(p2)

    p3 = traceability_dir / "claim-workpackage-matrix.md"
    p3.write_text(render_claim_workpackage_matrix(claims), encoding="utf-8")
    paths.append(p3)

    return paths
