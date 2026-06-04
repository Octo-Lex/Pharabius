"""Tests for v2.6.0 — Evidence-Backed Work Package Linkage.

Covers: upload parsing, work package persistence, finding links,
API list/detail, evidence basis derivation, degraded states,
cross-run isolation, malformed references, empty states.
"""

from __future__ import annotations

import io
import json
import os
import tarfile
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from pharabius_platform.db import get_session, init_db
from pharabius_platform.main import app
from pharabius_platform.models import Base

ADMIN_TOKEN = "test-admin-token"
os.environ.setdefault("ADMIN_TOKEN", ADMIN_TOKEN)
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true")

PROFILE_JSON = json.dumps(
    {
        "project_name": "Evidence Test",
        "ecosystem": "python",
        "language": "python",
        "framework": "fastapi",
        "package_manager": "pip",
    }
)

EVIDENCE_JSON = json.dumps(
    {
        "schema_version": "1.0",
        "evidence": [
            {
                "evidence_id": "EVD-000001",
                "type": "code_structure",
                "category": "architecture",
                "summary": "Authorization logic appears in multiple route handlers.",
                "confidence": "High",
                "source": "repository_scan",
                "location": {"file": "src/routes/admin.ts", "line_start": 32, "line_end": 74},
            },
            {
                "evidence_id": "EVD-000002",
                "type": "code_structure",
                "category": "architecture",
                "summary": "Middleware bypass in error handling.",
                "confidence": "Medium",
                "source": "repository_scan",
                "location": {"file": "src/middleware/auth.ts", "line_start": 10},
            },
        ],
    }
)

FINDINGS_JSON = json.dumps(
    {
        "schema_version": "1.0",
        "findings": [
            {
                "id": "TD-ARCH-001",
                "category": "TD-ARCH",
                "title": "Authorization boundary drift",
                "description": "Auth logic scattered across handlers.",
                "severity": "High",
                "evidence_ids": ["EVD-000001", "EVD-000002"],
                "technical_impact": "High",
                "business_impact": "High",
                "risk_score": 20,
                "priority": "High",
                "recommended_action": "Refactor",
            },
            {
                "id": "TD-TEST-001",
                "category": "TD-TEST",
                "title": "Missing integration tests",
                "description": "",
                "severity": "Medium",
                "evidence_ids": ["EVD-000001"],
                "technical_impact": "Medium",
                "business_impact": "Low",
                "risk_score": 10,
                "priority": "Medium",
                "recommended_action": "Add tests",
            },
        ],
    }
)


def _make_wp_markdown(
    wp_id: str = "WP-001",
    title: str = "Stabilize authorization boundary",
    linked_items: list[str] | None = None,
    objective: str = "Consolidate auth checks.",
    evidence: list[str] | None = None,
) -> str:
    """Generate a work package Markdown file."""
    items = linked_items or ["TD-ARCH-001", "TD-TEST-001"]
    ev = evidence or ["EVD-000001", "EVD-000002"]
    lines = [
        f"# Work Package: {wp_id} {title}",
        "",
        "## Status",
        "",
        "Ready for Product Engineering review",
        "",
        "## Linked Debt Items",
        "",
    ]
    for item in items:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## Objective",
            "",
            objective,
            "",
            "## Evidence",
            "",
        ]
    )
    for e in ev:
        lines.append(f"- `{e}`")
    lines.extend(
        [
            "",
            "## Current Risk",
            "",
            "High risk of auth bypass.",
            "",
            "## Recommended Engineering Approach",
            "",
            "1. Extract authorization middleware",
            "2. Add integration tests",
            "",
            "## Expected Affected Areas",
            "",
            "- src/routes/",
            "- src/middleware/",
            "",
            "## Verification Recommendations",
            "",
            "- Run authorization test suite",
            "- Verify no regression",
            "",
            "## Risks and Cautions",
            "",
            "- Temporary downtime during migration",
            "",
            "## Definition of Done",
            "",
            "- Authorization middleware extracted",
            "- Integration tests passing",
            "",
            "## Estimated Effort",
            "",
            "Medium",
        ]
    )
    return "\n".join(lines)


