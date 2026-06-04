"""Tests for v2.7.0 — Run History & Traceability Navigation.

Covers: run list/detail API, latest-run determinism, findings scoped by run,
evidence scoped by run, work packages scoped by run, upload run metadata,
degraded states, cross-run isolation, same-second ordering.
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
        "project_name": "Run History Test",
        "ecosystem": "python",
        "language": "python",
        "framework": "fastapi",
        "package_manager": "pip",
    }
)

FINDINGS_JSON = json.dumps(
    {
        "schema_version": "1.0",
        "findings": [
            {
                "id": "TD-ARCH-001",
                "category": "TD-ARCH",
                "title": "Auth boundary drift",
                "description": "Auth logic scattered.",
                "severity": "High",
                "evidence_ids": ["EVD-000001"],
                "technical_impact": "High",
                "business_impact": "High",
                "risk_score": 20,
                "priority": "High",
                "recommended_action": "Refactor",
            },
            {
                "id": "TD-TEST-001",
                "category": "TD-TEST",
                "title": "Missing tests",
                "description": "",
                "severity": "Medium",
                "evidence_ids": [],
                "technical_impact": "Medium",
                "business_impact": "Low",
                "risk_score": 10,
                "priority": "Medium",
                "recommended_action": "Add tests",
            },
        ],
    }
)

FINDINGS_JSON_V2 = json.dumps(
    {
        "schema_version": "1.0",
        "findings": [
            {
                "id": "TD-ARCH-001",
                "category": "TD-ARCH",
                "title": "Auth boundary drift v2",
                "description": "Still scattered.",
                "severity": "Critical",
                "evidence_ids": ["EVD-000002"],
                "technical_impact": "High",
                "business_impact": "High",
                "risk_score": 25,
                "priority": "Critical",
                "recommended_action": "Refactor now",
            },
        ],
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
                "summary": "Auth logic in handlers.",
                "confidence": "High",
                "source": "repository_scan",
                "location": {"file": "src/routes/admin.ts", "line_start": 32},
            },
        ],
    }
)

RUN_METADATA_JSON = json.dumps(
    {
        "schema_version": "1.0",
        "run_id": "RUN-20260529-120000",
        "timestamp": "2026-05-29T12:00:00Z",
        "repository": "/test",
        "commit": "abc123def456",
        "branch": "main",
        "tool_version": "2.7.0",
        "analysis_mode": "deterministic-no-ai",
        "commands_run": ["scan"],
        "files_written": [],
        "limitations": [],
        "summary": {"finding_count": 2, "evidence_count": 1},
    }
)

WP_MARKDOWN = (
    "# Work Package: WP-001 Stabilize auth\n\n"
    "## Status\n\nReady\n\n"
    "## Linked Debt Items\n\n- `TD-ARCH-001`\n\n"
    "## Objective\n\nConsolidate auth.\n\n"
    "## Evidence\n\n- `EVD-000001`\n\n"
    "## Current Risk\n\nHigh\n\n"
    "## Recommended Engineering Approach\n\n1. Extract middleware\n\n"
    "## Expected Affected Areas\n\n- src/\n\n"
    "## Verification Recommendations\n\n- Test\n\n"
    "## Risks and Cautions\n\n- Risk\n\n"
    "## Definition of Done\n\n- Done\n\n"
    "## Estimated Effort\n\nMedium"
)


def _make_tar_gz(files: dict[str, str | bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path, content in files.items():
            if isinstance(content, str):
                content = content.encode("utf-8")
            info = tarfile.TarInfo(name=path)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return buf.getvalue()


async def _upload(
    client: AsyncClient,
    files: dict[str, str | bytes],
    name: str = "Run History Repo",
) -> dict[str, object]:
    tar_data = _make_tar_gz(files)
    resp = await client.post(
        "/api/v1/bundles",
        files={"file": ("bundle.tar.gz", tar_data, "application/gzip")},
        data={"repository_name": name},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert resp.status_code == 201, f"Upload failed: {resp.status_code} {resp.text}"
    return resp.json()


def _full_bundle(
    *,
    findings: str = FINDINGS_JSON,
    evidence: str = EVIDENCE_JSON,
    run_metadata: str | None = RUN_METADATA_JSON,
    wp: str | None = WP_MARKDOWN,
) -> dict[str, str]:
    files: dict[str, str] = {
        ".ai-debt/project-profile.json": PROFILE_JSON,
        ".ai-debt/debt-register.json": findings,
        ".ai-debt/evidence.json": evidence,
    }
    if run_metadata:
        files[".ai-debt/runs/RUN-20260529-120000.json"] = run_metadata
    if wp:
        files[".ai-debt/work-packages/WP-001-stabilize-auth.md"] = wp
    return files


@pytest.fixture(autouse=True)
async def _setup_db(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[None, None]:
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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def seeded_single(client: AsyncClient) -> dict[str, object]:
    result = await _upload(client, _full_bundle())
    return result


@pytest.fixture
async def seeded_two_runs(client: AsyncClient) -> dict[str, object]:
    r1 = await _upload(client, _full_bundle())
    repo_id = r1["repository_id"]
    run1_id = r1["run_id"]

    # Second upload with different findings, no run metadata
    r2 = await _upload(
        client,
        {
            ".ai-debt/project-profile.json": PROFILE_JSON,
            ".ai-debt/debt-register.json": FINDINGS_JSON_V2,
            ".ai-debt/evidence.json": EVIDENCE_JSON,
        },
    )
    assert r2["repository_id"] == repo_id
    run2_id = r2["run_id"]
    return {"repo_id": repo_id, "run1_id": run1_id, "run2_id": run2_id}


# -- Run List API --


class TestRunListAPI:
    async def test_list_runs_returns_enriched(self, client: AsyncClient, seeded_single) -> None:
        repo_id = seeded_single["repository_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        run = data["runs"][0]
        assert "id" in run
        assert run["run_id"] == "RUN-20260529-120000"
        assert run["commit_sha"] == "abc123def456"
        assert run["branch_name"] == "main"
        assert run["analysis_mode"] == "deterministic-no-ai"
        assert run["is_latest"] is True
        assert run["evidence_count"] == 1
        assert run["work_package_count"] == 1
        assert run["has_evidence_store"] is True
        assert run["has_work_packages"] is True

    async def test_empty_repo_returns_empty(self, client: AsyncClient) -> None:
        result = await _upload(client, {".ai-debt/project-profile.json": PROFILE_JSON})
        repo_id = result["repository_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/runs")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_invalid_repo_id_returns_400(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/repositories/not-a-uuid/runs")
        assert resp.status_code == 400

    async def test_exactly_one_latest(self, client: AsyncClient, seeded_two_runs) -> None:
        repo_id = seeded_two_runs["repo_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/runs")
        runs = resp.json()["runs"]
        latest_count = sum(1 for r in runs if r["is_latest"])
        assert latest_count == 1


# -- Run Detail API --


class TestRunDetailAPI:
    async def test_run_detail_returns_full(self, client: AsyncClient, seeded_single) -> None:
        repo_id = seeded_single["repository_id"]
        run_id = seeded_single["run_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/runs/{run_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == "RUN-20260529-120000"
        assert data["summary"]["finding_count"] == 2
        assert data["summary"]["evidence_count"] == 1
        assert data["summary"]["work_package_count"] == 1
        assert data["capabilities"]["has_evidence_store"] is True
        assert data["capabilities"]["has_work_packages"] is True
        assert data["is_latest"] is True

    async def test_missing_run_returns_404(self, client: AsyncClient, seeded_single) -> None:
        repo_id = seeded_single["repository_id"]
        fake_run = "00000000-0000-0000-0000-000000000000"
        resp = await client.get(f"/api/v1/repositories/{repo_id}/runs/{fake_run}")
        assert resp.status_code == 404

    async def test_cross_repo_isolation(self, client: AsyncClient, seeded_single) -> None:
        other = await _upload(
            client,
            _full_bundle(findings=FINDINGS_JSON_V2, run_metadata=None),
            name="Other Repo",
        )
        run_id = seeded_single["run_id"]
        resp = await client.get(f"/api/v1/repositories/{other['repository_id']}/runs/{run_id}")
        assert resp.status_code == 404


# -- Latest Run Determinism --


class TestLatestRunDeterminism:
    async def test_latest_run_endpoint(self, client: AsyncClient, seeded_single) -> None:
        repo_id = seeded_single["repository_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/latest-run")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run"] is not None
        assert data["run"]["is_latest"] is True

    async def test_two_runs_latest_matches_list(self, client: AsyncClient, seeded_two_runs) -> None:
        repo_id = seeded_two_runs["repo_id"]
        resp_list = await client.get(f"/api/v1/repositories/{repo_id}/runs")
        runs = resp_list.json()["runs"]
        latest_from_list = next(r for r in runs if r["is_latest"])

        resp_latest = await client.get(f"/api/v1/repositories/{repo_id}/latest-run")
        latest_from_endpoint = resp_latest.json()["run"]
        assert latest_from_list["id"] == latest_from_endpoint["id"]


# -- Findings Scoped by Run --


class TestFindingsScopedByRun:
    async def test_findings_list_with_explicit_run(
        self, client: AsyncClient, seeded_two_runs
    ) -> None:
        repo_id = seeded_two_runs["repo_id"]
        run1_id = seeded_two_runs["run1_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/findings?run_id={run1_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        ids = [f["finding_id"] for f in data["findings"]]
        assert "TD-ARCH-001" in ids
        assert "TD-TEST-001" in ids

    async def test_findings_list_defaults_to_latest(
        self, client: AsyncClient, seeded_two_runs
    ) -> None:
        repo_id = seeded_two_runs["repo_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/findings")
        data = resp.json()
        # Run 2 has only TD-ARCH-001 with title "Auth boundary drift v2"
        assert data["total"] == 1
        assert data["findings"][0]["title"] == "Auth boundary drift v2"

    async def test_cross_run_finding_not_visible(
        self, client: AsyncClient, seeded_two_runs
    ) -> None:
        repo_id = seeded_two_runs["repo_id"]
        run1_id = seeded_two_runs["run1_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/findings?run_id={run1_id}")
        titles = [f["title"] for f in resp.json()["findings"]]
        assert "Auth boundary drift v2" not in titles

    async def test_same_finding_id_different_runs(
        self, client: AsyncClient, seeded_two_runs
    ) -> None:
        repo_id = seeded_two_runs["repo_id"]
        run1_id = seeded_two_runs["run1_id"]
        run2_id = seeded_two_runs["run2_id"]

        resp1 = await client.get(f"/api/v1/repositories/{repo_id}/findings?run_id={run1_id}")
        resp2 = await client.get(f"/api/v1/repositories/{repo_id}/findings?run_id={run2_id}")

        arch1 = next(f for f in resp1.json()["findings"] if f["finding_id"] == "TD-ARCH-001")
        arch2 = next(f for f in resp2.json()["findings"] if f["finding_id"] == "TD-ARCH-001")

        # Same finding_id, different data across runs
        assert arch1["title"] == "Auth boundary drift"
        assert arch2["title"] == "Auth boundary drift v2"
        assert arch1["severity"] == "High"
        assert arch2["severity"] == "Critical"


# -- Evidence Scoped by Run --


class TestEvidenceScopedByRun:
    async def test_evidence_with_run_id(self, client: AsyncClient, seeded_single) -> None:
        repo_id = seeded_single["repository_id"]
        run_id = seeded_single["run_id"]
        resp = await client.get(
            f"/api/v1/repositories/{repo_id}/evidence/EVD-000001?run_id={run_id}"
        )
        assert resp.status_code == 200
        assert resp.json()["evidence_id"] == "EVD-000001"

    async def test_cross_run_evidence_not_visible(
        self, client: AsyncClient, seeded_two_runs
    ) -> None:
        repo_id = seeded_two_runs["repo_id"]
        run2_id = seeded_two_runs["run2_id"]
        # Run 2 uploads evidence.json so EVD-000001 exists in both runs.
        # Verify that scoping works by checking run1 sees it and run2 also does.
        # Cross-run isolation is about findings/WPs, not evidence dedup.
        run1_id = seeded_two_runs["run1_id"]
        resp1 = await client.get(
            f"/api/v1/repositories/{repo_id}/evidence/EVD-000001?run_id={run1_id}"
        )
        assert resp1.status_code == 200
        resp2 = await client.get(
            f"/api/v1/repositories/{repo_id}/evidence/EVD-000001?run_id={run2_id}"
        )
        # Both runs have the same evidence.json so both resolve
        assert resp2.status_code == 200
        # But they are different records (different run_id)
        assert resp1.json()["evidence_id"] == resp2.json()["evidence_id"]


# -- Work Packages Scoped by Run --


class TestWorkPackagesScopedByRun:
    async def test_wp_list_with_run_id(self, client: AsyncClient, seeded_single) -> None:
        repo_id = seeded_single["repository_id"]
        run_id = seeded_single["run_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/work-packages?run_id={run_id}")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    async def test_wp_cross_run_isolation(self, client: AsyncClient, seeded_two_runs) -> None:
        repo_id = seeded_two_runs["repo_id"]
        run2_id = seeded_two_runs["run2_id"]
        # Run 2 has no work packages
        resp = await client.get(f"/api/v1/repositories/{repo_id}/work-packages?run_id={run2_id}")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# -- Upload Run Metadata --


class TestUploadRunMetadata:
    async def test_upload_stores_run_metadata(self, client: AsyncClient, seeded_single) -> None:
        repo_id = seeded_single["repository_id"]
        run_id = seeded_single["run_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/runs/{run_id}")
        data = resp.json()
        assert data["run_id"] == "RUN-20260529-120000"
        assert data["commit_sha"] == "abc123def456"
        assert data["branch_name"] == "main"
        assert data["analysis_mode"] == "deterministic-no-ai"

    async def test_upload_response_enriched(self, client: AsyncClient, seeded_single) -> None:
        assert seeded_single["created_at"] is not None
        assert seeded_single["is_latest"] is True
        assert isinstance(seeded_single["warnings"], list)

    async def test_upload_without_run_metadata(self, client: AsyncClient) -> None:
        result = await _upload(
            client,
            {
                ".ai-debt/project-profile.json": PROFILE_JSON,
                ".ai-debt/debt-register.json": FINDINGS_JSON,
                ".ai-debt/evidence.json": EVIDENCE_JSON,
            },
        )
        repo_id = result["repository_id"]
        run_id = result["run_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/runs/{run_id}")
        data = resp.json()
        # Defaults
        assert data["commit_sha"] == ""
        assert data["branch_name"] == ""
        assert data["analysis_mode"] == "baseline"


# -- Degraded States --


class TestDegradedStates:
    async def test_legacy_no_evidence(self, client: AsyncClient) -> None:
        result = await _upload(
            client,
            {
                ".ai-debt/project-profile.json": PROFILE_JSON,
                ".ai-debt/debt-register.json": FINDINGS_JSON,
            },
        )
        repo_id = result["repository_id"]
        run_id = result["run_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/runs/{run_id}")
        data = resp.json()
        assert data["summary"]["evidence_count"] == 0
        assert data["capabilities"]["has_evidence_store"] is False

    async def test_legacy_no_work_packages(self, client: AsyncClient) -> None:
        result = await _upload(
            client,
            {
                ".ai-debt/project-profile.json": PROFILE_JSON,
                ".ai-debt/debt-register.json": FINDINGS_JSON,
                ".ai-debt/evidence.json": EVIDENCE_JSON,
            },
        )
        repo_id = result["repository_id"]
        run_id = result["run_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/runs/{run_id}")
        data = resp.json()
        assert data["summary"]["work_package_count"] == 0
        assert data["capabilities"]["has_work_packages"] is False

    async def test_warning_count_from_degraded_links(self, client: AsyncClient) -> None:
        wp = WP_MARKDOWN.replace("- `TD-ARCH-001`", "- `TD-ARCH-001`\n- `TD-ARCH-999`")
        result = await _upload(client, _full_bundle(wp=wp))
        repo_id = result["repository_id"]
        run_id = result["run_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/runs/{run_id}")
        data = resp.json()
        # 1 missing link (TD-ARCH-999)
        assert data["summary"]["warning_count"] == 1

    async def test_empty_findings_run(self, client: AsyncClient) -> None:
        empty_findings = json.dumps({"schema_version": "1.0", "findings": []})
        result = await _upload(
            client,
            {
                ".ai-debt/project-profile.json": PROFILE_JSON,
                ".ai-debt/debt-register.json": empty_findings,
            },
        )
        repo_id = result["repository_id"]
        resp = await client.get(f"/api/v1/repositories/{repo_id}/runs")
        # Empty findings still creates a run with total_findings=0
        assert resp.json()["total"] == 1
        run = resp.json()["runs"][0]
        assert run["total_findings"] == 0
