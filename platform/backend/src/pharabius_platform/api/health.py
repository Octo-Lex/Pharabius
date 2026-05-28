"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
async def health_check() -> dict[str, str]:
    """Return platform health status."""
    return {"status": "ok", "version": "2.2.0"}
