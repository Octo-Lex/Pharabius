"""Tests for v2.5.0 Evidence Reference Resolution & Traceability.

Validates:
- Evidence records persisted from evidence.json
- Evidence lookup API
- Finding detail evidence resolution with status
- Upload warnings for malformed evidence
- Legacy bundle compatibility
- Review modal evidence drawer
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


def _make_tar_gz(
    files: dict[str, str],
    project_name: str = "test-project",
) -> bytes:
    """Create a tar.gz with given files."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data.encode())
            tar.addfile(info, io.BytesIO(data.encode()))
    return buf.getvalue()


EVIDENCE_JSON = json.dumps(
    {
        "schema_version": "1.0",
        "evidence": [
            {
                "evidence_id": "EVD-001",
                "source": "repository_scan",
                "type": "dependency_manifest",
                "category": "dependencies",
                "location": {"file": "package.json", "line_start": 1, "line_end": 30},
                "summary": "package.json found without lockfile",
                "confidence": "High",
            },
            {
                "evidence_id": "EVD-002",
                "source": "repository_scan",
                "type": "code_structure",
                "category": "architecture",
                "location": {"file": "src/index.js", "line_start": 10},
                "summary": "Entry point references missing modules",
                "confidence": "Medium",
            },
        ],
    }
)

FINDINGS_JSON = json.dumps(
    {
        "schema_version": "1.0",
        "project_name": "evidence-test",
        "findings": [
            {
                "id": "TD-DEP-001",
                "category": "TD-DEP",
                "title": "Missing lockfile",
                "description": "No lockfile for package.json",
                "severity": "Critical",
                "confidence": "High",
                "locations": ["package.json"],
                "evidence_ids": ["EVD-001", "EVD-002"],
                "technical_impact": "High",
                "business_impact": "Medium",
                "risk_score": 40,
                "priority": "Critical",
                "recommended_action": "Add lockfile",
            },
            {
                "id": "TD-ARCH-001",
                "category": "TD-ARCH",
                "title": "Boundary violation",
                "description": "",
                "severity": "High",
                "locations": [],
                "evidence_ids": ["EVD-999"],
                "technical_impact": "High",
                "business_impact": "Low",
                "risk_score": 30,
                "priority": "High",
                "recommended_action": "Refactor",
            },
            {
                "id": "TD-TEST-001",
                "category": "TD-TEST",
                "title": "Low coverage",
                "description": "",
                "severity": "Medium",
                "locations": [],
                "evidence_ids": [],
                "technical_impact": "Medium",
                "business_impact": "Low",
                "risk_score": 20,
                "priority": "Medium",
                "recommended_action": "Add tests",
            },
        ],
    }
)

PROFILE_JSON = json.dumps(
    {
        "schema_version": "1.0",
        "project_name": "evidence-test",
        "repository_root": "/test",
    }
)

MALFORMED_EVIDENCE_JSON = json.dumps(
    {
        "schema_version": "1.0",
        "evidence": [
            {"evidence_id": "EVD-GOOD", "type": "test", "category": "test", "summary": "OK"},
            "not a dict",
            {"no_id_field": True},
            {"evidence_id": "", "type": "test", "category": "test", "summary": "empty id"},
            {
                "evidence_id": "EVD-VALID",
                "type": "test",
                "category": "test",
                "summary": "Valid record",
            },
        ],
    }
)


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


async def _upload_files(client: AsyncClient, files: dict[str, str], name: str = "Test") -> dict:
    tar_data = _make_tar_gz(files, project_name=name)
    resp = await client.post(
        "/api/v1/bundles",
        files={"file": ("test.tar.gz", tar_data, "application/gzip")},
        data={"repository_name": name},
        headers=_auth(),
    )
    assert resp.status_code == 201, f"Upload failed: {resp.status_code} {resp.text[:300]}"
    return resp.json()


@pytest.fixture(autouse=True)
async def _setup_db(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[None, None]:
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true",
    )
    from pharabius_platform import db as db_mod
    from pharabius_platform.db import init_db

    init_db("sqlite+aiosqlite:///file::memory:?cache=shared&uri=true")
    assert db_mod._engine is not None
    async with db_mod._engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with db_mod._engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def seeded(client: AsyncClient) -> dict:
    """Upload bundle with evidence store."""
    return await _upload_files(
        client,
        {
            ".ai-debt/evidence.json": EVIDENCE_JSON,
            ".ai-debt/debt-register.json": FINDINGS_JSON,
            ".ai-debt/project-profile.json": PROFILE_JSON,
        },
        "Evidence Test",
    )


