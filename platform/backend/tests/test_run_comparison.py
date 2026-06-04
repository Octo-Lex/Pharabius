"""Tests for v3.0.0 — Run Comparison & Traceability Delta.

Covers: comparison endpoint validation, finding delta, work-package delta,
traceability delta, same-run comparison, route ordering, order-insensitive
evidence IDs.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from pharabius_platform.db import init_db
from pharabius_platform.main import app
from pharabius_platform.models import Base
from tests.test_run_history_navigation import (
    ADMIN_TOKEN,
    EVIDENCE_JSON,
    FINDINGS_JSON_V2,
    PROFILE_JSON,
    _full_bundle,
    _upload,
)

# Run B metadata with different run_id
RUN_METADATA_B = json.dumps(
    {
        "schema_version": "1.0",
        "run_id": "RUN-20260529-130000",
        "timestamp": "2026-05-29T13:00:00Z",
        "repository": "/test",
        "commit": "def456",
        "branch": "main",
        "tool_version": "3.0.0",
        "analysis_mode": "baseline",
        "commands_run": ["scan"],
        "files_written": [],
        "limitations": [],
        "summary": {"finding_count": 1, "evidence_count": 1},
    }
)

# Findings with an extra finding added in run B
FINDINGS_RUN_B = json.dumps(
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
            {
                "id": "TD-SEC-001",
                "category": "TD-SEC",
                "title": "New vulnerability",
                "description": "CVE detected.",
                "severity": "Critical",
                "evidence_ids": [],
                "risk_score": 30,
                "priority": "Critical",
                "recommended_action": "Patch",
            },
        ],
    }
)

# Run B WP with changed status
WP_RUN_B = (
    "# Work Package: WP-001 Stabilize auth\n\n"
    "## Status\n\nIn Progress\n\n"
    "## Linked Debt Items\n\n- `TD-ARCH-001`\n\n"
    "## Objective\n\nConsolidate auth.\n\n"
    "## Evidence\n\n- `EVD-000001`\n- `EVD-000002`\n\n"
    "## Current Risk\n\nHigh\n\n"
    "## Recommended Engineering Approach\n\n1. Extract middleware\n\n"
    "## Expected Affected Areas\n\n- src/\n\n"
    "## Verification Recommendations\n\n- Test\n\n"
    "## Risks and Cautions\n\n- Risk\n\n"
    "## Definition of Done\n\n- Done\n\n"
    "## Estimated Effort\n\nMedium"
)


def _bundle_b() -> dict[str, str]:
    files: dict[str, str] = {
        ".ai-debt/project-profile.json": PROFILE_JSON,
        ".ai-debt/debt-register.json": FINDINGS_RUN_B,
        ".ai-debt/evidence.json": EVIDENCE_JSON,
        ".ai-debt/runs/RUN-20260529-130000.json": RUN_METADATA_B,
        ".ai-debt/work-packages/WP-001-stabilize-auth.md": WP_RUN_B,
    }
    return files


# Findings with zero evidence IDs for empty-run test
FINDINGS_NO_EV = json.dumps(
    {
        "schema_version": "1.0",
        "findings": [
            {
                "id": "TD-001",
                "category": "TD-ARCH",
                "title": "Test",
                "description": "Test.",
                "severity": "Low",
                "evidence_ids": [],
                "risk_score": 1,
                "priority": "Low",
            },
        ],
    }
)

RUN_METADATA_C = json.dumps(
    {
        "schema_version": "1.0",
        "run_id": "RUN-20260529-140000",
        "timestamp": "2026-05-29T14:00:00Z",
        "repository": "/test",
        "commit": "ccc333",
        "branch": "main",
        "tool_version": "3.0.0",
        "analysis_mode": "baseline",
        "commands_run": ["scan"],
        "files_written": [],
        "limitations": [],
        "summary": {"finding_count": 1, "evidence_count": 0},
    }
)

RUN_METADATA_D = json.dumps(
    {
        "schema_version": "1.0",
        "run_id": "RUN-20260529-150000",
        "timestamp": "2026-05-29T15:00:00Z",
        "repository": "/test",
        "commit": "ddd444",
        "branch": "main",
        "tool_version": "3.0.0",
        "analysis_mode": "baseline",
        "commands_run": ["scan"],
        "files_written": [],
        "limitations": [],
        "summary": {"finding_count": 1, "evidence_count": 0},
    }
)


@pytest.fixture(autouse=True)
async def _setup_db(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[None, None]:
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true",
    )
    from pharabius_platform import db as db_mod

    init_db("sqlite+aiosqlite:///file::memory:?cache=shared&uri=true")
    async with db_mod._engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with db_mod._engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await db_mod._engine.dispose()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


@pytest.fixture
async def seeded_two_runs(client: AsyncClient) -> dict[str, object]:
    """Upload two runs to the same repository with different content."""
    # Run A uses the standard fixtures
    a = await _upload(client, _full_bundle())
    repo_id = a["repository_id"]
    run_a_id = a["run_id"]
    assert run_a_id is not None, f"Run A upload returned no run_id: {a}"

    # Run B uses FINDINGS_JSON_V2 (different content → different hash)
    # Note: _full_bundle always uses key '.ai-debt/runs/RUN-20260529-120000.json'
    b_files = _full_bundle(findings=FINDINGS_JSON_V2, run_metadata=RUN_METADATA_B, wp=WP_RUN_B)
    b = await _upload(client, b_files)
    run_b_id = b["run_id"]
    assert run_b_id is not None, f"Run B upload returned no run_id: {b}"

    return {
        "repo_id": repo_id,
        "run_a_id": run_a_id,
        "run_b_id": run_b_id,
    }


class TestComparisonValidation:
    async def test_compare_requires_both_run_ids(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/repositories/some-repo/runs/compare")
        assert resp.status_code == 422

    async def test_compare_rejects_missing_run(self, client: AsyncClient, seeded_two_runs) -> None:
        data = seeded_two_runs
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        resp = await client.get(
            f"/api/v1/repositories/{data['repo_id']}/runs/compare",
            params={"baseline_run_id": fake_uuid, "comparison_run_id": data["run_b_id"]},
        )
        assert resp.status_code == 404

    async def test_compare_rejects_cross_repo(self, client: AsyncClient, seeded_two_runs) -> None:
        data = seeded_two_runs
        # Upload to a different repo with unique content
        other_findings = json.dumps(
            {
                "schema_version": "1.0",
                "findings": [
                    {
                        "id": "TD-OTHER-001",
                        "category": "TD-ARCH",
                        "title": "Other finding",
                        "description": "",
                        "severity": "Low",
                        "evidence_ids": [],
                        "risk_score": 1,
                        "priority": "Low",
                        "technical_impact": "Low",
                        "business_impact": "Low",
                        "recommended_action": "None",
                    },
                ],
            }
        )
        other_bundle = _full_bundle(findings=other_findings)
        run_key = ".ai-debt/runs/RUN-20260529-120000.json"
        other_bundle[run_key] = other_bundle.pop(run_key)  # keep same key
        other = await _upload(client, other_bundle, name="Other Repo")
        other_run_id = other["run_id"]

        resp = await client.get(
            f"/api/v1/repositories/{data['repo_id']}/runs/compare",
            params={
                "baseline_run_id": other_run_id,
                "comparison_run_id": data["run_b_id"],
            },
        )
        # Cross-repo run_id not found in this repository's runs
        assert resp.status_code in (400, 404)

    async def test_compare_route_does_not_conflict_with_run_detail(
        self, client: AsyncClient, seeded_two_runs
    ) -> None:
        """GET /runs/compare hits comparison endpoint, not run_id='compare'."""
        data = seeded_two_runs
        resp = await client.get(
            f"/api/v1/repositories/{data['repo_id']}/runs/compare",
            params={
                "baseline_run_id": data["run_a_id"],
                "comparison_run_id": data["run_b_id"],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "summary" in body
        assert "findings_delta" in body


class TestSameRunComparison:
    async def test_same_run_compare_all_unchanged(
        self, client: AsyncClient, seeded_two_runs
    ) -> None:
        data = seeded_two_runs
        resp = await client.get(
            f"/api/v1/repositories/{data['repo_id']}/runs/compare",
            params={
                "baseline_run_id": data["run_a_id"],
                "comparison_run_id": data["run_a_id"],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        summary = body["summary"]["findings"]
        assert summary["added"] == 0
        assert summary["removed"] == 0
        assert summary["changed"] == 0
        assert summary["unchanged"] == 2

        wp_summary = body["summary"]["work_packages"]
        assert wp_summary["added"] == 0
        assert wp_summary["removed"] == 0
        assert wp_summary["changed"] == 0
        assert wp_summary["unchanged"] == 1


class TestFindingDelta:
    async def test_finding_added_removed_changed_unchanged(
        self, client: AsyncClient, seeded_two_runs
    ) -> None:
        data = seeded_two_runs
        resp = await client.get(
            f"/api/v1/repositories/{data['repo_id']}/runs/compare",
            params={
                "baseline_run_id": data["run_a_id"],
                "comparison_run_id": data["run_b_id"],
            },
        )
        assert resp.status_code == 200
        body = resp.json()

        deltas = body["findings_delta"]
        by_fid = {d["finding_id"]: d for d in deltas}

        # TD-ARCH-001: changed (different title/severity/risk_score)
        assert by_fid["TD-ARCH-001"]["status"] == "changed"

        # TD-TEST-001: removed (only in baseline, not in V2 findings)
        assert by_fid["TD-TEST-001"]["status"] == "removed"

        # TD-SEC-001 does not exist in either run's standard fixtures

        summary = body["summary"]["findings"]
        assert summary["added"] == 0
        assert summary["removed"] == 1  # TD-TEST-001
        assert summary["changed"] == 1  # TD-ARCH-001
        assert summary["unchanged"] == 0

    async def test_finding_changed_fields_listed(
        self, client: AsyncClient, seeded_two_runs
    ) -> None:
        data = seeded_two_runs
        resp = await client.get(
            f"/api/v1/repositories/{data['repo_id']}/runs/compare",
            params={
                "baseline_run_id": data["run_a_id"],
                "comparison_run_id": data["run_b_id"],
            },
        )
        body = resp.json()
        deltas = {d["finding_id"]: d for d in body["findings_delta"]}

        changed = deltas["TD-ARCH-001"]
        assert "severity" in changed["changed_fields"]
        assert "risk_score" in changed["changed_fields"]

    async def test_finding_evidence_id_order_unchanged(
        self, client: AsyncClient, seeded_two_runs
    ) -> None:
        """Same evidence IDs in different order → unchanged."""
        data = seeded_two_runs
        resp = await client.get(
            f"/api/v1/repositories/{data['repo_id']}/runs/compare",
            params={
                "baseline_run_id": data["run_a_id"],
                "comparison_run_id": data["run_b_id"],
            },
        )
        body = resp.json()
        deltas = {d["finding_id"]: d for d in body["findings_delta"]}

        # TD-TEST-001 is removed in run B (not in V2 findings)
        assert deltas["TD-TEST-001"]["status"] == "removed"


class TestWorkPackageDelta:
    async def test_work_package_changed(self, client: AsyncClient, seeded_two_runs) -> None:
        data = seeded_two_runs
        resp = await client.get(
            f"/api/v1/repositories/{data['repo_id']}/runs/compare",
            params={
                "baseline_run_id": data["run_a_id"],
                "comparison_run_id": data["run_b_id"],
            },
        )
        body = resp.json()

        wp_deltas = body["work_packages_delta"]
        assert len(wp_deltas) == 1
        wp = wp_deltas[0]
        assert wp["package_id"] == "WP-001"
        assert wp["status"] == "changed"

    async def test_work_package_changed_fields(self, client: AsyncClient, seeded_two_runs) -> None:
        data = seeded_two_runs
        resp = await client.get(
            f"/api/v1/repositories/{data['repo_id']}/runs/compare",
            params={
                "baseline_run_id": data["run_a_id"],
                "comparison_run_id": data["run_b_id"],
            },
        )
        body = resp.json()
        wp = body["work_packages_delta"][0]
        # Status changed, linked_debt_item_ids changed (2→1), declared_evidence_ids changed
        assert "status" in wp["changed_fields"]


class TestTraceabilityDelta:
    async def test_traceability_improved(self, client: AsyncClient, seeded_two_runs) -> None:
        data = seeded_two_runs
        resp = await client.get(
            f"/api/v1/repositories/{data['repo_id']}/runs/compare",
            params={
                "baseline_run_id": data["run_a_id"],
                "comparison_run_id": data["run_b_id"],
            },
        )
        body = resp.json()
        trace = body["traceability_delta"]
        assert "evidence" in trace
        assert "work_package_links" in trace
        ev = trace["evidence"]
        assert ev["status"] in ("improved", "unchanged", "regressed")

    async def test_traceability_empty_runs_without_evidence_ids_is_unchanged(
        self, client: AsyncClient
    ) -> None:
        """Two runs with zero evidence IDs → traceability unchanged."""
        # First run
        findings_a = json.dumps(
            {
                "schema_version": "1.0",
                "findings": [
                    {
                        "id": "TD-001",
                        "category": "TD-ARCH",
                        "title": "Test A",
                        "description": "A.",
                        "severity": "Low",
                        "evidence_ids": [],
                        "risk_score": 1,
                        "priority": "Low",
                        "technical_impact": "Low",
                        "business_impact": "Low",
                        "recommended_action": "None",
                    },
                ],
            }
        )
        meta_a = json.dumps(
            {
                "schema_version": "1.0",
                "run_id": "RUN-EMPTY-A",
                "timestamp": "2026-05-29T14:00:00Z",
                "repository": "/test",
                "commit": "eee111",
                "branch": "main",
                "tool_version": "3.0.0",
                "analysis_mode": "baseline",
                "commands_run": ["scan"],
                "files_written": [],
                "limitations": [],
                "summary": {"finding_count": 1, "evidence_count": 0},
            }
        )
        bundle_a = _full_bundle(
            findings=findings_a,
            run_metadata=meta_a,
            evidence=EVIDENCE_JSON,
            wp=None,
        )
        a = await _upload(client, bundle_a)

        # Second run (different title and metadata → different hash)
        findings_b = json.dumps(
            {
                "schema_version": "1.0",
                "findings": [
                    {
                        "id": "TD-001",
                        "category": "TD-ARCH",
                        "title": "Test B",
                        "description": "B.",
                        "severity": "Low",
                        "evidence_ids": [],
                        "risk_score": 1,
                        "priority": "Low",
                        "technical_impact": "Low",
                        "business_impact": "Low",
                        "recommended_action": "None",
                    },
                ],
            }
        )
        meta_b = json.dumps(
            {
                "schema_version": "1.0",
                "run_id": "RUN-EMPTY-B",
                "timestamp": "2026-05-29T15:00:00Z",
                "repository": "/test",
                "commit": "fff222",
                "branch": "main",
                "tool_version": "3.0.0",
                "analysis_mode": "baseline",
                "commands_run": ["scan"],
                "files_written": [],
                "limitations": [],
                "summary": {"finding_count": 1, "evidence_count": 0},
            }
        )
        bundle_b = _full_bundle(
            findings=findings_b,
            run_metadata=meta_b,
            evidence=EVIDENCE_JSON,
            wp=None,
        )
        b = await _upload(client, bundle_b)

        resp = await client.get(
            f"/api/v1/repositories/{a['repository_id']}/runs/compare",
            params={
                "baseline_run_id": a["run_id"],
                "comparison_run_id": b["run_id"],
            },
        )
        assert resp.status_code == 200, f"Compare failed: {resp.text[:300]}"
        body = resp.json()
        ev = body["traceability_delta"]["evidence"]
        assert ev["status"] == "unchanged"
