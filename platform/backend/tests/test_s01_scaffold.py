"""S01 scaffold tests — health endpoint, error envelope, admin token auth."""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

from pharabius_platform.main import app


@pytest.fixture
def admin_token() -> str:
    token = "test_admin_token_s01"
    os.environ["ADMIN_TOKEN"] = token
    yield token
    os.environ.pop("ADMIN_TOKEN", "")


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "2.2.0"


class TestErrorEnvelope:
    async def test_404_uses_error_envelope(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "request_id" in data["error"]

    async def test_error_has_request_id(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/nonexistent")
        data = response.json()
        assert len(data["error"]["request_id"]) > 0


class TestRequestId:
    async def test_response_includes_request_id_header(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/health")
        assert "x-request-id" in response.headers
        assert len(response.headers["x-request-id"]) > 0


class TestAdminTokenAuth:
    async def test_admin_token_rejected_without_credentials(
        self, client: AsyncClient, admin_token: str
    ) -> None:
        from fastapi import HTTPException

        from pharabius_platform.middleware.auth import require_admin

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(None)
        assert exc_info.value.status_code == 401

    async def test_admin_token_accepted(self, client: AsyncClient, admin_token: str) -> None:
        # Health is unprotected, so we test auth via the middleware function directly
        from fastapi.security import HTTPAuthorizationCredentials

        from pharabius_platform.middleware.auth import require_admin

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=admin_token)
        result = await require_admin(creds)
        assert result == "admin"

    async def test_admin_token_rejected_wrong_token(
        self, client: AsyncClient, admin_token: str
    ) -> None:
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials

        from pharabius_platform.middleware.auth import require_admin

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong_token")
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(creds)
        assert exc_info.value.status_code == 401

    async def test_admin_token_rejected_none(self, client: AsyncClient, admin_token: str) -> None:
        """Explicit None credentials rejected."""
        from fastapi import HTTPException

        from pharabius_platform.middleware.auth import require_admin

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(None)
        assert exc_info.value.status_code == 401
        assert "required" in str(exc_info.value.detail).lower()