def _make_tar_gz(files: dict[str, str | bytes]) -> bytes:
    """Create a tar.gz bundle from {path: content}."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path, content in files.items():
            if isinstance(content, str):
                content = content.encode("utf-8")
            info = tarfile.TarInfo(name=path)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return buf.getvalue()


async def _upload_files(
    client: AsyncClient,
    files: dict[str, str | bytes],
    name: str = "WP Test Repo",
) -> dict[str, object]:
    """Upload a bundle and return the parsed response."""
    tar_data = _make_tar_gz(files)
    resp = await client.post(
        "/api/v1/bundles",
        files={"file": ("bundle.tar.gz", tar_data, "application/gzip")},
        data={"repository_name": name},
        headers={"Authorization": "Bearer " + ADMIN_TOKEN},
    )
    assert resp.status_code == 201, f"Upload failed: {resp.status_code} {resp.text}"
    return resp.json()


@pytest.fixture(autouse=True)
async def _setup_db(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[None, None]:
    """Create and drop all tables per test for isolation."""
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true",
    )
    from pharabius_platform import db as db_mod

    init_db("sqlite+aiosqlite:///file::memory:?cache=shared&uri=true")
    assert db_mod._engine is not None
    async with db_mod._engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    TestSession = sessionmaker(db_mod._engine, class_=AsyncSession, expire_on_commit=False)

    async def override():
        async with TestSession() as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield
    app.dependency_overrides.clear()
    async with db_mod._engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client() -> AsyncClient:
    """Async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def seeded(client: AsyncClient) -> dict[str, object]:
    """Upload a bundle with work packages and return key IDs."""
    wp_md = _make_wp_markdown()
    result = await _upload_files(
        client,
        {
            ".ai-debt/project-profile.json": PROFILE_JSON,
            ".ai-debt/debt-register.json": FINDINGS_JSON,
            ".ai-debt/evidence.json": EVIDENCE_JSON,
            ".ai-debt/work-packages/WP-001-stabilize-auth.md": wp_md,
        },
    )
    return result


# ── Upload Tests ───────────────────────────────────────────────────


