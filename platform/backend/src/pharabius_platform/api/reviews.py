"""Review decision API endpoints for hosted finding review workflow.

Reuses CLI DecisionStatus values: accepted, rejected, deferred,
needs-investigation, duplicate, already-fixed, risk-accepted.
Reviewer is free-text advisory — not verified identity.
Review decisions never mutate Finding records.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pharabius_platform.db import get_session
from pharabius_platform.middleware.auth import require_token
from pharabius_platform.models import Repository, ReviewDecision

router = APIRouter(tags=["reviews"])

VALID_STATUSES = {
    "accepted",
    "rejected",
    "deferred",
    "needs-investigation",
    "duplicate",
    "already-fixed",
    "risk-accepted",
}


def _validate_status(status_value: str) -> None:
    """Raise 400 if status is not a valid DecisionStatus."""
    if status_value not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{status_value}'. Must be one of: {sorted(VALID_STATUSES)}",
        )


async def _get_repo_or_404(
    repo_id: str,
    session: AsyncSession,
) -> Repository:
    """Resolve repo_id string to Repository or 404."""
    try:
        repo_uuid = uuid.UUID(repo_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid repository ID format.",
        ) from None

    result = await session.execute(select(Repository).where(Repository.id == repo_uuid))
    repo = result.scalar_one_or_none()
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        ) from None
    return repo


def _decision_to_dict(d: ReviewDecision) -> dict[str, object]:
    """Convert a ReviewDecision ORM object to a response dict."""
    return {
        "id": str(d.id),
        "repository_id": str(d.repository_id),
        "run_id": str(d.run_id) if d.run_id else None,
        "finding_id": d.finding_id,
        "status": d.status,
        "previous_status": d.previous_status,
        "reviewer": d.reviewer,
        "rationale": d.rationale,
        "ticket_url": d.ticket_url,
        "owner_area": d.owner_area,
        "target_release": d.target_release,
        "notes": d.notes,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        "deleted_at": d.deleted_at.isoformat() if d.deleted_at else None,
        "deleted_by": d.deleted_by,
        "delete_reason": d.delete_reason,
    }


@router.post(
    "/api/v1/repositories/{repo_id}/reviews",
    status_code=status.HTTP_201_CREATED,
)
async def create_review_decision(
    repo_id: str,
    body: dict[str, object],
    session: Annotated[AsyncSession, Depends(get_session)],
    _token: str = Depends(require_token),
) -> dict[str, object]:
    """Create a review decision for a finding.

    Idempotent by (repository_id, finding_id): if an active decision exists,
    updates it instead (recording previous_status).
    """
    repo = await _get_repo_or_404(repo_id, session)

    finding_id = body.get("finding_id", "")
    if not finding_id or not isinstance(finding_id, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="finding_id is required and must be a string.",
        )

    status_value = body.get("status", "")
    if not isinstance(status_value, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status must be a string.",
        )
    _validate_status(status_value)

    # Check for existing active decision (idempotent)
    existing_result = await session.execute(
        select(ReviewDecision).where(
            ReviewDecision.repository_id == repo.id,
            ReviewDecision.finding_id == finding_id,
            ReviewDecision.deleted_at.is_(None),
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing is not None:
        # Update existing (record previous_status)
        previous = existing.status
        existing.status = status_value
        existing.previous_status = previous
        existing.reviewer = str(body.get("reviewer", existing.reviewer))
        existing.rationale = str(body.get("rationale", existing.rationale))
        existing.ticket_url = str(body.get("ticket_url", existing.ticket_url))
        existing.owner_area = str(body.get("owner_area", existing.owner_area))
        existing.target_release = str(body.get("target_release", existing.target_release))
        existing.notes = str(body.get("notes", existing.notes))
        existing.updated_at = datetime.now(UTC)
        await session.flush()
        await session.commit()
        return _decision_to_dict(existing)

    # Create new decision
    decision = ReviewDecision(
        repository_id=repo.id,
        run_id=_optional_uuid(body.get("run_id")),
        finding_id=finding_id,
        status=status_value,
        previous_status="",
        reviewer=str(body.get("reviewer", "")),
        rationale=str(body.get("rationale", "")),
        ticket_url=str(body.get("ticket_url", "")),
        owner_area=str(body.get("owner_area", "")),
        target_release=str(body.get("target_release", "")),
        notes=str(body.get("notes", "")),
    )
    session.add(decision)
    await session.flush()
    await session.commit()
    return _decision_to_dict(decision)


@router.get("/api/v1/repositories/{repo_id}/reviews")
async def list_review_decisions(
    repo_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    include_deleted: bool = Query(default=False),
    status_filter: str | None = Query(default=None, alias="status"),
) -> dict[str, object]:
    """List review decisions for a repository.

    By default excludes soft-deleted decisions.
    Use include_deleted=true to see all decisions including tombstones.
    """
    repo = await _get_repo_or_404(repo_id, session)

    query = select(ReviewDecision).where(ReviewDecision.repository_id == repo.id)

    if not include_deleted:
        query = query.where(ReviewDecision.deleted_at.is_(None))

    if status_filter:
        _validate_status(status_filter)
        query = query.where(ReviewDecision.status == status_filter)

    query = query.order_by(ReviewDecision.created_at.desc())
    result = await session.execute(query)
    decisions = result.scalars().all()

    return {
        "decisions": [_decision_to_dict(d) for d in decisions],
        "total": len(decisions),
    }


@router.get("/api/v1/repositories/{repo_id}/reviews/summary")
async def get_review_summary(
    repo_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    """Review progress summary for a repository.

    Returns counts by status plus total/decided/undecided.
    """
    repo = await _get_repo_or_404(repo_id, session)

    # Count decisions by status (active only)
    result = await session.execute(
        select(ReviewDecision.status, func.count(ReviewDecision.id))
        .where(ReviewDecision.repository_id == repo.id, ReviewDecision.deleted_at.is_(None))
        .group_by(ReviewDecision.status)
    )
    status_counts = dict(result.all())

    total_decisions = sum(status_counts.values())

    return {
        "total_decisions": total_decisions,
        "status_counts": {
            "accepted": status_counts.get("accepted", 0),
            "rejected": status_counts.get("rejected", 0),
            "deferred": status_counts.get("deferred", 0),
            "needs-investigation": status_counts.get("needs-investigation", 0),
            "duplicate": status_counts.get("duplicate", 0),
            "already-fixed": status_counts.get("already-fixed", 0),
            "risk-accepted": status_counts.get("risk-accepted", 0),
        },
    }


@router.patch("/api/v1/repositories/{repo_id}/reviews/{decision_id}")
async def update_review_decision(
    repo_id: str,
    decision_id: str,
    body: dict[str, object],
    session: Annotated[AsyncSession, Depends(get_session)],
    _token: str = Depends(require_token),
) -> dict[str, object]:
    """Update an existing review decision.

    Records previous_status when status changes.
    """
    await _get_repo_or_404(repo_id, session)

    decision_uuid = _parse_uuid_or_400(decision_id)
    result = await session.execute(
        select(ReviewDecision).where(
            ReviewDecision.id == decision_uuid,
            ReviewDecision.deleted_at.is_(None),
        )
    )
    decision = result.scalar_one_or_none()
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review decision not found.",
        ) from None

    # Update fields
    new_status = body.get("status")
    if new_status is not None:
        _validate_status(str(new_status))
        decision.previous_status = decision.status
        decision.status = str(new_status)

    for field in ("reviewer", "rationale", "ticket_url", "owner_area", "target_release", "notes"):
        if field in body:
            setattr(decision, field, str(body[field]))

    decision.updated_at = datetime.now(UTC)
    await session.flush()
    await session.commit()
    return _decision_to_dict(decision)


@router.delete("/api/v1/repositories/{repo_id}/reviews/{decision_id}")
async def delete_review_decision(
    repo_id: str,
    decision_id: str,
    body: dict[str, object],
    session: Annotated[AsyncSession, Depends(get_session)],
    _token: str = Depends(require_token),
) -> dict[str, object]:
    """Soft-delete a review decision.

    Records deleted_by, delete_reason, and deleted_at for audit.
    The record is retained in the database.
    """
    await _get_repo_or_404(repo_id, session)

    decision_uuid = _parse_uuid_or_400(decision_id)
    result = await session.execute(
        select(ReviewDecision).where(
            ReviewDecision.id == decision_uuid,
            ReviewDecision.deleted_at.is_(None),
        )
    )
    decision = result.scalar_one_or_none()
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review decision not found or already deleted.",
        ) from None

    decision.deleted_at = datetime.now(UTC)
    decision.deleted_by = str(body.get("deleted_by", ""))
    decision.delete_reason = str(body.get("delete_reason", ""))
    await session.flush()
    await session.commit()
    return _decision_to_dict(decision)


@router.post("/api/v1/repositories/{repo_id}/reviews/bulk")
async def bulk_review_decisions(
    repo_id: str,
    body: dict[str, object],
    session: Annotated[AsyncSession, Depends(get_session)],
    _token: str = Depends(require_token),
) -> dict[str, object]:
    """Bulk create/update review decisions.

    Accepts an array of decisions. Idempotent by (repository_id, finding_id).
    Returns created/updated count plus warnings for unknown finding IDs.
    """
    repo = await _get_repo_or_404(repo_id, session)

    decisions_data = body.get("decisions", [])
    if not isinstance(decisions_data, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'decisions' must be an array.",
        )

    # Validate all statuses first
    for i, item in enumerate(decisions_data):
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"decisions[{i}] must be an object.",
            )
        finding_id = item.get("finding_id", "")
        if not finding_id or not isinstance(finding_id, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"decisions[{i}].finding_id is required.",
            )
        s = item.get("status", "")
        if not isinstance(s, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"decisions[{i}].status must be a string.",
            )
        _validate_status(s)

    # Collect known finding IDs for this repo
    from pharabius_platform.models import Finding, Run

    known_result = await session.execute(
        select(Finding.finding_id)
        .join(Run, Finding.run_id == Run.id)
        .where(Run.repository_id == repo.id)
        .distinct()
    )
    known_finding_ids = {row[0] for row in known_result.all()}

    warnings: list[str] = []
    created = 0
    updated = 0

    for item in decisions_data:
        finding_id = str(item["finding_id"])
        status_value = str(item["status"])

        if finding_id not in known_finding_ids:
            warnings.append(f"Unknown finding ID: {finding_id}")

        # Check existing
        existing_result = await session.execute(
            select(ReviewDecision).where(
                ReviewDecision.repository_id == repo.id,
                ReviewDecision.finding_id == finding_id,
                ReviewDecision.deleted_at.is_(None),
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            previous = existing.status
            existing.status = status_value
            existing.previous_status = previous
            for field in (
                "reviewer",
                "rationale",
                "ticket_url",
                "owner_area",
                "target_release",
                "notes",
            ):
                if field in item:
                    setattr(existing, field, str(item[field]))
            existing.updated_at = datetime.now(UTC)
            updated += 1
        else:
            decision = ReviewDecision(
                repository_id=repo.id,
                run_id=_optional_uuid(item.get("run_id")),
                finding_id=finding_id,
                status=status_value,
                reviewer=str(item.get("reviewer", "")),
                rationale=str(item.get("rationale", "")),
                ticket_url=str(item.get("ticket_url", "")),
                owner_area=str(item.get("owner_area", "")),
                target_release=str(item.get("target_release", "")),
                notes=str(item.get("notes", "")),
            )
            session.add(decision)
            created += 1

    await session.flush()
    await session.commit()

    return {
        "created": created,
        "updated": updated,
        "total": created + updated,
        "warnings": warnings,
    }


@router.get("/api/v1/repositories/{repo_id}/reviews/audit-log")
async def get_review_audit_log(
    repo_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, object]:
    """Full audit history of review decisions including soft-deleted.

    Returns all decisions (active and deleted) ordered by most recent first.
    """
    repo = await _get_repo_or_404(repo_id, session)

    result = await session.execute(
        select(ReviewDecision)
        .where(ReviewDecision.repository_id == repo.id)
        .order_by(ReviewDecision.updated_at.desc())
        .limit(limit)
    )
    decisions = result.scalars().all()

    entries = []
    for d in decisions:
        entry: dict[str, object] = {
            "id": str(d.id),
            "finding_id": d.finding_id,
            "status": d.status,
            "previous_status": d.previous_status,
            "reviewer": d.reviewer,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
            "is_deleted": d.deleted_at is not None,
        }
        if d.deleted_at is not None:
            entry["deleted_at"] = d.deleted_at.isoformat()
            entry["deleted_by"] = d.deleted_by
            entry["delete_reason"] = d.delete_reason
        entries.append(entry)

    return {
        "entries": entries,
        "total": len(entries),
    }


def _optional_uuid(value: object | None) -> uuid.UUID | None:
    """Parse an optional UUID string."""
    if value is None or value == "":
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _parse_uuid_or_400(value: str) -> uuid.UUID:
    """Parse a UUID string or raise 400."""
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format.",
        ) from None
