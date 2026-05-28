"""Token-based authentication middleware.

Supports two auth methods:
1. Admin token via ADMIN_TOKEN env var
2. Database-backed API keys (phar_* prefix)
"""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pharabius_platform.db import get_session
from pharabius_platform.models import APIKey

_bearer_scheme = HTTPBearer(auto_error=False)


def _hash_token(token: str) -> str:
    """Hash an API token for comparison."""
    return hashlib.sha256(token.encode()).hexdigest()


def get_admin_token() -> str:
    """Get the configured admin token from environment."""
    return os.environ.get("ADMIN_TOKEN", "")


async def require_admin(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ],
) -> str:
    """Require a valid admin token."""
    admin_token = get_admin_token()
    if not admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No admin token configured.",
        )
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization required.",
        )
    if credentials.credentials != admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token.",
        )
    return "admin"


async def require_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> str:
    """Require a valid token (admin or API key).

    Admin token: checked against ADMIN_TOKEN env var.
    API key: must start with 'phar_', looked up in database.
    Rejected if key is inactive or expired.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization required.",
        )

    token_value = credentials.credentials

    # Check admin token first
    admin_token = get_admin_token()
    if admin_token and token_value == admin_token:
        return "admin"

    # Check API key (must have phar_ prefix)
    if token_value.startswith("phar_"):
        key_hash = _hash_token(token_value)
        result = await session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
        api_key = result.scalar_one_or_none()

        if api_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key.",
            )

        if not api_key.active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has been revoked.",
            )

        if api_key.expires_at is not None and api_key.expires_at < datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired.",
            )

        # Update last_used_at
        api_key.last_used_at = datetime.now(UTC)
        await session.flush()

        return api_key.key_type

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token format. Use admin token or phar_* API key.",
    )
