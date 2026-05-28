"""API key CRUD endpoints."""

from __future__ import annotations

import hashlib
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pharabius_platform.db import get_session
from pharabius_platform.middleware.auth import require_admin
from pharabius_platform.models import APIKey, Organization

router = APIRouter(tags=["api-keys"])


class CreateAPIKeyRequest(BaseModel):
    name: str
    key_type: str = "upload"  # "admin" or "upload"
    organization_slug: str = "default"


class APIKeyResponse(BaseModel):
    id: str
    name: str
    key_type: str
    key: str = ""  # Only populated on creation
    created_at: str = ""
    expires_at: str | None = None
    active: bool = True


class APIKeyListItem(BaseModel):
    id: str
    name: str
    key_type: str
    last_used_at: str | None = None
    expires_at: str | None = None
    active: bool = True


def _generate_key() -> str:
    """Generate a random API key."""
    return f"phar_{secrets.token_hex(24)}"


def _hash_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


@router.post("/api/v1/api-keys", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: CreateAPIKeyRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[str, Depends(require_admin)],
) -> dict[str, object]:
    """Create a new API key."""
    if request.key_type not in ("admin", "upload"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="key_type must be 'admin' or 'upload'",
        )

    # Get or create organization
    result = await session.execute(
        select(Organization).where(Organization.slug == request.organization_slug)
    )
    org = result.scalar_one_or_none()
    if org is None:
        org = Organization(name=request.organization_slug, slug=request.organization_slug)
        session.add(org)
        await session.flush()

    raw_key = _generate_key()
    key_hash = _hash_key(raw_key)

    api_key = APIKey(
        organization_id=org.id,
        key_hash=key_hash,
        name=request.name,
        key_type=request.key_type,
    )
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)

    return {
        "id": str(api_key.id),
        "name": api_key.name,
        "key_type": api_key.key_type,
        "key": raw_key,  # Shown only once
        "active": api_key.active,
    }


@router.get("/api/v1/api-keys")
async def list_api_keys(
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[str, Depends(require_admin)],
) -> dict[str, object]:
    """List all API keys (without raw key values)."""
    result = await session.execute(select(APIKey).order_by(APIKey.name))
    keys = result.scalars().all()

    items = [
        {
            "id": str(k.id),
            "name": k.name,
            "key_type": k.key_type,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "active": k.active,
        }
        for k in keys
    ]

    return {"api_keys": items, "total": len(items)}


@router.delete("/api/v1/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[str, Depends(require_admin)],
) -> dict[str, object]:
    """Revoke an API key."""
    from uuid import UUID

    try:
        key_uuid = UUID(key_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid key ID",
        ) from None

    result = await session.execute(select(APIKey).where(APIKey.id == key_uuid))
    api_key = result.scalar_one_or_none()

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        ) from None

    api_key.active = False
    await session.commit()

    return {"id": str(api_key.id), "active": False}
