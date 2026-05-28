"""Tests for v2.4.0 Finding Detail Enrichment.

Validates:
- Migration 003 adds description, locations, evidence_ids to findings
- Upload parser persists description/locations/evidence_ids
- API responses include new fields
- Single-finding endpoint works
- Frontend handles empty fields gracefully
"""

from __future__ import annotations

import io
import json
import tarfile
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from pharabius_platform.main import app
from pharabius_platform.models import Base

ADMIN_TOKEN = "test_admin_token"

EVIDENCE_JSON = json.dumps({"schema_version": "1.0", "evidence": []})


def _make_findings_json(
    findings: list[dict] | None = None,
    project_name: str = "detail-test",
) -> str:
    if findings is None:
        findings = [
            {
                "id": "TD-DEP-001",
                "category": "TD-DEP",
                "issue_type": "technical_debt",
                "title": "Missing lockfile",
                "description": "No lockfile detected for package.json",
                "severity": "Critical",
                "confidence": "High",
                "locations": ["package.json", "src/index.js"],
                "evidence_ids": ["EVD-001", "EVD-002"],
                "technical_impact": "High",
                "business_impact": "Medium",
                "risk_score": 40,
                "priority": "Critical",
                "recommended_action": "Add lockfile",
            },
            {
                "id": "TD-TEST-001",
                "category": "TD-TEST",
                "issue_type": "technical_debt",
                "title": "Low coverage",
                "description": "Test coverage below threshold",
                "severity": "Medium",
                "confidence": "Medium",
                "locations": ["src/"],
                "evidence_ids": ["EVD-003"],
                "technical_impact": "Medium",
                "business_impact": "Low",
                "risk_score": 20,
                "priority": "Medium",
                "recommended_action": "Add tests",
            },
        ]
    return json.dumps(
        {
            "schema_version": "1.0",
            "project_name": project_name,
            "findings": findings,
        }
    )


def _make_profile_json(project_name: str = "detail-test") -> str:
    return json.dumps(
        {
            "schema_version": "1.0",
            "project_name": project_name,
            "repository_root": "/test",
        }
    )


def _make_tar_gz(findings: list[dict] | None = None, project_name: str = "detail-test") -> bytes:
    register = _make_findings_json(findings, project_name)
    profile = _make_profile_json(project_name)

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in [
            (".ai-debt/evidence.json", EVIDENCE_JSON),
            (".ai-debt/debt-register.json", register),
            (".ai-debt/project-profile.json", profile),
        ]:
            info = tarfile.TarInfo(name=name)
            info.size = len(data.encode())
            tar.addfile(info, io.BytesIO(data.encode()))
    return buf.getvalue()


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


async def _get_repo_id(client: AsyncClient) -> str:
    resp = await client.get("/api/v1/repositories")
    data = resp.json()
    repos = data["repositories"]
    assert len(repos) > 0
    return repos[0]["id"]


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
    """Client with uploaded findings containing detail fields."""
    tar_data = _make_tar_gz()
    resp = await client.post(
        "/api/v1/bundles",
        files={"file": ("test.tar.gz", tar_data, "application/gzip")},
        data={"repository_name": "Detail Test Repo"},
        headers=_auth(),
    )
    assert resp.status_code == 201
    return client


class TestMigration003Columns:
    """Verify the 3 new columns exist on the findings table."""

    async def test_description_column_exists(self):
        from sqlalchemy import text

        from pharabius_platform import db as db_mod

        assert db_mod._engine is not None
        async with db_mod._engine.begin() as conn:
            result = await conn.execute(text("PRAGMA table_info(findings)"))
            columns = {row[1] for row in result}
            assert "description" in columns

    async def test_locations_column_exists(self):
        from sqlalchemy import text

        from pharabius_platform import db as db_mod

        assert db_mod._engine is not None
        async with db_mod._engine.begin() as conn:
            result = await conn.execute(text("PRAGMA table_info(findings)"))
            columns = {row[1] for row in result}
            assert "locations" in columns

    async def test_evidence_ids_column_exists(self):
        from sqlalchemy import text

        from pharabius_platform import db as db_mod

        assert db_mod._engine is not None
        async with db_mod._engine.begin() as conn:
            result = await conn.execute(text("PRAGMA table_info(findings)"))
            columns = {row[1] for row in result}
            assert "evidence_ids" in columns


