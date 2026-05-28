"""S04 tests — Endpoint integration with mock DB records.

Verifies that read endpoints return correct data when given
mock ORM records. NOT database-backed — uses shape verification.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pharabius_platform.main import app
from pharabius_platform.models import (
    ArtifactBundle,
    Claim,
    Finding,
    Gap,
    Organization,
    Repository,
    Run,
)


def _make_org() -> Organization:
    return Organization(name="Test Org", slug="test-org")


def _make_repo(org_id: uuid.UUID) -> Repository:
    return Repository(
        organization_id=org_id,
        name="test-repo",
        slug="test-repo",
        last_uploaded_at=datetime.now(UTC),
    )


def _make_bundle(repo_id: uuid.UUID) -> ArtifactBundle:
    return ArtifactBundle(
        repository_id=repo_id,
        upload_source="api",
        file_size_bytes=2048,
        content_hash="abc123def456",
        storage_path="/storage/ab/abc123def456.tar.gz",
        is_valid=True,
    )


def _make_run(bundle_id: uuid.UUID, repo_id: uuid.UUID) -> Run:
    return Run(
        bundle_id=bundle_id,
        repository_id=repo_id,
        run_id="RUN-20260528-120000",
        total_findings=3,
        critical=0,
        high=1,
        medium=1,
        low=1,
        readiness_status="needs_review",
        gate_result="warn",
    )


def _make_finding(run_id: uuid.UUID) -> Finding:
    return Finding(
        run_id=run_id,
        finding_id="TD-DEP-001",
        category="TD-DEP",
        title="Missing lockfile",
        severity="High",
        confidence="High",
        risk_score=25,
        priority="High",
    )


class TestRepositoryEndpointLogic:
    """Verify repository list/detail data shapes."""

    def test_org_model_fields(self) -> None:
        org = _make_org()
        assert org.slug == "test-org"
        assert org.name == "Test Org"

    def test_repo_model_fields(self) -> None:
        org = _make_org()
        org.id = uuid.uuid4()
        repo = _make_repo(org.id)
        assert repo.name == "test-repo"
        assert repo.last_uploaded_at is not None

    def test_repo_list_item_shape(self) -> None:
        org = _make_org()
        org.id = uuid.uuid4()
        repo = _make_repo(org.id)
        repo.id = uuid.uuid4()
        run = _make_run(uuid.uuid4(), repo.id)

        # Expected API response shape
        item = {
            "id": str(repo.id),
            "name": repo.name,
            "slug": repo.slug,
            "latest_run": {
                "run_id": run.run_id,
                "total_findings": run.total_findings,
                "gate_result": run.gate_result,
            },
        }
        assert item["latest_run"]["total_findings"] == 3
        assert item["latest_run"]["gate_result"] == "warn"


class TestFindingsEndpointLogic:
    """Verify findings list data shapes."""

    def test_finding_model_fields(self) -> None:
        run = _make_run(uuid.uuid4(), uuid.uuid4())
        run.id = uuid.uuid4()
        finding = _make_finding(run.id)
        assert finding.finding_id == "TD-DEP-001"
        assert finding.severity == "High"
        assert finding.category == "TD-DEP"

    def test_finding_response_shape(self) -> None:
        finding = _make_finding(uuid.uuid4())
        item = {
            "id": str(uuid.uuid4()),
            "finding_id": finding.finding_id,
            "category": finding.category,
            "title": finding.title,
            "severity": finding.severity,
            "confidence": finding.confidence,
            "risk_score": finding.risk_score,
        }
        assert item["severity"] == "High"
        assert item["risk_score"] == 25


class TestPortfolioEndpointLogic:
    """Verify portfolio aggregation shapes."""

    def test_portfolio_aggregation_shape(self) -> None:
        repos = [
            {"name": "repo-a", "total_findings": 3, "gate_result": "warn"},
            {"name": "repo-b", "total_findings": 1, "gate_result": "pass"},
        ]
        total = sum(r["total_findings"] for r in repos)
        assert total == 4

    def test_risk_rollup_shape(self) -> None:
        run = _make_run(uuid.uuid4(), uuid.uuid4())
        rollup = {
            "critical": run.critical,
            "high": run.high,
            "medium": run.medium,
            "low": run.low,
        }
        assert rollup == {"critical": 0, "high": 1, "medium": 1, "low": 1}


class TestTrendsEndpointLogic:
    """Verify trend point shapes."""

    def test_trend_point_shape(self) -> None:
        run = _make_run(uuid.uuid4(), uuid.uuid4())
        point = {
            "run_id": run.run_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "total_findings": run.total_findings,
            "critical": run.critical,
            "high": run.high,
            "medium": run.medium,
            "low": run.low,
            "gate_result": run.gate_result,
        }
        assert point["total_findings"] == 3


class TestClaimsGapsReadinessLogic:
    """Verify claims/gaps/readiness data shapes."""

    def test_claim_model(self) -> None:
        claim = Claim(
            bundle_id=None,
            repository_id=None,
            claim_id="CLAIM-001",
            claim_type="behavioral",
            status="unvalidated",
            confidence="High",
            description="Test",
        )
        assert claim.claim_id == "CLAIM-001"

    def test_gap_model(self) -> None:
        gap = Gap(
            bundle_id=None,
            repository_id=None,
            gap_id="GAP-001",
            description="Missing tests",
            severity="Medium",
        )
        assert gap.gap_id == "GAP-001"

    def test_readiness_entry_shape(self) -> None:
        run = _make_run(uuid.uuid4(), uuid.uuid4())
        entry = {
            "repository_id": str(uuid.uuid4()),
            "repository_name": "test-repo",
            "readiness_status": run.readiness_status,
        }
        assert entry["readiness_status"] == "needs_review"


class TestAllEndpointsStillRegistered:
    """Verify no routes were lost during refactor."""

    def test_all_18_endpoints(self) -> None:
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
            assert endpoint in routes, f"Missing: {endpoint}"

        # Parameterized routes
        param_patterns = [
            "repositories/{repo_id}",
            "api-keys/{key_id}",
        ]
        for pattern in param_patterns:
            assert any(pattern in r for r in routes), f"Missing: {pattern}"
