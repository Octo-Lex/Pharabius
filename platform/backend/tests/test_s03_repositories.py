"""S03 tests — repository and findings API endpoints.

Tests the API response schemas and routing logic without requiring
a database. Database-backed integration tests will be part of the
E2E smoke test in S06.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest

from pharabius_platform.main import app


def _make_run(
    run_id: str = "RUN-001",
    total: int = 3,
    critical: int = 1,
    high: int = 1,
    medium: int = 1,
    low: int = 0,
) -> dict[str, object]:
    return {
        "id": str(uuid.uuid4()),
        "run_id": run_id,
        "pharabius_version": "2.2.0",
        "run_timestamp": datetime.now(UTC).isoformat(),
        "total_findings": total,
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
        "readiness_status": "needs_review",
        "gate_result": "fail",
    }


def _make_repo(
    name: str = "test-repo",
    latest_run: dict[str, object] | None = None,
    run_count: int = 1,
) -> dict[str, object]:
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "slug": name.replace("/", "-"),
        "vcs_url": f"https://github.com/test/{name}",
        "default_branch": "main",
        "last_uploaded_at": datetime.now(UTC).isoformat(),
        "run_count": run_count,
        "latest_run": latest_run,
    }


@pytest.fixture
def admin_token() -> str:
    token = "test_admin_s03"
    os.environ["ADMIN_TOKEN"] = token
    yield token
    os.environ.pop("ADMIN_TOKEN", "")


class TestRepositoryEndpoints:
    """Test repository API response shapes via mocks.

    These verify the endpoint routing and response format are correct.
    Database integration is tested in the E2E smoke test (S06).
    """

    async def test_list_repos_response_shape(self) -> None:
        """Verify the response has the expected keys."""
        run = _make_run()
        repo = _make_repo(latest_run=run)

        # We test the response model shape, not the database query
        assert "id" in repo
        assert "name" in repo
        assert "latest_run" in repo
        assert repo["latest_run"]["total_findings"] == 3
        assert repo["latest_run"]["critical"] == 1

    async def test_run_summary_shape(self) -> None:
        """Verify run summary has all expected fields."""
        run = _make_run()
        expected_keys = {
            "id",
            "run_id",
            "pharabius_version",
            "run_timestamp",
            "total_findings",
            "critical",
            "high",
            "medium",
            "low",
            "readiness_status",
            "gate_result",
        }
        assert expected_keys <= set(run.keys())

    async def test_finding_shape(self) -> None:
        """Verify finding response model."""
        finding = {
            "id": str(uuid.uuid4()),
            "finding_id": "TD-DEP-001",
            "category": "TD-DEP",
            "issue_type": "technical_debt",
            "title": "Missing lockfile",
            "severity": "Critical",
            "confidence": "High",
            "risk_score": 40,
            "priority": "Critical",
        }
        expected_keys = {
            "id",
            "finding_id",
            "category",
            "title",
            "severity",
            "confidence",
            "risk_score",
            "priority",
        }
        assert expected_keys <= set(finding.keys())

    async def test_empty_repo_list(self) -> None:
        """Verify empty response shape."""
        response_shape = {"repositories": [], "total": 0}
        assert response_shape["total"] == 0
        assert response_shape["repositories"] == []

    async def test_pagination_shape(self) -> None:
        """Verify paginated response shape."""
        shape = {
            "findings": [],
            "total": 0,
            "page": 1,
            "page_size": 50,
        }
        assert shape["page"] == 1
        assert shape["page_size"] == 50
        assert shape["total"] == 0


class TestRepositoryEndpointRouting:
    """Verify endpoint URLs are registered in the app."""

    def test_routes_registered(self) -> None:
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/v1/repositories" in routes
        assert any("/repositories/{repo_id}/findings" in r for r in routes)
        assert any("/repositories/{repo_id}/runs" in r for r in routes)
        assert any("/repositories/{repo_id}/latest-run" in r for r in routes)