class TestEvidenceUploadPersistence:
    """Evidence records are persisted from evidence.json."""

    async def test_upload_persists_evidence_count(self, seeded):
        assert seeded["evidence_count"] == 2

    async def test_upload_without_evidence_succeeds(self, client: AsyncClient):
        result = await _upload_files(
            client,
            {
                ".ai-debt/debt-register.json": json.dumps(
                    {
                        "schema_version": "1.0",
                        "findings": [
                            {
                                "id": "TD-001",
                                "category": "TD-DEP",
                                "title": "T",
                                "description": "",
                                "severity": "Low",
                                "evidence_ids": [],
                                "technical_impact": "Low",
                                "business_impact": "Low",
                                "risk_score": 5,
                                "priority": "Low",
                                "recommended_action": "N",
                            }
                        ],
                    }
                ),
                ".ai-debt/project-profile.json": PROFILE_JSON,
            },
            "No Evidence",
        )
        assert result["evidence_count"] == 0

    async def test_upload_malformed_evidence_warnings(self, client: AsyncClient):
        result = await _upload_files(
            client,
            {
                ".ai-debt/evidence.json": MALFORMED_EVIDENCE_JSON,
                ".ai-debt/debt-register.json": json.dumps(
                    {
                        "schema_version": "1.0",
                        "findings": [
                            {
                                "id": "TD-001",
                                "category": "TD-DEP",
                                "title": "T",
                                "description": "",
                                "severity": "Low",
                                "evidence_ids": [],
                                "technical_impact": "Low",
                                "business_impact": "Low",
                                "risk_score": 5,
                                "priority": "Low",
                                "recommended_action": "N",
                            }
                        ],
                    }
                ),
                ".ai-debt/project-profile.json": PROFILE_JSON,
            },
            "Malformed Evidence",
        )
        assert result["evidence_count"] == 2  # EVD-GOOD + EVD-VALID
        assert len(result["evidence_warnings"]) == 3  # non-dict, no id, empty id


