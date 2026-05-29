"""Run comparison API — deterministic delta between two audit runs."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from pharabius_platform.db import get_session
from pharabius_platform.models import (
    EvidenceRecord,
    Finding,
    Run,
    WorkPackage,
)

router = APIRouter()

# --- Canonical comparison helpers ---


def _norm_str(val: str | None) -> str:
    """Normalize string: trim, None → empty."""
    if val is None:
        return ""
    return val.strip()


def _norm_list(val: list | None) -> list[str]:
    """Normalize list: None → [], sort for deterministic comparison."""
    if val is None:
        return []
    return sorted(val)


def _canonicalize_finding(finding: Finding) -> dict[str, object]:
    """Convert Finding ORM to deterministic dict for comparison."""
    return {
        "title": _norm_str(finding.title),
        "category": _norm_str(finding.category),
        "issue_type": _norm_str(finding.issue_type),
        "description": _norm_str(finding.description),
        "severity": _norm_str(finding.severity),
        "confidence": _norm_str(finding.confidence),
        "risk_score": finding.risk_score or 0,
        "priority": _norm_str(finding.priority),
        "locations": _norm_list(finding.locations),
        "evidence_ids": _norm_list(finding.evidence_ids),
    }


def _canonicalize_work_package(
    wp: WorkPackage,
    linked_debt_ids: list[str],
) -> dict[str, object]:
    """Convert WorkPackage ORM to deterministic dict for comparison."""
    return {
        "title": _norm_str(wp.title),
        "objective": _norm_str(wp.objective),
        "current_risk": _norm_str(wp.current_risk),
        "estimated_effort": _norm_str(wp.estimated_effort),
        "expected_risk_reduction": _norm_str(wp.expected_risk_reduction),
        "suggested_owner_area": _norm_str(wp.suggested_owner_area),
        "status": _norm_str(wp.status),
        "recommended_engineering_approach": _norm_list(wp.recommended_engineering_approach),
        "expected_affected_areas": _norm_list(wp.expected_affected_areas),
        "preconditions": _norm_list(wp.preconditions),
        "verification_recommendations": _norm_list(wp.verification_recommendations),
        "risks_and_cautions": _norm_list(wp.risks_and_cautions),
        "definition_of_done": _norm_list(wp.definition_of_done),
        "declared_evidence_ids": _norm_list(wp.declared_evidence_ids),
        "linked_debt_item_ids": sorted(linked_debt_ids),
    }


def _finding_summary(finding: Finding) -> dict[str, object]:
    """Compact finding data for delta response."""
    return {
        "finding_id": finding.finding_id,
        "title": _norm_str(finding.title),
        "category": _norm_str(finding.category),
        "severity": _norm_str(finding.severity),
        "confidence": _norm_str(finding.confidence),
        "risk_score": finding.risk_score or 0,
        "priority": _norm_str(finding.priority),
        "evidence_ids": _norm_list(finding.evidence_ids),
    }


def _wp_summary(
    wp: WorkPackage,
    resolved_count: int,
    missing_count: int,
) -> dict[str, object]:
    """Compact work package data for delta response."""
    return {
        "package_id": wp.package_id,
        "title": _norm_str(wp.title),
        "status": _norm_str(wp.status),
        "estimated_effort": _norm_str(wp.estimated_effort),
        "declared_evidence_count": len(wp.declared_evidence_ids or []),
        "linked_finding_count": resolved_count + missing_count,
        "resolved_finding_count": resolved_count,
        "missing_finding_count": missing_count,
    }


# --- Delta engines ---


def _compute_changed_fields(
    baseline_canon: dict, comparison_canon: dict
) -> list[str]:
    """Return list of field names that differ between canonical dicts."""
    changed = []
    for key in baseline_canon:
        if baseline_canon[key] != comparison_canon[key]:
            changed.append(key)
    return changed


def _traceability_status(
    baseline_unresolved: int,
    comparison_unresolved: int,
    baseline_resolved: int,
    comparison_resolved: int,
) -> str:
    """Compute traceability status from resolved/unresolved counts."""
    if comparison_unresolved < baseline_unresolved:
        return "improved"
    if comparison_unresolved > baseline_unresolved:
        return "regressed"
    if comparison_resolved > baseline_resolved:
        return "improved"
    return "unchanged"


def _compute_findings_delta(
    baseline_findings: list[Finding],
    comparison_findings: list[Finding],
    baseline_evidence_ids: set[str],
    comparison_evidence_ids: set[str],
) -> tuple[list[dict], dict[str, int]]:
    """Compute finding deltas and summary counts."""
    baseline_by_fid = {f.finding_id: f for f in baseline_findings}
    comparison_by_fid = {f.finding_id: f for f in comparison_findings}

    baseline_ids = set(baseline_by_fid.keys())
    comparison_ids = set(comparison_by_fid.keys())

    added_ids = comparison_ids - baseline_ids
    removed_ids = baseline_ids - comparison_ids
    common_ids = baseline_ids & comparison_ids

    deltas = []
    counts = {"added": 0, "removed": 0, "changed": 0, "unchanged": 0}

    # Added
    for fid in sorted(added_ids):
        f = comparison_by_fid[fid]
        deltas.append({
            "finding_id": fid,
            "status": "added",
            "baseline": None,
            "comparison": _finding_summary(f),
            "changed_fields": [],
            "traceability_change": None,
        })
        counts["added"] += 1

    # Removed
    for fid in sorted(removed_ids):
        f = baseline_by_fid[fid]
        deltas.append({
            "finding_id": fid,
            "status": "removed",
            "baseline": _finding_summary(f),
            "comparison": None,
            "changed_fields": [],
            "traceability_change": None,
        })
        counts["removed"] += 1

    # Common (changed or unchanged)
    for fid in sorted(common_ids):
        bf = baseline_by_fid[fid]
        cf = comparison_by_fid[fid]

        b_canon = _canonicalize_finding(bf)
        c_canon = _canonicalize_finding(cf)
        changed_fields = _compute_changed_fields(b_canon, c_canon)
        status = "changed" if changed_fields else "unchanged"
        # Traceability change for this finding
        b_ev = set(_norm_list(bf.evidence_ids))
        c_ev = set(_norm_list(cf.evidence_ids))
        b_resolved = len(b_ev & baseline_evidence_ids)
        c_resolved = len(c_ev & comparison_evidence_ids)
        b_unresolved = len(b_ev) - b_resolved
        c_unresolved = len(c_ev) - c_resolved

        t_status = _traceability_status(b_unresolved, c_unresolved, b_resolved, c_resolved)

        deltas.append({
            "finding_id": fid,
            "status": status,
            "baseline": _finding_summary(bf),
            "comparison": _finding_summary(cf),
            "changed_fields": changed_fields,
            "traceability_change": {
                "baseline_evidence_ids": len(b_ev),
                "comparison_evidence_ids": len(c_ev),
                "baseline_resolved": b_resolved,
                "comparison_resolved": c_resolved,
                "status": t_status,
            },
        })
        counts[status] += 1

    return deltas, counts


def _compute_wp_delta(
    baseline_wps: list[WorkPackage],
    comparison_wps: list[WorkPackage],
) -> tuple[list[dict], dict[str, int]]:
    """Compute work package deltas and summary counts."""
    baseline_by_pid: dict[str, tuple[WorkPackage, list[str], int, int]] = {}
    for wp in baseline_wps:
        links = wp.finding_links or []
        debt_ids = [lk.debt_item_id for lk in links]
        resolved = sum(1 for lk in links if lk.resolution_status == "resolved")
        missing = sum(1 for lk in links if lk.resolution_status == "missing")
        baseline_by_pid[wp.package_id] = (wp, debt_ids, resolved, missing)

    comparison_by_pid: dict[str, tuple[WorkPackage, list[str], int, int]] = {}
    for wp in comparison_wps:
        links = wp.finding_links or []
        debt_ids = [lk.debt_item_id for lk in links]
        resolved = sum(1 for lk in links if lk.resolution_status == "resolved")
        missing = sum(1 for lk in links if lk.resolution_status == "missing")
        comparison_by_pid[wp.package_id] = (wp, debt_ids, resolved, missing)

    baseline_ids = set(baseline_by_pid.keys())
    comparison_ids = set(comparison_by_pid.keys())

    added_ids = comparison_ids - baseline_ids
    removed_ids = baseline_ids - comparison_ids
    common_ids = baseline_ids & comparison_ids

    deltas = []
    counts = {"added": 0, "removed": 0, "changed": 0, "unchanged": 0}

    for pid in sorted(added_ids):
        wp, _, resolved, missing = comparison_by_pid[pid]
        deltas.append({
            "package_id": pid,
            "status": "added",
            "baseline": None,
            "comparison": _wp_summary(wp, resolved, missing),
            "changed_fields": [],
            "traceability_change": None,
        })
        counts["added"] += 1

    for pid in sorted(removed_ids):
        wp, _, resolved, missing = baseline_by_pid[pid]
        deltas.append({
            "package_id": pid,
            "status": "removed",
            "baseline": _wp_summary(wp, resolved, missing),
            "comparison": None,
            "changed_fields": [],
            "traceability_change": None,
        })
        counts["removed"] += 1

    for pid in sorted(common_ids):
        b_wp, b_debt_ids, b_resolved, b_missing = baseline_by_pid[pid]
        c_wp, c_debt_ids, c_resolved, c_missing = comparison_by_pid[pid]

        b_canon = _canonicalize_work_package(b_wp, b_debt_ids)
        c_canon = _canonicalize_work_package(c_wp, c_debt_ids)
        changed_fields = _compute_changed_fields(b_canon, c_canon)
        status = "changed" if changed_fields else "unchanged"
        t_status = _traceability_status(
            b_missing, c_missing, b_resolved, c_resolved
        )

        deltas.append({
            "package_id": pid,
            "status": status,
            "baseline": _wp_summary(b_wp, b_resolved, b_missing),
            "comparison": _wp_summary(c_wp, c_resolved, c_missing),
            "changed_fields": changed_fields,
            "traceability_change": {
                "baseline_resolved_links": b_resolved,
                "comparison_resolved_links": c_resolved,
                "baseline_missing_links": b_missing,
                "comparison_missing_links": c_missing,
                "status": t_status,
            },
        })
        counts[status] += 1

    return deltas, counts


def _compute_traceability_delta(
    baseline_findings: list[Finding],
    comparison_findings: list[Finding],
    baseline_evidence_ids: set[str],
    comparison_evidence_ids: set[str],
    baseline_wps: list[WorkPackage],
    comparison_wps: list[WorkPackage],
) -> dict[str, object]:
    """Compute traceability coverage delta."""
    # Evidence references
    b_all_ev: set[str] = set()
    for f in baseline_findings:
        b_all_ev.update(_norm_list(f.evidence_ids))
    c_all_ev: set[str] = set()
    for f in comparison_findings:
        c_all_ev.update(_norm_list(f.evidence_ids))

    b_unique_count = len(b_all_ev)
    c_unique_count = len(c_all_ev)
    b_resolved = len(b_all_ev & baseline_evidence_ids)
    c_resolved = len(c_all_ev & comparison_evidence_ids)
    b_unresolved = b_unique_count - b_resolved
    c_unresolved = c_unique_count - c_resolved

    # Determine status
    if b_unique_count == 0 and c_unique_count == 0:
        ev_status = "unchanged"
    elif not baseline_evidence_ids and not comparison_evidence_ids:
        # No evidence store in either run
        ev_status = ("unchanged" if b_unique_count == 0 and c_unique_count == 0 else "unavailable")
    else:
        ev_status = _traceability_status(
            b_unresolved, c_unresolved, b_resolved, c_resolved
        )

    # Work package linkage
    b_total_links = 0
    b_resolved_links = 0
    b_missing_links = 0
    for wp in baseline_wps:
        links = wp.finding_links or []
        b_total_links += len(links)
        b_resolved_links += sum(1 for lk in links if lk.resolution_status == "resolved")
        b_missing_links += sum(1 for lk in links if lk.resolution_status == "missing")

    c_total_links = 0
    c_resolved_links = 0
    c_missing_links = 0
    for wp in comparison_wps:
        links = wp.finding_links or []
        c_total_links += len(links)
        c_resolved_links += sum(1 for lk in links if lk.resolution_status == "resolved")
        c_missing_links += sum(1 for lk in links if lk.resolution_status == "missing")

    wp_status = _traceability_status(
        b_missing_links, c_missing_links, b_resolved_links, c_resolved_links
    )

    return {
        "evidence": {
            "baseline_unique_evidence_id_count": b_unique_count,
            "comparison_unique_evidence_id_count": c_unique_count,
            "baseline_resolved_unique": b_resolved,
            "comparison_resolved_unique": c_resolved,
            "baseline_unresolved_unique": b_unresolved,
            "comparison_unresolved_unique": c_unresolved,
            "status": ev_status,
        },
        "work_package_links": {
            "baseline_total": b_total_links,
            "comparison_total": c_total_links,
            "baseline_resolved": b_resolved_links,
            "comparison_resolved": c_resolved_links,
            "baseline_missing": b_missing_links,
            "comparison_missing": c_missing_links,
            "status": wp_status,
        },
    }


# --- Endpoint ---


@router.get("/api/v1/repositories/{repo_id}/runs/compare")
async def compare_runs(
    repo_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    baseline_run_id: str = Query(..., description="Baseline run UUID"),
    comparison_run_id: str = Query(..., description="Comparison run UUID"),
    include_findings: bool = Query(True),
    include_work_packages: bool = Query(True),
    include_traceability: bool = Query(True),
) -> dict[str, object]:
    """Compare two audit runs from the same repository.

    Same-run comparison is allowed (returns all unchanged).
    """
    try:
        repo_uuid = uuid.UUID(repo_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_repo_id", "message": "Invalid repository ID."},
        ) from None

    try:
        baseline_uuid = uuid.UUID(baseline_run_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_baseline_run_id", "message": "Invalid baseline run ID."},
        ) from None

    try:
        comparison_uuid = uuid.UUID(comparison_run_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_comparison_run_id", "message": "Invalid comparison run ID."},
        ) from None

    # Fetch runs — must belong to this repository
    stmt = select(Run).where(
        Run.repository_id == repo_uuid,
        Run.id.in_([baseline_uuid, comparison_uuid]),
    )
    result = await session.execute(stmt)
    runs = {r.id: r for r in result.scalars().all()}

    if baseline_uuid not in runs:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "baseline_not_found",
                "message": "Baseline run not found in this repository.",
            },
        ) from None

    if comparison_uuid not in runs:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "comparison_not_found",
                "message": "Comparison run not found in this repository.",
            },
        ) from None

    baseline_run = runs[baseline_uuid]
    comparison_run = runs[comparison_uuid]

    # Run info
    def _run_info(r: Run) -> dict[str, object]:
        return {
            "id": str(r.id),
            "run_id": r.run_id,
            "run_timestamp": r.run_timestamp.isoformat() if r.run_timestamp else None,
            "commit_sha": r.commit_sha or "",
            "branch_name": r.branch_name or "",
            "analysis_mode": r.analysis_mode or "",
        }

    response: dict[str, object] = {
        "repository_id": str(repo_uuid),
        "baseline_run": _run_info(baseline_run),
        "comparison_run": _run_info(comparison_run),
    }

    # Fetch findings for both runs
    stmt_f = select(Finding).where(
        Finding.run_id.in_([baseline_uuid, comparison_uuid]),
    )
    result_f = await session.execute(stmt_f)
    all_findings = list(result_f.scalars().all())
    baseline_findings = [f for f in all_findings if f.run_id == baseline_uuid]
    comparison_findings = [f for f in all_findings if f.run_id == comparison_uuid]

    # Fetch evidence records for both runs
    stmt_ev = select(EvidenceRecord.evidence_id).where(
        EvidenceRecord.run_id.in_([baseline_uuid, comparison_uuid]),
    )
    result_ev = await session.execute(stmt_ev)
    ev_rows = result_ev.all()
    baseline_evidence_ids = {
        row[0] for row in ev_rows
        # We need to filter by run, but we fetched both. Let's fix this.
    }

    # Actually fetch with run_id distinction
    stmt_bev = select(EvidenceRecord.evidence_id).where(
        EvidenceRecord.run_id == baseline_uuid,
    )
    result_bev = await session.execute(stmt_bev)
    baseline_evidence_ids = {row[0] for row in result_bev.all()}

    stmt_cev = select(EvidenceRecord.evidence_id).where(
        EvidenceRecord.run_id == comparison_uuid,
    )
    result_cev = await session.execute(stmt_cev)
    comparison_evidence_ids = {row[0] for row in result_cev.all()}

    # Fetch work packages for both runs
    stmt_wp = (
        select(WorkPackage)
        .where(WorkPackage.run_id.in_([baseline_uuid, comparison_uuid]))
        .options(selectinload(WorkPackage.finding_links))
    )
    result_wp = await session.execute(stmt_wp)
    all_wps = list(result_wp.scalars().all())
    baseline_wps = [wp for wp in all_wps if wp.run_id == baseline_uuid]
    comparison_wps = [wp for wp in all_wps if wp.run_id == comparison_uuid]

    # Findings delta
    findings_delta: list[dict] = []
    findings_counts = {"added": 0, "removed": 0, "changed": 0, "unchanged": 0}

    if include_findings:
        findings_delta, findings_counts = _compute_findings_delta(
            baseline_findings, comparison_findings,
            baseline_evidence_ids, comparison_evidence_ids,
        )

    # Work packages delta
    wp_delta: list[dict] = []
    wp_counts = {"added": 0, "removed": 0, "changed": 0, "unchanged": 0}

    if include_work_packages:
        wp_delta, wp_counts = _compute_wp_delta(baseline_wps, comparison_wps)

    # Traceability delta
    traceability_delta: dict[str, object] = {}

    if include_traceability:
        traceability_delta = _compute_traceability_delta(
            baseline_findings, comparison_findings,
            baseline_evidence_ids, comparison_evidence_ids,
            baseline_wps, comparison_wps,
        )

    # Summary (always computed)
    response["summary"] = {
        "findings": {
            "baseline_total": len(baseline_findings),
            "comparison_total": len(comparison_findings),
            **findings_counts,
        },
        "work_packages": {
            "baseline_total": len(baseline_wps),
            "comparison_total": len(comparison_wps),
            **wp_counts,
        },
    }
    response["findings_delta"] = findings_delta
    response["work_packages_delta"] = wp_delta
    response["traceability_delta"] = traceability_delta

    return response