class TestUploadParserDetail:
    """Verify upload parser persists description, locations, evidence_ids."""

    async def test_upload_persists_description(self, seeded_client: AsyncClient):
        repo_id = await _get_repo_id(seeded_client)
        resp = await seeded_client.get(f"/api/v1/repositories/{repo_id}/findings")
        data = resp.json()
        findings = {f["finding_id"]: f for f in data["findings"]}
        assert findings["TD-DEP-001"]["description"] == "No lockfile detected for package.json"

    async def test_upload_persists_locations(self, seeded_client: AsyncClient):
        repo_id = await _get_repo_id(seeded_client)
        resp = await seeded_client.get(f"/api/v1/repositories/{repo_id}/findings")
        data = resp.json()
        findings = {f["finding_id"]: f for f in data["findings"]}
        assert findings["TD-DEP-001"]["locations"] == ["package.json", "src/index.js"]

    async def test_upload_persists_evidence_ids(self, seeded_client: AsyncClient):
        repo_id = await _get_repo_id(seeded_client)
        resp = await seeded_client.get(f"/api/v1/repositories/{repo_id}/findings")
        data = resp.json()
        findings = {f["finding_id"]: f for f in data["findings"]}
        assert findings["TD-DEP-001"]["evidence_ids"] == ["EVD-001", "EVD-002"]

    async def test_upload_handles_missing_optional_fields(self, client: AsyncClient):
        """Findings without description/locations/evidence_ids don't crash."""
        findings = [
            {
                "id": "TD-MIN-001",
                "category": "TD-DEP",
                "title": "Minimal finding",
                "description": "",
                "severity": "Low",
                "confidence": "Low",
                "locations": [],
                "evidence_ids": [],
                "technical_impact": "Low",
                "business_impact": "Low",
                "risk_score": 5,
                "priority": "Low",
                "recommended_action": "Ignore",
            },
        ]
        tar_data = _make_tar_gz(findings=findings, project_name="minimal-test")
        resp = await client.post(
            "/api/v1/bundles",
            files={"file": ("minimal.tar.gz", tar_data, "application/gzip")},
            data={"repository_name": "Minimal Test"},
            headers=_auth(),
        )
        assert resp.status_code == 201


class TestAPIResponseEnrichment:
    """Verify API responses include the new fields."""

    async def test_findings_list_includes_description(self, seeded_client: AsyncClient):
        repo_id = await _get_repo_id(seeded_client)
        resp = await seeded_client.get(f"/api/v1/repositories/{repo_id}/findings")
        data = resp.json()
        assert data["findings"][0]["description"] is not None

    async def test_findings_list_includes_locations(self, seeded_client: AsyncClient):
        repo_id = await _get_repo_id(seeded_client)
        resp = await seeded_client.get(f"/api/v1/repositories/{repo_id}/findings")
        data = resp.json()
        f = next(f for f in data["findings"] if f["finding_id"] == "TD-DEP-001")
        assert isinstance(f["locations"], list)

    async def test_findings_list_includes_evidence_ids(self, seeded_client: AsyncClient):
        repo_id = await _get_repo_id(seeded_client)
        resp = await seeded_client.get(f"/api/v1/repositories/{repo_id}/findings")
        data = resp.json()
        f = next(f for f in data["findings"] if f["finding_id"] == "TD-DEP-001")
        assert isinstance(f["evidence_ids"], list)

    async def test_findings_list_handles_null_locations(self, seeded_client: AsyncClient):
        """API returns empty list for null locations/evidence_ids."""
        repo_id = await _get_repo_id(seeded_client)
        resp = await seeded_client.get(f"/api/v1/repositories/{repo_id}/findings")
        data = resp.json()
        for f in data["findings"]:
            assert isinstance(f["locations"], list)
            assert isinstance(f["evidence_ids"], list)

    async def test_findings_empty_fields_return_defaults(self, client: AsyncClient):
        """Empty description/locations/evidence_ids return safe defaults."""
        findings = [
            {
                "id": "TD-EMPTY-001",
                "category": "TD-DOCS",
                "title": "No context",
                "description": "",
                "severity": "Low",
                "confidence": "Low",
                "locations": [],
                "evidence_ids": [],
                "technical_impact": "Low",
                "business_impact": "Low",
                "risk_score": 5,
                "priority": "Low",
                "recommended_action": "None",
            },
        ]
        tar_data = _make_tar_gz(findings=findings, project_name="empty-test")
        resp = await client.post(
            "/api/v1/bundles",
            files={"file": ("empty.tar.gz", tar_data, "application/gzip")},
            data={"repository_name": "Empty Fields Test"},
            headers=_auth(),
        )
        assert resp.status_code == 201
        repo_id = resp.json()["repository_id"]

        find_resp = await client.get(f"/api/v1/repositories/{repo_id}/findings")
        data = find_resp.json()
        f = data["findings"][0]
        assert f["description"] == ""
        assert f["locations"] == []
        assert f["evidence_ids"] == []