class TestWorkPackageUpload:
    """Work package parsing and persistence during upload."""

    async def test_work_packages_parsed(self, client: AsyncClient) -> None:
        result = await _upload_files(
            client,
            {
                ".ai-debt/project-profile.json": PROFILE_JSON,
                ".ai-debt/debt-register.json": FINDINGS_JSON,
                ".ai-debt/evidence.json": EVIDENCE_JSON,
                ".ai-debt/work-packages/WP-001-stabilize-auth.md": _make_wp_markdown(),
            },
        )
        assert result["work_package_count"] == 1
        assert result["work_package_warnings"] == []

    async def test_no_work_packages_is_ok(self, client: AsyncClient) -> None:
        result = await _upload_files(
            client,
            {
                ".ai-debt/project-profile.json": PROFILE_JSON,
                ".ai-debt/debt-register.json": FINDINGS_JSON,
                ".ai-debt/evidence.json": EVIDENCE_JSON,
            },
        )
        assert result["work_package_count"] == 0
        assert result["work_package_warnings"] == []

    async def test_multiple_work_packages(self, client: AsyncClient) -> None:
        wp1 = _make_wp_markdown("WP-001", "First package", ["TD-ARCH-001"])
        wp2 = _make_wp_markdown("WP-002", "Second package", ["TD-TEST-001"])
        result = await _upload_files(
            client,
            {
                ".ai-debt/project-profile.json": PROFILE_JSON,
                ".ai-debt/debt-register.json": FINDINGS_JSON,
                ".ai-debt/evidence.json": EVIDENCE_JSON,
                ".ai-debt/work-packages/WP-001-first.md": wp1,
                ".ai-debt/work-packages/WP-002-second.md": wp2,
            },
        )
        assert result["work_package_count"] == 2

    async def test_missing_linked_finding_preserved(self, client: AsyncClient) -> None:
        """Work package references finding not in this upload."""
        wp = _make_wp_markdown(linked_items=["TD-ARCH-001", "TD-ARCH-999"])
        result = await _upload_files(
            client,
            {
                ".ai-debt/project-profile.json": PROFILE_JSON,
                ".ai-debt/debt-register.json": FINDINGS_JSON,
                ".ai-debt/evidence.json": EVIDENCE_JSON,
                ".ai-debt/work-packages/WP-001-missing.md": wp,
            },
        )
        assert result["work_package_count"] == 1
        repo_id = result["repository_id"]

        # Verify missing link preserved
        resp = await client.get(f"/api/v1/repositories/{repo_id}/work-packages/WP-001")
        assert resp.status_code == 200
        data = resp.json()
        statuses = [lf["status"] for lf in data["linked_findings"]]
        assert "resolved" in statuses
        assert "missing" in statuses

    async def test_malformed_work_package_warning(self, client: AsyncClient) -> None:
        """Non-WP-*.md file in work-packages dir is ignored."""
        result = await _upload_files(
            client,
            {
                ".ai-debt/project-profile.json": PROFILE_JSON,
                ".ai-debt/debt-register.json": FINDINGS_JSON,
                ".ai-debt/evidence.json": EVIDENCE_JSON,
                ".ai-debt/work-packages/README.md": "Not a work package",
            },
        )
        assert result["work_package_count"] == 0

    async def test_duplicate_package_id_warning(self, client: AsyncClient) -> None:
        """Two files with same WP ID → second skipped."""
        wp1 = _make_wp_markdown("WP-001", "First")
        wp2 = _make_wp_markdown("WP-001", "Duplicate")
        result = await _upload_files(
            client,
            {
                ".ai-debt/project-profile.json": PROFILE_JSON,
                ".ai-debt/debt-register.json": FINDINGS_JSON,
                ".ai-debt/evidence.json": EVIDENCE_JSON,
                ".ai-debt/work-packages/WP-001-first.md": wp1,
                ".ai-debt/work-packages/WP-001-second.md": wp2,
            },
        )
        assert result["work_package_count"] == 1
        assert len(result["work_package_warnings"]) == 1
        assert result["work_package_warnings"][0]["code"] == "duplicate_work_package_id"


# ── API List Tests ─────────────────────────────────────────────────


