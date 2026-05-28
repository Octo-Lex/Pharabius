"""Repository and findings API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pharabius_platform.db import get_session
from pharabius_platform.models import Finding, Repository, Run

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
            "severity": f.severity,
            "confidence": f.confidence,
            "risk_score": f.risk_score,
            "priority": f.priority,
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
