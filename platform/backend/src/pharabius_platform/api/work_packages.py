"""Work package API — list and detail endpoints."""

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


@router.get("/api/v1/repositories/{repo_id}/work-packages")
async def list_work_packages(
    repo_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    run_id: str | None = Query(None),
) -> dict[str, object]:
    """List work packages for a repository's latest or specified run."""
    try:
        repo_uuid = uuid.UUID(repo_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_repo_id", "message": "Invalid repository ID."},
        ) from None

    # Resolve run
    target_run_id = await _resolve_run_id(session, repo_uuid, run_id)
    if target_run_id is None:
        return {"work_packages": [], "total": 0}

    # Query work packages with link counts
    stmt = (
        select(WorkPackage)
        .where(
            WorkPackage.repository_id == repo_uuid,
            WorkPackage.run_id == target_run_id,
        )
        .options(selectinload(WorkPackage.finding_links))
        .order_by(WorkPackage.package_id)
    )
    result = await session.execute(stmt)
    packages = list(result.scalars().all())

    summaries = []
    for wp in packages:
        links = wp.finding_links or []
        resolved_count = sum(1 for lk in links if lk.resolution_status == "resolved")
        missing_count = sum(1 for lk in links if lk.resolution_status == "missing")

        summaries.append(
            {
                "package_id": wp.package_id,
                "title": wp.title,
                "status": wp.status or "",
                "estimated_effort": wp.estimated_effort or "",
                "linked_finding_count": len(links),
                "resolved_finding_count": resolved_count,
                "missing_finding_count": missing_count,
            }
        )

    return {"work_packages": summaries, "total": len(summaries)}


@router.get("/api/v1/repositories/{repo_id}/work-packages/{package_id}")
async def get_work_package(
    repo_id: str,
    package_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    run_id: str | None = Query(None),
    include_findings: bool = Query(False),
    include_evidence: bool = Query(False),
) -> dict[str, object]:
    """Get a single work package by package_id.

    include_evidence=true implies include_findings=true.
    """
    # If evidence requested, always include findings too
    if include_evidence:
        include_findings = True

    try:
        repo_uuid = uuid.UUID(repo_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_repo_id", "message": "Invalid repository ID."},
        ) from None

    # Resolve run
    target_run_id = await _resolve_run_id(session, repo_uuid, run_id)
    if target_run_id is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "work_package_not_found",
                "message": "Work package not found.",
            },
        ) from None

    # Find work package
    stmt = (
        select(WorkPackage)
        .where(
            WorkPackage.repository_id == repo_uuid,
            WorkPackage.run_id == target_run_id,
            WorkPackage.package_id == package_id,
        )
        .options(selectinload(WorkPackage.finding_links))
    )
    result = await session.execute(stmt)
    wp = result.scalar_one_or_none()

    if wp is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "work_package_not_found",
                "message": f"Work package {package_id} not found.",
            },
        ) from None

    # Build linked findings with optional expansion
    linked_findings = await _resolve_linked_findings(
        session,
        repo_uuid,
        target_run_id,
        wp,
        include_findings=include_findings,
        include_evidence=include_evidence,
    )

    links = wp.finding_links or []
    resolved_count = sum(1 for lk in links if lk.resolution_status == "resolved")
    missing_count = sum(1 for lk in links if lk.resolution_status == "missing")

    return {
        "package_id": wp.package_id,
        "title": wp.title,
        "objective": wp.objective or "",
        "current_risk": wp.current_risk or "",
        "recommended_engineering_approach": wp.recommended_engineering_approach or [],
        "expected_affected_areas": wp.expected_affected_areas or [],
        "preconditions": wp.preconditions or [],
        "verification_recommendations": wp.verification_recommendations or [],
        "risks_and_cautions": wp.risks_and_cautions or [],
        "definition_of_done": wp.definition_of_done or [],
        "estimated_effort": wp.estimated_effort or "",
        "expected_risk_reduction": wp.expected_risk_reduction or "",
        "suggested_owner_area": wp.suggested_owner_area or "",
        "status": wp.status or "",
        "declared_evidence_ids": wp.declared_evidence_ids or [],
        "linked_finding_count": len(links),
        "resolved_finding_count": resolved_count,
        "missing_finding_count": missing_count,
        "linked_findings": linked_findings,
    }


async def _resolve_run_id(
    session: AsyncSession, repo_uuid: uuid.UUID, run_id: str | None
) -> uuid.UUID | None:
    """Resolve target run ID from explicit param or latest run."""
    if run_id is not None:
        try:
            return uuid.UUID(run_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={"code": "invalid_run_id", "message": "Invalid run ID."},
            ) from None

    # Latest run
    stmt = (
        select(Run.id)
        .where(Run.repository_id == repo_uuid)
        .order_by(Run.run_timestamp.desc(), Run.id.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return row


async def _resolve_linked_findings(
    session: AsyncSession,
    repo_uuid: uuid.UUID,
    run_id: uuid.UUID,
    wp: WorkPackage,
    include_findings: bool,
    include_evidence: bool,
) -> list[dict[str, object]]:
    """Resolve linked findings for a work package.

    If include_findings is False, returns status only (finding=null).
    If include_findings is True, adds compact finding bodies.
    If include_evidence is True (implies include_findings), adds evidence references.
    """
    # Batch-load all findings for this run if needed
    findings_by_id: dict[uuid.UUID, Finding] = {}
    if include_findings:
        stmt = select(Finding).where(
            Finding.run_id == run_id,
        )
        result = await session.execute(stmt)
        for f in result.scalars():
            findings_by_id[f.id] = f

    # Batch-load evidence if needed
    evidence_by_id: dict[str, dict[str, object]] = {}
    if include_evidence:
        stmt = select(EvidenceRecord).where(
            EvidenceRecord.repository_id == repo_uuid,
            EvidenceRecord.run_id == run_id,
        )
        result = await session.execute(stmt)
        for ev in result.scalars():
            evidence_by_id[ev.evidence_id] = {
                "evidence_id": ev.evidence_id,
                "source": ev.source,
                "type": ev.type,
                "category": ev.category,
                "summary": ev.summary,
                "file_path": ev.file_path or None,
                "line_start": ev.line_start,
                "line_end": ev.line_end,
                "confidence": ev.confidence,
            }

    links = wp.finding_links or []
    result_list: list[dict[str, object]] = []

    for link in links:
        entry: dict[str, object] = {
            "debt_item_id": link.debt_item_id,
            "status": link.resolution_status,
            "reason": link.reason,
            "finding": None,
            "evidence_references": [],
        }

        if include_findings and link.finding_id is not None:
            finding = findings_by_id.get(link.finding_id)
            if finding is not None:
                entry["finding"] = {
                    "finding_id": finding.finding_id,
                    "title": finding.title,
                    "severity": finding.severity,
                    "confidence": finding.confidence or "Medium",
                    "category": finding.category,
                }

                if include_evidence:
                    ev_ids = finding.evidence_ids or []
                    refs: list[dict[str, object]] = []
                    for eid in ev_ids:
                        ev_record = evidence_by_id.get(eid)
                        if ev_record is not None:
                            refs.append(
                                {
                                    "evidence_id": eid,
                                    "status": "resolved",
                                    "evidence": ev_record,
                                }
                            )
                        else:
                            refs.append(
                                {
                                    "evidence_id": eid,
                                    "status": "missing",
                                    "reason": ("Evidence record not found in this run."),
                                }
                            )
                    entry["evidence_references"] = refs

        result_list.append(entry)

    return result_list
