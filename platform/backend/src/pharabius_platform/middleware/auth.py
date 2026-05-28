"""Token-based authentication middleware."""

from __future__ import annotations

import hashlib
import os
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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
) -> str:
    """Require a valid token (admin or API key).

    For S01, this only checks admin token.
    S05 will add API key lookup against the database.
    """
    return await require_admin(credentials)
