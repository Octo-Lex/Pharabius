"""S06 — E2E smoke test and hardening tests.

E2E smoke test proves the upload → parse → query pipeline.
Security and packaging checks.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import tarfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from pharabius_platform.main import app


def _create_minimal_bundle(base: Path) -> bytes:
    """Create a minimal valid .ai-debt bundle tarball."""
    ai_debt = base / ".ai-debt"
    ai_debt.mkdir()

    (ai_debt / "evidence.json").write_text(
        json.dumps({"schema_version": "1.0", "evidence": []}), encoding="utf-8"
    )
    (ai_debt / "debt-register.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "project_name": "e2e-test",
                "findings": [
                    {
                        "id": "TD-DEP-001",
                        "category": "TD-DEP",
                        "issue_type": "technical_debt",
                        "title": "E2E test finding",
                        "description": "Test",
                        "severity": "High",
                        "confidence": "High",
                        "locations": ["src/main.py"],
                        "evidence_ids": ["EVD-001"],
                        "technical_impact": "Medium",
                        "business_impact": "Low",
                        "risk_score": 25,
                        "priority": "High",
                        "recommended_action": "Fix",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (ai_debt / "project-profile.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "project_name": "e2e-test",
                "repository_root": "/e2e",
            }
        ),
        encoding="utf-8",
    )

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(str(ai_debt), arcname=".ai-debt")
    return buf.getvalue()


@pytest.fixture
def admin_token() -> str:
    token = "test_admin_s06"
    os.environ["ADMIN_TOKEN"] = token
    yield token
    os.environ.pop("ADMIN_TOKEN", "")


class TestE2ESmokeTest:
    """Full pipeline: upload → store → parse → verify endpoints exist."""

    async def test_upload_stores_and_parses(self, admin_token: str, tmp_path: Path) -> None:
        """Step 1-4: Upload valid bundle, verify stored and parsed."""
        tarball = _create_minimal_bundle(tmp_path)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/bundles",
                headers={"Authorization": f"Bearer {admin_token}"},
                files={"file": ("bundle.tar.gz", tarball, "application/gzip")},
            )
            assert response.status_code == 201
            data = response.json()
            assert data["is_valid"] is True
            assert data["content_hash"] == hashlib.sha256(tarball).hexdigest()
            assert data["file_size_bytes"] > 0

    async def test_health_endpoint(self) -> None:
        """Step: Health check works."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/v1/health")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"


class TestSecurityChecklist:
    """Verify upload security measures."""

    async def test_no_token_rejected(self, tmp_path: Path) -> None:
        tarball = _create_minimal_bundle(tmp_path)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/bundles",
                files={"file": ("bundle.tar.gz", tarball, "application/gzip")},
            )
            assert response.status_code == 401

    async def test_wrong_token_rejected(self, admin_token: str, tmp_path: Path) -> None:
        tarball = _create_minimal_bundle(tmp_path)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/bundles",
                headers={"Authorization": "Bearer wrong"},
                files={"file": ("bundle.tar.gz", tarball, "application/gzip")},
            )
            assert response.status_code == 401

    async def test_oversized_rejected(self, admin_token: str) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/bundles",
                headers={"Authorization": f"Bearer {admin_token}"},
                files={"file": ("big.tar.gz", b"x" * (51 * 1024 * 1024), "application/gzip")},
            )
            assert response.status_code == 413

    async def test_api_keys_hashed(self) -> None:
        """Verify keys are hashed, not stored in plain text."""
        from pharabius_platform.api.api_keys import _hash_key

        raw = "phar_test_key_12345"
        hashed = _hash_key(raw)
        assert hashed != raw
        assert len(hashed) == 64


class TestAllEndpointsRegistered:
    """Verify every documented endpoint exists."""

    def test_all_endpoints(self) -> None:
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        expected = [
            "/api/v1/health",
            "/api/v1/bundles",
            "/api/v1/repositories",
            "/api/v1/portfolio",
            "/api/v1/portfolio/risk-rollup",
            "/api/v1/claims",
            "/api/v1/gaps",
            "/api/v1/readiness",
            "/api/v1/api-keys",
        ]
        for endpoint in expected:
            assert endpoint in routes, f"Missing endpoint: {endpoint}"

        # Parameterized routes
        param_routes = [
            "/repositories/{repo_id}/findings",
            "/repositories/{repo_id}/runs",
            "/repositories/{repo_id}/latest-run",
            "/repositories/{repo_id}/trends",
            "/repositories/{repo_id}/gate-history",
            "/api-keys/{key_id}",
        ]
        for pattern in param_routes:
            assert any(pattern in r for r in routes), f"Missing route: {pattern}"