class TestWorkPackageList:
    """Work package list endpoint."""

    async def test_list_work_packages(self, client: AsyncClient, seeded) -> None:
        repo_id = seeded["repository_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/work-packages")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["work_packages"][0]["package_id"] == "WP-001"
        assert data["work_packages"][0]["linked_finding_count"] == 2

    async def test_list_empty(self, client: AsyncClient) -> None:
        result = await _upload_files(
            client,
            {
                ".ai-debt/project-profile.json": PROFILE_JSON,
                ".ai-debt/debt-register.json": FINDINGS_JSON,
                ".ai-debt/evidence.json": EVIDENCE_JSON,
            },
        )
        repo_id = result["repository_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/work-packages")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_list_invalid_repo(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/repositories/invalid-uuid/work-packages")
        assert resp.status_code == 400


# ── API Detail Tests ───────────────────────────────────────────────


class TestWorkPackageDetail:
    """Work package detail endpoint."""

    async def test_detail_basic(self, client: AsyncClient, seeded) -> None:
        repo_id = seeded["repository_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/work-packages/WP-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["package_id"] == "WP-001"
        assert data["title"] == "WP-001 Stabilize authorization boundary"
        assert data["objective"] == "Consolidate auth checks."
        assert len(data["linked_findings"]) == 2

    async def test_detail_404(self, client: AsyncClient, seeded) -> None:
        repo_id = seeded["repository_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/work-packages/WP-999")
        assert resp.status_code == 404

    async def test_detail_include_findings(self, client: AsyncClient, seeded) -> None:
        repo_id = seeded["repository_id"]
        resp = await client.get(
            f"/api/v1/repositories/{repo_id}/work-packages/WP-001?include_findings=true"
        )
        assert resp.status_code == 200
        data = resp.json()
        resolved = [lf for lf in data["linked_findings"] if lf["status"] == "resolved"]
        assert len(resolved) == 2
        # Finding bodies populated
        for lf in resolved:
            assert lf["finding"] is not None
            assert "finding_id" in lf["finding"]

    async def test_detail_include_evidence(self, client: AsyncClient, seeded) -> None:
        repo_id = seeded["repository_id"]
        resp = await client.get(
            f"/api/v1/repositories/{repo_id}/work-packages/WP-001?include_evidence=true"
        )
        assert resp.status_code == 200
        data = resp.json()
        # include_evidence implies include_findings
        resolved = [lf for lf in data["linked_findings"] if lf["status"] == "resolved"]
        assert len(resolved) == 2
        # Evidence references populated
        for lf in resolved:
            if lf["finding"] is not None:
                assert len(lf["evidence_references"]) > 0
                # Check evidence bodies
                for ref in lf["evidence_references"]:
                    assert "evidence_id" in ref
                    assert "status" in ref

    async def test_detail_evidence_resolved_status(self, client: AsyncClient, seeded) -> None:
        repo_id = seeded["repository_id"]
        resp = await client.get(
            f"/api/v1/repositories/{repo_id}/work-packages/WP-001?include_evidence=true"
        )
        data = resp.json()
        # TD-ARCH-001 has EVD-000001 and EVD-000002 — both should resolve
        arch_lf = next(lf for lf in data["linked_findings"] if lf["debt_item_id"] == "TD-ARCH-001")
        assert arch_lf["status"] == "resolved"
        ev_refs = arch_lf["evidence_references"]
        resolved_ev = [r for r in ev_refs if r["status"] == "resolved"]
        assert len(resolved_ev) == 2
        assert resolved_ev[0]["evidence"]["summary"] != ""


# ── Cross-Run Isolation ───────────────────────────────────────────


class TestCrossRunIsolation:
    """Work packages are run-scoped."""

    async def test_no_cross_run_leakage(self, client: AsyncClient) -> None:
        """Upload two bundles to same repo, verify run scoping."""
        # First upload with WP
        wp1 = _make_wp_markdown("WP-001", "First run WP", ["TD-ARCH-001"])
        r1 = await _upload_files(
            client,
            {
                ".ai-debt/project-profile.json": PROFILE_JSON,
                ".ai-debt/debt-register.json": FINDINGS_JSON,
                ".ai-debt/evidence.json": EVIDENCE_JSON,
                ".ai-debt/work-packages/WP-001-first.md": wp1,
            },
        )
        repo_id = r1["repository_id"]
        run1_id = r1["run_id"]
        assert run1_id is not None

        # Second upload without WP (should not leak)
        r2 = await _upload_files(
            client,
            {
                ".ai-debt/project-profile.json": PROFILE_JSON,
                ".ai-debt/debt-register.json": FINDINGS_JSON,
                ".ai-debt/evidence.json": EVIDENCE_JSON,
            },
        )
        assert r2["repository_id"] == repo_id
        run2_id = r2["run_id"]
        assert run2_id is not None
        assert run2_id != run1_id

        # Run 2 (latest) should show no work packages
        resp = await client.get(f"/api/v1/repositories/{repo_id}/work-packages?run_id={run2_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

        # Run 1 should still have work packages
        resp = await client.get(f"/api/v1/repositories/{repo_id}/work-packages?run_id={run1_id}")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


# ── Degraded States ───────────────────────────────────────────────


class TestDegradedStates:
    """Missing and malformed references are preserved."""

    async def test_missing_finding_in_detail(self, client: AsyncClient) -> None:
        wp = _make_wp_markdown(linked_items=["TD-ARCH-001", "TD-ARCH-999"])
        result = await _upload_files(
            client,
            {
                ".ai-debt/project-profile.json": PROFILE_JSON,
                ".ai-debt/debt-register.json": FINDINGS_JSON,
                ".ai-debt/evidence.json": EVIDENCE_JSON,
                ".ai-debt/work-packages/WP-001-missing.md": wp,
            },
        )
        repo_id = result["repository_id"]
        resp = await client.get(
            f"/api/v1/repositories/{repo_id}/work-packages/WP-001?include_findings=true"
        )
        data = resp.json()
        missing = [lf for lf in data["linked_findings"] if lf["status"] == "missing"]
        assert len(missing) == 1
        assert missing[0]["debt_item_id"] == "TD-ARCH-999"
        assert missing[0]["finding"] is None
        assert missing[0]["reason"] is not None

    async def test_malformed_debt_item_normalized(self, client: AsyncClient) -> None:
        """Empty debt item is normalized to __malformed__:N."""
        # Manually craft a WP with empty linked items
        wp_content = _make_wp_markdown(linked_items=["TD-ARCH-001"])
        # Inject an empty item
        wp_content = wp_content.replace(
            "- `TD-ARCH-001`",
            "- `TD-ARCH-001`\n- ` `",
        )
        result = await _upload_files(
            client,
            {
                ".ai-debt/project-profile.json": PROFILE_JSON,
                ".ai-debt/debt-register.json": FINDINGS_JSON,
                ".ai-debt/evidence.json": EVIDENCE_JSON,
                ".ai-debt/work-packages/WP-001-malformed.md": wp_content,
            },
        )
        repo_id = result["repository_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/work-packages/WP-001")
        data = resp.json()
        malformed = [lf for lf in data["linked_findings"] if lf["status"] == "malformed_reference"]
        assert len(malformed) == 1
        assert malformed[0]["debt_item_id"].startswith("__malformed__")

    async def test_finding_with_missing_evidence(self, client: AsyncClient) -> None:
        """Resolved finding references missing evidence."""
        wp = _make_wp_markdown(linked_items=["TD-ARCH-001"])
        # Findings reference EVD-000001, EVD-000002 which exist
        # Add an evidence ID that doesn't exist
        findings = json.loads(FINDINGS_JSON)
        findings["findings"][0]["evidence_ids"] = [
            "EVD-000001",
            "EVD-999999",  # Missing
        ]
        result = await _upload_files(
            client,
            {
                ".ai-debt/project-profile.json": PROFILE_JSON,
                ".ai-debt/debt-register.json": json.dumps(findings),
                ".ai-debt/evidence.json": EVIDENCE_JSON,
                ".ai-debt/work-packages/WP-001-missing-ev.md": wp,
            },
        )
        repo_id = result["repository_id"]
        resp = await client.get(
            f"/api/v1/repositories/{repo_id}/work-packages/WP-001?include_evidence=true"
        )
        data = resp.json()
        arch_lf = next(lf for lf in data["linked_findings"] if lf["debt_item_id"] == "TD-ARCH-001")
        missing_ev = [r for r in arch_lf["evidence_references"] if r["status"] == "missing"]
        assert len(missing_ev) == 1
        assert missing_ev[0]["evidence_id"] == "EVD-999999"


# ── Migration Test ─────────────────────────────────────────────────


class TestAlembicMigration005:
    """Verify migration 005 structure."""

    def test_migration_exists(self) -> None:
        import pathlib

        path = (
            pathlib.Path(__file__).parent.parent / "alembic" / "versions" / "005_work_packages.py"
        )
        assert path.exists(), "Migration 005 not found"

    def test_model_table_count(self) -> None:
        assert len(Base.metadata.tables) == 14

    def test_work_package_table_exists(self) -> None:
        assert "work_packages" in Base.metadata.tables

    def test_work_package_findings_table_exists(self) -> None:
        assert "work_package_findings" in Base.metadata.tables