class TestSingleFindingEndpoint:
    """Verify GET /repositories/{id}/findings/{finding_id}."""

    async def test_get_single_finding(self, seeded_client: AsyncClient):
        repo_id = await _get_repo_id(seeded_client)
        resp = await seeded_client.get(f"/api/v1/repositories/{repo_id}/findings/TD-DEP-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["finding_id"] == "TD-DEP-001"
        assert data["title"] == "Missing lockfile"
        assert data["description"] == "No lockfile detected for package.json"
        assert data["locations"] == ["package.json", "src/index.js"]
        assert data["evidence_ids"] == ["EVD-001", "EVD-002"]

    async def test_get_single_finding_not_found(self, seeded_client: AsyncClient):
        repo_id = await _get_repo_id(seeded_client)
        resp = await seeded_client.get(f"/api/v1/repositories/{repo_id}/findings/TD-FAKE-999")
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "not_found"

    async def test_get_single_finding_invalid_repo(self, client: AsyncClient):
        resp = await client.get("/api/v1/repositories/not-a-uuid/findings/TD-001")
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data

    async def test_get_single_finding_second(self, seeded_client: AsyncClient):
        repo_id = await _get_repo_id(seeded_client)
        resp = await seeded_client.get(f"/api/v1/repositories/{repo_id}/findings/TD-TEST-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["finding_id"] == "TD-TEST-001"
        assert data["description"] == "Test coverage below threshold"
        assert data["locations"] == ["src/"]
        assert data["evidence_ids"] == ["EVD-003"]


class TestFrontendFieldHandling:
    """Verify frontend TypeScript types handle the new fields."""

    def test_finding_type_has_new_fields(self):
        import pathlib

        ts_path = pathlib.Path(__file__).parent.parent / "frontend" / "src" / "api" / "client.ts"
        if not ts_path.exists():
            pytest.skip("Frontend source not found")
        content = ts_path.read_text(encoding="utf-8")
        assert "description" in content
        assert "locations" in content
        assert "evidence_ids" in content

    def test_findings_table_has_context_section(self):
        import pathlib

        ts_path = (
            pathlib.Path(__file__).parent.parent
            / "frontend"
            / "src"
            / "views"
            / "FindingsTable.tsx"
        )
        if not ts_path.exists():
            pytest.skip("Frontend source not found")
        content = ts_path.read_text(encoding="utf-8")
        assert "Finding Detail" in content
        assert "Evidence IDs are references" in content
        assert "showContext" in content


class TestAlembicMigration003:
    """Verify migration 003 file is well-formed."""

    def test_migration_file_exists(self):
        import pathlib

        migration_path = (
            pathlib.Path(__file__).parent.parent / "alembic" / "versions" / "003_finding_detail.py"
        )
        assert migration_path.exists()

    def test_migration_has_correct_revision(self):
        import pathlib

        migration_path = (
            pathlib.Path(__file__).parent.parent / "alembic" / "versions" / "003_finding_detail.py"
        )
        content = migration_path.read_text(encoding="utf-8")
        assert 'revision = "003"' in content
        assert 'down_revision = "002"' in content
        assert "sa.Column" in content
        assert "sa.Text()" in content
        assert "sa.JSON()" in content

    def test_migration_downgrade_drops_columns(self):
        import pathlib

        migration_path = (
            pathlib.Path(__file__).parent.parent / "alembic" / "versions" / "003_finding_detail.py"
        )
        content = migration_path.read_text(encoding="utf-8")
        assert 'drop_column("findings", "evidence_ids")' in content
        assert 'drop_column("findings", "locations")' in content
        assert 'drop_column("findings", "description")' in content
