"""Repository and findings API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pharabius_platform.db import get_session
from pharabius_platform.models import EvidenceRecord, Finding, Repository, Run

router = APIRouter(tags=["repositories"])


@router.get("/api/v1/repositories")
async def list_repositories(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    """List all repositories with latest run summary."""
    # Get all repos
    result = await session.execute(select(Repository).order_by(Repository.last_uploaded_at.desc()))
    repos = result.scalars().all()

    items = []
    for repo in repos:
        # Get latest run
        run_result = await session.execute(
            select(Run)
            .where(Run.repository_id == repo.id)
            .order_by(Run.run_timestamp.desc())
            .limit(1)
        )
        latest_run = run_result.scalar_one_or_none()

        items.append(
            {
                "id": str(repo.id),
                "name": repo.name,
                "slug": repo.slug,
                "vcs_url": repo.vcs_url,
                "last_uploaded_at": repo.last_uploaded_at.isoformat()
                if repo.last_uploaded_at
                else None,
                "latest_run": _run_summary(latest_run) if latest_run else None,
            }
        )

    return {"repositories": items, "total": len(items)}


@router.get("/api/v1/repositories/{repo_id}")
async def get_repository(
    repo_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    """Get repository detail with latest run summary."""
    from uuid import UUID

    try:
        repo_uuid = UUID(repo_id)
    except ValueError:
        return {"error": {"code": "invalid_id", "message": "Invalid repository ID"}}

    result = await session.execute(select(Repository).where(Repository.id == repo_uuid))
    repo = result.scalar_one_or_none()
    if repo is None:
        return {"error": {"code": "not_found", "message": "Repository not found"}}

    # Latest run
    run_result = await session.execute(
        select(Run).where(Run.repository_id == repo.id).order_by(Run.run_timestamp.desc()).limit(1)
    )
    latest_run = run_result.scalar_one_or_none()

    # Run count
    count_result = await session.execute(select(func.count()).where(Run.repository_id == repo.id))
    run_count = count_result.scalar() or 0

    return {
        "id": str(repo.id),
        "name": repo.name,
        "slug": repo.slug,
        "vcs_url": repo.vcs_url,
        "default_branch": repo.default_branch,
        "last_uploaded_at": repo.last_uploaded_at.isoformat() if repo.last_uploaded_at else None,
        "run_count": run_count,
        "latest_run": _run_summary(latest_run) if latest_run else None,
    }


@router.get("/api/v1/repositories/{repo_id}/findings")
async def list_findings(
    repo_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    severity: str | None = None,
    category: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> dict[str, object]:
    """List findings for a repository with optional filters."""
    from uuid import UUID

    try:
        repo_uuid = UUID(repo_id)
    except ValueError:
        return {"error": {"code": "invalid_id", "message": "Invalid repository ID"}}

    # Get latest run for this repo
    run_result = await session.execute(
        select(Run)
        .where(Run.repository_id == repo_uuid)
        .order_by(Run.run_timestamp.desc())
        .limit(1)
    )
    latest_run = run_result.scalar_one_or_none()
    if latest_run is None:
        return {"findings": [], "total": 0, "page": page, "page_size": page_size}

    # Build query
    query = select(Finding).where(Finding.run_id == latest_run.id)

    if severity:
        query = query.where(Finding.severity == severity)
    if category:
        query = query.where(Finding.category == category)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    # Paginate
    query = query.order_by(Finding.risk_score.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    findings = result.scalars().all()

    items = [
        {
            "id": str(f.id),
            "finding_id": f.finding_id,
            "category": f.category,
            "issue_type": f.issue_type,
            "title": f.title,
            "description": f.description or "",
            "severity": f.severity,
            "confidence": f.confidence,
            "risk_score": f.risk_score,
            "priority": f.priority,
            "locations": f.locations,
            "evidence_ids": f.evidence_ids,
        }
        for f in findings
    ]

    return {
        "findings": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/api/v1/repositories/{repo_id}/runs")
async def list_runs(
    repo_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    """List run history for a repository."""
    from uuid import UUID

    try:
        repo_uuid = UUID(repo_id)
    except ValueError:
        return {"error": {"code": "invalid_id", "message": "Invalid repository ID"}}

    result = await session.execute(
        select(Run).where(Run.repository_id == repo_uuid).order_by(Run.run_timestamp.desc())
    )
    runs = result.scalars().all()

    items = [_run_summary(r) for r in runs]
    return {"runs": items, "total": len(items)}


@router.get("/api/v1/repositories/{repo_id}/latest-run")
async def get_latest_run(
    repo_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    """Get latest run summary for a repository."""
    from uuid import UUID

    try:
        repo_uuid = UUID(repo_id)
    except ValueError:
        return {"error": {"code": "invalid_id", "message": "Invalid repository ID"}}

    result = await session.execute(
        select(Run)
        .where(Run.repository_id == repo_uuid)
        .order_by(Run.run_timestamp.desc())
        .limit(1)
    )
    run = result.scalar_one_or_none()

    if run is None:
        return {"run": None}
    return {"run": _run_summary(run)}


def _run_summary(run: Run) -> dict[str, object]:
    """Convert a Run to a summary dict."""
    return {
        "id": str(run.id),
        "run_id": run.run_id,
        "pharabius_version": run.pharabius_version,
        "run_timestamp": run.run_timestamp.isoformat() if run.run_timestamp else None,
        "total_findings": run.total_findings,
        "critical": run.critical,
        "high": run.high,
        "medium": run.medium,
        "low": run.low,
        "readiness_status": run.readiness_status,
        "gate_result": run.gate_result,
    }


@router.get("/api/v1/repositories/{repo_id}/findings/{finding_id}")
async def get_finding(
    repo_id: str,
    finding_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    include_evidence: bool = False,
) -> dict[str, object]:
    """Get a single finding by finding_id for a repository's latest run.

    ?include_evidence=true adds resolved evidence records.
    Evidence resolution always uses the finding's own run_id.
    """
    from uuid import UUID

    try:
        repo_uuid = UUID(repo_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_id", "message": "Invalid repository ID"},
        ) from None

    # Get latest run for this repo
    run_result = await session.execute(
        select(Run)
        .where(Run.repository_id == repo_uuid)
        .order_by(Run.run_timestamp.desc())
        .limit(1)
    )
    latest_run = run_result.scalar_one_or_none()
    if latest_run is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "No runs found for repository"},
        )

    # Find by finding_id (not UUID)
    result = await session.execute(
        select(Finding).where(
            Finding.run_id == latest_run.id,
            Finding.finding_id == finding_id,
        )
    )
    finding = result.scalar_one_or_none()
    if finding is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "finding_not_found",
                "message": f"Finding {finding_id} not found.",
                "finding_id": finding_id,
            },
        )

    # Resolve evidence references (always using finding's run_id)
    evidence_references = await _resolve_evidence(
        session, repo_uuid, finding.run_id, finding.evidence_ids, include_evidence
    )

    return {
        "id": str(finding.id),
        "finding_id": finding.finding_id,
        "category": finding.category,
        "issue_type": finding.issue_type,
        "title": finding.title,
        "description": finding.description or "",
        "severity": finding.severity,
        "confidence": finding.confidence,
        "risk_score": finding.risk_score,
        "priority": finding.priority,
        "locations": finding.locations,
        "evidence_ids": finding.evidence_ids,
        "evidence_references": evidence_references,
    }


@router.get("/api/v1/repositories/{repo_id}/evidence/{evidence_id}")
async def get_evidence(
    repo_id: str,
    evidence_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    run_id: str | None = None,
) -> dict[str, object]:
    """Get a single evidence record by evidence_id.

    By default scopes to latest run. Optional ?run_id= scopes to specific run.
    """
    from uuid import UUID

    try:
        repo_uuid = UUID(repo_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_id", "message": "Invalid repository ID"},
        ) from None

    # Determine run scope
    if run_id:
        try:
            run_uuid = UUID(run_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={"code": "invalid_id", "message": "Invalid run ID"},
            ) from None
        scope_run_id = run_uuid
    else:
        # Default: latest run
        run_result = await session.execute(
            select(Run)
            .where(Run.repository_id == repo_uuid)
            .order_by(Run.run_timestamp.desc())
            .limit(1)
        )
        latest_run = run_result.scalar_one_or_none()
        if latest_run is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "not_found", "message": "No runs found for repository"},
            )
        scope_run_id = latest_run.id

    result = await session.execute(
        select(EvidenceRecord).where(
            EvidenceRecord.repository_id == repo_uuid,
            EvidenceRecord.run_id == scope_run_id,
            EvidenceRecord.evidence_id == evidence_id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "evidence_not_found",
                "message": "Evidence record not found.",
                "evidence_id": evidence_id,
            },
        )

    return _evidence_record_response(record)


async def _resolve_evidence(
    session: AsyncSession,
    repo_id: object,
    run_id: object,
    evidence_ids: list[str] | None,
    include_body: bool = False,
) -> list[dict[str, object]]:
    """Resolve evidence_ids into evidence reference objects.

    Always uses the finding's own run_id, not the repo's latest run.
    """
    if not evidence_ids:
        return []

    # Check if any evidence records exist for this run
    count_result = await session.execute(
        select(func.count())
        .select_from(EvidenceRecord)
        .where(
            EvidenceRecord.repository_id == repo_id,
            EvidenceRecord.run_id == run_id,
        )
    )
    total_evidence = count_result.scalar() or 0

    references: list[dict[str, object]] = []
    for eid in evidence_ids:
        if not eid or not isinstance(eid, str):
            references.append(
                {
                    "evidence_id": str(eid) if eid else "",
                    "status": "malformed_reference",
                    "reason": "Evidence ID is empty or not a valid string.",
                }
            )
            continue

        result = await session.execute(
            select(EvidenceRecord).where(
                EvidenceRecord.repository_id == repo_id,
                EvidenceRecord.run_id == run_id,
                EvidenceRecord.evidence_id == eid,
            )
        )
        record = result.scalar_one_or_none()

        if record is not None:
            ref: dict[str, object] = {
                "evidence_id": eid,
                "status": "resolved",
            }
            if include_body:
                ref["evidence"] = _evidence_record_response(record)
            references.append(ref)
        elif total_evidence > 0:
            references.append(
                {
                    "evidence_id": eid,
                    "status": "missing",
                    "reason": "Evidence ID referenced by finding but not found in this upload's evidence store.",
                }
            )
        else:
            references.append(
                {
                    "evidence_id": eid,
                    "status": "legacy_no_evidence_store",
                    "reason": "This upload does not include an evidence store.",
                }
            )

    return references


def _evidence_record_response(record: EvidenceRecord) -> dict[str, object]:
    """Convert an EvidenceRecord ORM object to an API response dict.

    Excludes raw_observation by default.
    Exposes evidence_metadata as 'metadata' in the response.
    """
    return {
        "evidence_id": record.evidence_id,
        "source": record.source,
        "type": record.type,
        "category": record.category,
        "summary": record.summary,
        "file_path": record.file_path or None,
        "line_start": record.line_start,
        "line_end": record.line_end,
        "subject": record.subject,
        "object": record.object,
        "confidence": record.confidence,
        "collected_at": record.collected_at or None,
        "metadata": record.evidence_metadata or {},
    }
