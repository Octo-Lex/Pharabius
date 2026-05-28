"""S02 tests — Hosted finding review workflow API endpoints (v2.3.0)."""

from __future__ import annotations

import io
import json
import tarfile
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from pharabius_platform.main import app

ADMIN_TOKEN = "test_admin_token_v230"


def _make_tar_gz(files: dict[str, str]) -> bytes:
    """Create a tar.gz in-memory from {filename: content} pairs."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, content in files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


EVIDENCE_JSON = json.dumps({"schema_version": "1.0", "evidence": []})
DEBT_REGISTER_JSON = json.dumps(
    {
        "schema_version": "1.0",
        "project_name": "review-test-repo",
        "findings": [
            {
                "id": "TD-DEP-001",
                "category": "TD-DEP",
                "issue_type": "technical_debt",
                "title": "Missing lockfile",
                "description": "Test",
                "severity": "High",
                "confidence": "High",
                "locations": ["package.json"],
                "evidence_ids": ["EVD-001"],
                "technical_impact": "Low",
                "business_impact": "Low",
                "risk_score": 25,
                "priority": "High",
                "recommended_action": "Fix",
            },
            {
                "id": "TD-ARCH-001",
                "category": "TD-ARCH",
                "issue_type": "technical_debt",
                "title": "Cycle detected",
                "description": "Test",
                "severity": "Medium",
                "confidence": "Medium",
                "locations": ["src/main.py"],
                "evidence_ids": ["EVD-001"],
                "technical_impact": "Low",
                "business_impact": "Low",
                "risk_score": 15,
                "priority": "Medium",
                "recommended_action": "Refactor",
            },
        ],
    }
)
PROFILE_JSON = json.dumps(
    {
        "schema_version": "1.0",
        "project_name": "review-test-repo",
        "repository_root": "/tmp/test",
    }
)


@pytest.fixture(autouse=True)
async def _setup_db(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[None, None]:
    """Create tables before each test, drop after."""
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true",
    )

    from pharabius_platform import db as db_mod
    from pharabius_platform.db import init_db
    from pharabius_platform.models import Base

    db_url = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"
    init_db(db_url)

    assert db_mod._engine is not None
    async with db_mod._engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with db_mod._engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client() -> AsyncClient:
    """Provide an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def seeded_client(client: AsyncClient) -> AsyncClient:
    """Client with a seeded repo containing 2 findings."""
    tar_data = _make_tar_gz(
        {
            ".ai-debt/evidence.json": EVIDENCE_JSON,
            ".ai-debt/debt-register.json": DEBT_REGISTER_JSON,
            ".ai-debt/project-profile.json": PROFILE_JSON,
        }
    )
    resp = await client.post(
        "/api/v1/bundles",
        files={"file": ("bundle.tar.gz", tar_data, "application/gzip")},
        data={"repository_name": "review-test-repo"},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert resp.status_code == 201
    return client


def _repo_id(client: AsyncClient) -> str:
    """Helper: get the first repo ID."""
    import asyncio

    resp = asyncio.get_event_loop().run_until_complete(client.get("/api/v1/repositories"))
    data = resp.json()
    return data["repositories"][0]["id"]


async def _get_repo_id(client: AsyncClient) -> str:
    resp = await client.get("/api/v1/repositories")
    data = resp.json()
    return data["repositories"][0]["id"]


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


class TestReviewStatusValidation:
    """Status values must exactly match CLI DecisionStatus."""

    async def test_valid_status_accepted(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/repositories/00000000-0000-0000-0000-000000000000/reviews",
            json={"finding_id": "TD-001", "status": "accepted"},
            headers=_auth(),
        )
        # Will 404 (no repo) but NOT 400 (invalid status)
        assert resp.status_code != 400

    async def test_invalid_status_rejected_with_400(self, seeded_client: AsyncClient) -> None:
        repo_id = await _get_repo_id(seeded_client)
        resp = await seeded_client.post(
            f"/api/v1/repositories/{repo_id}/reviews",
            json={"finding_id": "TD-001", "status": "validated"},
            headers=_auth(),
        )
        assert resp.status_code == 400
        assert "Invalid status" in resp.json()["error"]["message"]

    async def test_all_seven_statuses_valid(self, client: AsyncClient) -> None:
        statuses = [
            "accepted",
            "rejected",
            "deferred",
            "needs-investigation",
            "duplicate",
            "already-fixed",
            "risk-accepted",
        ]
        for s in statuses:
            resp = await client.post(
                "/api/v1/repositories/00000000-0000-0000-0000-000000000000/reviews",
                json={"finding_id": "TD-001", "status": s},
                headers=_auth(),
            )
            assert resp.status_code != 400, f"Status '{s}' should be valid"


class TestCreateReviewDecision:
    """Create review decisions for findings."""

    async def test_create_decision(self, seeded_client: AsyncClient) -> None:
        repo_id = await _get_repo_id(seeded_client)
        resp = await seeded_client.post(
            f"/api/v1/repositories/{repo_id}/reviews",
            json={
                "finding_id": "TD-DEP-001",
                "status": "accepted",
                "reviewer": "alice",
                "rationale": "Known dependency, will fix in Q3",
            },
            headers=_auth(),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["finding_id"] == "TD-DEP-001"
        assert body["status"] == "accepted"
        assert body["reviewer"] == "alice"
        assert body["previous_status"] == ""
        assert body["id"] is not None

    async def test_create_without_auth_rejected(self, seeded_client: AsyncClient) -> None:
        repo_id = await _get_repo_id(seeded_client)
        resp = await seeded_client.post(
            f"/api/v1/repositories/{repo_id}/reviews",
            json={"finding_id": "TD-DEP-001", "status": "accepted"},
        )
        assert resp.status_code == 401


class TestUpdateReviewDecision:
    """Update records previous_status."""

    async def test_update_records_previous_status(self, seeded_client: AsyncClient) -> None:
        repo_id = await _get_repo_id(seeded_client)

        # Create
        resp = await seeded_client.post(
            f"/api/v1/repositories/{repo_id}/reviews",
            json={"finding_id": "TD-DEP-001", "status": "deferred"},
            headers=_auth(),
        )
        assert resp.status_code == 201
        decision_id = resp.json()["id"]

        # Update
        resp = await seeded_client.patch(
            f"/api/v1/repositories/{repo_id}/reviews/{decision_id}",
            json={"status": "accepted", "rationale": "Resolved"},
            headers=_auth(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "accepted"
        assert body["previous_status"] == "deferred"


class TestIdempotentCreate:
    """Creating with same finding_id updates existing (idempotent)."""

    async def test_idempotent_by_finding_id(self, seeded_client: AsyncClient) -> None:
        repo_id = await _get_repo_id(seeded_client)

        # First create
        resp1 = await seeded_client.post(
            f"/api/v1/repositories/{repo_id}/reviews",
            json={"finding_id": "TD-ARCH-001", "status": "deferred"},
            headers=_auth(),
        )
        assert resp1.status_code == 201
        first_id = resp1.json()["id"]

        # Second create with same finding_id → updates
        resp2 = await seeded_client.post(
            f"/api/v1/repositories/{repo_id}/reviews",
            json={"finding_id": "TD-ARCH-001", "status": "rejected"},
            headers=_auth(),
        )
        assert resp2.status_code == 201
        assert resp2.json()["id"] == first_id
        assert resp2.json()["previous_status"] == "deferred"
        assert resp2.json()["status"] == "rejected"


class TestSoftDelete:
    """Delete preserves audit history (soft delete)."""

    async def test_soft_delete_retains_record(self, seeded_client: AsyncClient) -> None:
        repo_id = await _get_repo_id(seeded_client)

        # Create
        resp = await seeded_client.post(
            f"/api/v1/repositories/{repo_id}/reviews",
            json={"finding_id": "TD-DEP-001", "status": "accepted"},
            headers=_auth(),
        )
        decision_id = resp.json()["id"]

        # Delete
        resp = await seeded_client.request(
            "DELETE",
            f"/api/v1/repositories/{repo_id}/reviews/{decision_id}",
            json={"deleted_by": "bob", "delete_reason": "Mistake"},
            headers=_auth(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["deleted_at"] is not None
        assert body["deleted_by"] == "bob"
        assert body["delete_reason"] == "Mistake"

        # Not in default list
        resp = await seeded_client.get(f"/api/v1/repositories/{repo_id}/reviews")
        decisions = resp.json()["decisions"]
        finding_ids = [d["finding_id"] for d in decisions]
        assert "TD-DEP-001" not in finding_ids

        # IS in include_deleted list
        resp = await seeded_client.get(
            f"/api/v1/repositories/{repo_id}/reviews?include_deleted=true"
        )
        decisions = resp.json()["decisions"]
        finding_ids = [d["finding_id"] for d in decisions]
        assert "TD-DEP-001" in finding_ids

    async def test_delete_in_audit_log(self, seeded_client: AsyncClient) -> None:
        repo_id = await _get_repo_id(seeded_client)

        resp = await seeded_client.post(
            f"/api/v1/repositories/{repo_id}/reviews",
            json={"finding_id": "TD-ARCH-001", "status": "risk-accepted"},
            headers=_auth(),
        )
        decision_id = resp.json()["id"]

        await seeded_client.request(
            "DELETE",
            f"/api/v1/repositories/{repo_id}/reviews/{decision_id}",
            json={"deleted_by": "alice", "delete_reason": "Re-evaluating"},
            headers=_auth(),
        )

        resp = await seeded_client.get(f"/api/v1/repositories/{repo_id}/reviews/audit-log")
        entries = resp.json()["entries"]
        assert any(e["finding_id"] == "TD-ARCH-001" and e["is_deleted"] for e in entries)


class TestReviewSummary:
    """Summary returns status counts."""

    async def test_summary_counts(self, seeded_client: AsyncClient) -> None:
        repo_id = await _get_repo_id(seeded_client)

        await seeded_client.post(
            f"/api/v1/repositories/{repo_id}/reviews",
            json={"finding_id": "TD-DEP-001", "status": "accepted"},
            headers=_auth(),
        )
        await seeded_client.post(
            f"/api/v1/repositories/{repo_id}/reviews",
            json={"finding_id": "TD-ARCH-001", "status": "deferred"},
            headers=_auth(),
        )

        resp = await seeded_client.get(f"/api/v1/repositories/{repo_id}/reviews/summary")
        body = resp.json()
        assert body["total_decisions"] == 2
        assert body["status_counts"]["accepted"] == 1
        assert body["status_counts"]["deferred"] == 1


class TestBulkReview:
    """Bulk create/update with warnings for unknown finding IDs."""

    async def test_bulk_creates_decisions(self, seeded_client: AsyncClient) -> None:
        repo_id = await _get_repo_id(seeded_client)

        resp = await seeded_client.post(
            f"/api/v1/repositories/{repo_id}/reviews/bulk",
            json={
                "decisions": [
                    {"finding_id": "TD-DEP-001", "status": "accepted", "reviewer": "alice"},
                    {"finding_id": "TD-ARCH-001", "status": "rejected", "reviewer": "bob"},
                ],
            },
            headers=_auth(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["created"] == 2
        assert body["updated"] == 0
        assert body["warnings"] == []

    async def test_bulk_warns_on_unknown_finding(self, seeded_client: AsyncClient) -> None:
        repo_id = await _get_repo_id(seeded_client)

        resp = await seeded_client.post(
            f"/api/v1/repositories/{repo_id}/reviews/bulk",
            json={
                "decisions": [
                    {"finding_id": "TD-DEP-001", "status": "accepted"},
                    {"finding_id": "TD-FAKE-999", "status": "rejected"},
                ],
            },
            headers=_auth(),
        )
        body = resp.json()
        assert body["created"] == 2
        assert len(body["warnings"]) == 1
        assert "TD-FAKE-999" in body["warnings"][0]

    async def test_bulk_idempotent_by_finding_id(self, seeded_client: AsyncClient) -> None:
        repo_id = await _get_repo_id(seeded_client)

        # First bulk
        await seeded_client.post(
            f"/api/v1/repositories/{repo_id}/reviews/bulk",
            json={
                "decisions": [
                    {"finding_id": "TD-DEP-001", "status": "accepted"},
                ],
            },
            headers=_auth(),
        )

        # Second bulk with same finding_id → updates
        resp = await seeded_client.post(
            f"/api/v1/repositories/{repo_id}/reviews/bulk",
            json={
                "decisions": [
                    {"finding_id": "TD-DEP-001", "status": "rejected"},
                ],
            },
            headers=_auth(),
        )
        body = resp.json()
        assert body["created"] == 0
        assert body["updated"] == 1


class TestReadEndpointsAccessible:
    """Read endpoints work without auth."""

    async def test_list_reviews_no_auth(self, seeded_client: AsyncClient) -> None:
        repo_id = await _get_repo_id(seeded_client)
        resp = await seeded_client.get(f"/api/v1/repositories/{repo_id}/reviews")
        assert resp.status_code == 200

    async def test_summary_no_auth(self, seeded_client: AsyncClient) -> None:
        repo_id = await _get_repo_id(seeded_client)
        resp = await seeded_client.get(f"/api/v1/repositories/{repo_id}/reviews/summary")
        assert resp.status_code == 200

    async def test_audit_log_no_auth(self, seeded_client: AsyncClient) -> None:
        repo_id = await _get_repo_id(seeded_client)
        resp = await seeded_client.get(f"/api/v1/repositories/{repo_id}/reviews/audit-log")
        assert resp.status_code == 200


class TestReviewDoesNotMutateFindings:
    """Review decisions never mutate Finding records."""

    async def test_findings_unchanged_after_review(self, seeded_client: AsyncClient) -> None:
        repo_id = await _get_repo_id(seeded_client)

        # Get findings before
        resp_before = await seeded_client.get(f"/api/v1/repositories/{repo_id}/findings")
        findings_before = resp_before.json()["findings"]

        # Create review
        await seeded_client.post(
            f"/api/v1/repositories/{repo_id}/reviews",
            json={"finding_id": "TD-DEP-001", "status": "accepted"},
            headers=_auth(),
        )

        # Get findings after
        resp_after = await seeded_client.get(f"/api/v1/repositories/{repo_id}/findings")
        findings_after = resp_after.json()["findings"]

        # Findings are identical
        assert findings_before == findings_after
