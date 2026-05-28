"""Portfolio aggregation, trend, and gate history API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pharabius_platform.db import get_session
from pharabius_platform.models import (
    Claim,
    Gap,
    Organization,
    QualityGateResult,
    Repository,
    Run,
)

router = APIRouter(tags=["portfolio", "trends", "gates"])


@router.get("/api/v1/portfolio")
async def get_portfolio(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    """Portfolio summary across all repositories."""
    # Get all orgs/repos
    org_result = await session.execute(select(Organization))
    org_result.scalars().all()

    repo_result = await session.execute(select(Repository))
    repos = repo_result.scalars().all()

    # Aggregate from latest runs
    total_repos = len(repos)
    total_findings = 0
    total_critical = 0
    total_high = 0
    total_medium = 0
    total_low = 0
    repo_summaries = []

    for repo in repos:
        run_result = await session.execute(
            select(Run)
            .where(Run.repository_id == repo.id)
            .order_by(Run.run_timestamp.desc())
            .limit(1)
        )
        latest_run = run_result.scalar_one_or_none()

        if latest_run:
            total_findings += latest_run.total_findings
            total_critical += latest_run.critical
            total_high += latest_run.high
            total_medium += latest_run.medium
            total_low += latest_run.low
            gate_result = latest_run.gate_result
        else:
            gate_result = "unknown"

        repo_summaries.append(
            {
                "id": str(repo.id),
                "name": repo.name,
                "latest_gate_result": gate_result,
            }
        )

    return {
        "total_repositories": total_repos,
        "total_findings": total_findings,
        "severity": {
            "critical": total_critical,
            "high": total_high,
            "medium": total_medium,
            "low": total_low,
        },
        "repositories": repo_summaries,
    }


@router.get("/api/v1/portfolio/risk-rollup")
async def get_risk_rollup(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    """Severity distribution across all repositories."""
    result = await session.execute(
        select(
            func.sum(Run.critical).label("critical"),
            func.sum(Run.high).label("high"),
            func.sum(Run.medium).label("medium"),
            func.sum(Run.low).label("low"),
        )
    )
    row = result.one()

    return {
        "critical": row.critical or 0,
        "high": row.high or 0,
        "medium": row.medium or 0,
        "low": row.low or 0,
    }


@router.get("/api/v1/repositories/{repo_id}/trends")
async def get_trends(
    repo_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    """Trend points for a repository."""
    from uuid import UUID

    try:
        repo_uuid = UUID(repo_id)
    except ValueError:
        return {"error": {"code": "invalid_id", "message": "Invalid repository ID"}}

    result = await session.execute(
        select(Run).where(Run.repository_id == repo_uuid).order_by(Run.run_timestamp.asc())
    )
    runs = result.scalars().all()

    points = [
        {
            "run_id": r.run_id,
            "timestamp": r.run_timestamp.isoformat() if r.run_timestamp else None,
            "total_findings": r.total_findings,
            "critical": r.critical,
            "high": r.high,
            "medium": r.medium,
            "low": r.low,
            "gate_result": r.gate_result,
        }
        for r in runs
    ]

    return {"points": points, "total": len(points)}


@router.get("/api/v1/repositories/{repo_id}/gate-history")
async def get_gate_history(
    repo_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    """Quality gate pass/fail history for a repository."""
    from uuid import UUID

    try:
        repo_uuid = UUID(repo_id)
    except ValueError:
        return {"error": {"code": "invalid_id", "message": "Invalid repository ID"}}

    result = await session.execute(
        select(Run).where(Run.repository_id == repo_uuid).order_by(Run.run_timestamp.desc())
    )
    runs = result.scalars().all()

    history = []
    for run in runs:
        # Get gate result if available
        gate_result = await session.execute(
            select(QualityGateResult).where(QualityGateResult.run_id == run.id)
        )
        gate = gate_result.scalar_one_or_none()

        history.append(
            {
                "run_id": run.run_id,
                "timestamp": run.run_timestamp.isoformat() if run.run_timestamp else None,
                "gate_result": run.gate_result,
                "passed": gate.passed if gate else None,
                "total_findings": run.total_findings,
                "critical": run.critical,
                "high": run.high,
            }
        )

    return {"history": history, "total": len(history)}


@router.get("/api/v1/claims")
async def list_claims(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    """List claims across all repositories."""
    result = await session.execute(select(Claim))
    claims = result.scalars().all()

    items = [
        {
            "id": str(c.id),
            "claim_id": c.claim_id,
            "claim_type": c.claim_type,
            "status": c.status,
            "confidence": c.confidence,
            "description": c.description,
        }
        for c in claims
    ]

    return {"claims": items, "total": len(items)}


@router.get("/api/v1/gaps")
async def list_gaps(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    """List gaps across all repositories."""
    result = await session.execute(select(Gap))
    gaps = result.scalars().all()

    items = [
        {
            "id": str(g.id),
            "gap_id": g.gap_id,
            "description": g.description,
            "severity": g.severity,
        }
        for g in gaps
    ]

    return {"gaps": items, "total": len(items)}


@router.get("/api/v1/readiness")
async def list_readiness(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    """Readiness status across all repositories."""
    result = await session.execute(select(Repository))
    repos = result.scalars().all()

    items = []
    for repo in repos:
        run_result = await session.execute(
            select(Run)
            .where(Run.repository_id == repo.id)
            .order_by(Run.run_timestamp.desc())
            .limit(1)
        )
        latest_run = run_result.scalar_one_or_none()

        items.append(
            {
                "repository_id": str(repo.id),
                "repository_name": repo.name,
                "readiness_status": latest_run.readiness_status if latest_run else "unknown",
            }
        )

    return {"readiness": items, "total": len(items)}
