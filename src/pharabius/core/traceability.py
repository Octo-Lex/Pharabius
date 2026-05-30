"""Traceability matrix generation, rendering, and quality assessment.

Generates evidence→finding, finding→claim, and claim→work-package
traceability matrices plus a quality summary with orphan/broken detection.
All outputs are deterministic Markdown or JSON.
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


def compute_traceability_quality(
    evidence_ids: set[str],
    findings: list[dict[str, object]],
    claims: list[OperationalClaim],
    work_packages: list[dict[str, object]],
) -> dict[str, object]:
    """Compute traceability quality metrics.

    Args:
        evidence_ids: Set of all evidence IDs from evidence.json.
        findings: List of finding dicts from debt-register.json.
        claims: List of OperationalClaim objects.
        work_packages: List of work package dicts with package_id and linked_debt_items.
    """
    finding_ids = {str(f.get("id", "")) for f in findings}
    wp_ids = {str(wp.get("package_id", "")) for wp in work_packages}

    # Findings with at least one evidence ID
    findings_with_evidence = sum(
        1 for f in findings if f.get("evidence_ids") and len(f["evidence_ids"]) > 0
    )
    findings_with_evidence_pct = (
        round(findings_with_evidence / len(findings) * 100, 1) if findings else 0.0
    )

    # Claims linked to at least one finding
    claims_with_findings = sum(1 for c in claims if c.linked_findings)
    claims_with_findings_pct = (
        round(claims_with_findings / len(claims) * 100, 1) if claims else 0.0
    )

    # Claims linked to at least one work package
    claims_with_wp = sum(1 for c in claims if c.linked_work_packages)
    claims_with_wp_pct = (
        round(claims_with_wp / len(claims) * 100, 1) if claims else 0.0
    )

    # Work packages linked to at least one finding
    wp_with_findings = sum(
        1 for wp in work_packages
        if wp.get("linked_debt_items") and len(wp["linked_debt_items"]) > 0
    )
    wp_with_findings_pct = (
        round(wp_with_findings / len(work_packages) * 100, 1) if work_packages else 0.0
    )

    # Orphan evidence: not referenced by any finding
    referenced_evidence: set[str] = set()
    for f in findings:
        for eid in (f.get("evidence_ids") or []):
            referenced_evidence.add(str(eid))
    orphan_evidence_count = len(evidence_ids - referenced_evidence)

    # Orphan findings: not linked to any claim
    findings_in_claims: set[str] = set()
    for c in claims:
        for fid in c.linked_findings:
            findings_in_claims.add(fid)
    orphan_finding_count = len(finding_ids - findings_in_claims)

    # Broken references: IDs referenced but not found
    broken_count = 0
    for c in claims:
        for fid in c.linked_findings:
            if fid not in finding_ids:
                broken_count += 1
        for wp_id in (c.linked_work_packages or []):
            if wp_id not in wp_ids:
                broken_count += 1
    for wp in work_packages:
        for debt_id in (wp.get("linked_debt_items") or []):
            if str(debt_id) not in finding_ids:
                broken_count += 1

    # Grade
    if (
        findings_with_evidence_pct >= 95
        and claims_with_wp_pct >= 80
        and broken_count == 0
    ):
        grade = "complete"
    elif (
        findings_with_evidence_pct >= 80
        and claims_with_findings_pct >= 70
        and broken_count == 0
    ):
        grade = "usable"
    elif findings_with_evidence_pct >= 50:
        grade = "partial"
    else:
        grade = "weak"

    return {
        "total_findings": len(findings),
        "total_claims": len(claims),
        "total_work_packages": len(work_packages),
        "total_evidence": len(evidence_ids),
        "findings_with_evidence_pct": findings_with_evidence_pct,
        "claims_with_findings_pct": claims_with_findings_pct,
        "claims_with_work_packages_pct": claims_with_wp_pct,
        "work_packages_with_findings_pct": wp_with_findings_pct,
        "orphan_evidence_count": orphan_evidence_count,
        "orphan_finding_count": orphan_finding_count,
        "broken_reference_count": broken_count,
        "traceability_grade": grade,
    }


def render_traceability_quality_markdown(quality: dict[str, object]) -> str:
    """Render traceability quality as Markdown."""
    lines: list[str] = []
    lines.append("# Traceability Quality Summary")
    lines.append("")

    lines.append("## Grade")
    lines.append("")
    lines.append(f"**{quality['traceability_grade'].toString().upper() if hasattr(quality['traceability_grade'], 'toString') else str(quality['traceability_grade']).upper()}**")
    lines.append("")

    lines.append("## Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    for key in (
        "total_findings",
        "total_claims",
        "total_work_packages",
        "total_evidence",
        "findings_with_evidence_pct",
        "claims_with_findings_pct",
        "claims_with_work_packages_pct",
        "work_packages_with_findings_pct",
        "orphan_evidence_count",
        "orphan_finding_count",
        "broken_reference_count",
    ):
        label = key.replace("_", " ").replace(" pct", " %").title()
        lines.append(f"| {label} | {quality[key]} |")
    lines.append("")

    return "\n".join(lines)


def write_traceability_quality(
    traceability_dir: Path, quality: dict[str, object]
) -> list[Path]:
    """Write traceability quality JSON and Markdown."""
    import json

    traceability_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    json_path = traceability_dir / "traceability-quality.json"
    json_path.write_text(json.dumps(quality, indent=2) + "\n", encoding="utf-8")
    paths.append(json_path)

    md_path = traceability_dir / "traceability-quality.md"
    md_path.write_text(render_traceability_quality_markdown(quality), encoding="utf-8")
    paths.append(md_path)

    return paths