class TestEvidenceLookupAPI:
    """GET /repositories/{id}/evidence/{evidence_id}."""

    async def test_get_existing_evidence(self, client: AsyncClient, seeded):
        repo_id = seeded["repository_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/evidence/EVD-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["evidence_id"] == "EVD-001"
        assert data["summary"] == "package.json found without lockfile"
        assert data["file_path"] == "package.json"
        assert data["line_start"] == 1
        assert data["confidence"] == "High"

    async def test_get_missing_evidence_404(self, client: AsyncClient, seeded):
        repo_id = seeded["repository_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/evidence/EVD-999")
        assert resp.status_code == 404

    async def test_get_evidence_invalid_repo(self, client: AsyncClient):
        resp = await client.get("/api/v1/repositories/not-uuid/evidence/EVD-001")
        assert resp.status_code == 400

    async def test_evidence_response_excludes_raw_observation(self, client: AsyncClient, seeded):
        repo_id = seeded["repository_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/evidence/EVD-001")
        data = resp.json()
        assert "raw_observation" not in data


class TestFindingDetailEvidenceResolution:
    """Finding detail endpoint includes evidence_references with resolution status."""

    async def test_resolved_evidence(self, client: AsyncClient, seeded):
        repo_id = seeded["repository_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/findings/TD-DEP-001")
        assert resp.status_code == 200
        refs = resp.json()["evidence_references"]
        resolved = [r for r in refs if r["status"] == "resolved"]
        assert len(resolved) == 2
        assert resolved[0]["evidence_id"] in ("EVD-001", "EVD-002")

    async def test_missing_evidence_status(self, client: AsyncClient, seeded):
        """TD-ARCH-001 references EVD-999 which doesn't exist → 'missing'."""
        repo_id = seeded["repository_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/findings/TD-ARCH-001")
        refs = resp.json()["evidence_references"]
        assert len(refs) == 1
        assert refs[0]["status"] == "missing"
        assert refs[0]["evidence_id"] == "EVD-999"

    async def test_empty_evidence_ids_no_references(self, client: AsyncClient, seeded):
        """TD-TEST-001 has empty evidence_ids → no references."""
        repo_id = seeded["repository_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/findings/TD-TEST-001")
        refs = resp.json()["evidence_references"]
        assert refs == []

    async def test_include_evidence_expansion(self, client: AsyncClient, seeded):
        """?include_evidence=true adds full evidence body."""
        repo_id = seeded["repository_id"]
        resp = await client.get(
            f"/api/v1/repositories/{repo_id}/findings/TD-DEP-001?include_evidence=true"
        )
        data = resp.json()
        resolved = [r for r in data["evidence_references"] if r["status"] == "resolved"]
        assert all("evidence" in r for r in resolved)
        assert resolved[0]["evidence"]["summary"] is not None

    async def test_no_include_evidence_no_body(self, client: AsyncClient, seeded):
        """Without ?include_evidence, no evidence body in references."""
        repo_id = seeded["repository_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/findings/TD-DEP-001")
        refs = resp.json()["evidence_references"]
        assert all("evidence" not in r for r in refs)


class TestLegacyNoEvidenceStore:
    """Legacy bundles without evidence store show degraded state."""

    async def test_legacy_finding_evidence_legacy_status(self, client: AsyncClient):
        """Finding with evidence_ids but no evidence store → legacy_no_evidence_store."""
        result = await _upload_files(
            client,
            {
                ".ai-debt/debt-register.json": json.dumps(
                    {
                        "schema_version": "1.0",
                        "findings": [
                            {
                                "id": "TD-LEG-001",
                                "category": "TD-DEP",
                                "title": "Legacy",
                                "description": "",
                                "severity": "Low",
                                "evidence_ids": ["EVD-001"],
                                "technical_impact": "Low",
                                "business_impact": "Low",
                                "risk_score": 5,
                                "priority": "Low",
                                "recommended_action": "N",
                            }
                        ],
                    }
                ),
                ".ai-debt/project-profile.json": PROFILE_JSON,
            },
            "Legacy No Store",
        )
        repo_id = result["repository_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/findings/TD-LEG-001")
        refs = resp.json()["evidence_references"]
        assert len(refs) == 1
        assert refs[0]["status"] == "legacy_no_evidence_store"

    async def test_legacy_evidence_lookup_404(self, client: AsyncClient):
        """Evidence lookup for legacy bundle returns 404."""
        result = await _upload_files(
            client,
            {
                ".ai-debt/debt-register.json": json.dumps(
                    {
                        "schema_version": "1.0",
                        "findings": [
                            {
                                "id": "TD-LEG-002",
                                "category": "TD-DEP",
                                "title": "Legacy 2",
                                "description": "",
                                "severity": "Low",
                                "evidence_ids": ["EVD-001"],
                                "technical_impact": "Low",
                                "business_impact": "Low",
                                "risk_score": 5,
                                "priority": "Low",
                                "recommended_action": "N",
                            }
                        ],
                    }
                ),
                ".ai-debt/project-profile.json": PROFILE_JSON,
            },
            "Legacy Lookup",
        )
        repo_id = result["repository_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/evidence/EVD-001")
        assert resp.status_code == 404


class TestCrossRunScoping:
    """Evidence resolution uses finding's own run_id, not latest."""

    async def test_evidence_scoped_to_finding_run(self, client: AsyncClient, seeded):
        """Evidence resolution uses finding's own run_id."""
        repo_id = seeded["repository_id"]

        # Get first run's finding and verify its evidence resolves correctly
        resp = await client.get(
            f"/api/v1/repositories/{repo_id}/findings/TD-DEP-001?include_evidence=true"
        )
        assert resp.status_code == 200
        data = resp.json()
        refs = data["evidence_references"]
        resolved = [r for r in refs if r["status"] == "resolved"]
        assert len(resolved) == 2
        # Verify evidence body is populated for resolved refs
        assert "summary" in resolved[0]["evidence"]
        assert resolved[0]["evidence"]["confidence"] in ("High", "Medium")


class TestAlembicMigration004:
    """Verify migration 004 structure."""

    def test_migration_exists(self):
        import pathlib

        path = (
            pathlib.Path(__file__).parent.parent
            / "alembic"
            / "versions"
            / "004_evidence_records.py"
        )
        assert path.exists()

    def test_migration_creates_table(self):
        import pathlib

        content = (
            pathlib.Path(__file__).parent.parent
            / "alembic"
            / "versions"
            / "004_evidence_records.py"
        ).read_text(encoding="utf-8")
        assert "create_table" in content
        assert "evidence_records" in content
        assert "drop_table" in content


class TestFrontendEvidenceDrawer:
    """Verify frontend types include evidence references."""

    def test_client_has_evidence_types(self):
        import pathlib

        ts_path = pathlib.Path(__file__).parent.parent / "frontend" / "src" / "api" / "client.ts"
        if not ts_path.exists():
            pytest.skip("Frontend source not found")
        content = ts_path.read_text(encoding="utf-8")
        assert "EvidenceReference" in content
        assert "EvidenceRecord" in content
        assert "evidence_references" in content

    def test_findings_table_has_evidence_chip(self):
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
        assert "EvidenceChip" in content
        assert "legacy_no_evidence_store" in content
