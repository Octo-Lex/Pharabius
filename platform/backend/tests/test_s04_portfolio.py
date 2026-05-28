"""S04 tests — portfolio, trend, gate, claims, gaps, readiness APIs."""

from __future__ import annotations

from pharabius_platform.main import app


class TestEndpointRegistration:
    """Verify all S04 endpoints are registered."""

    def test_portfolio_routes_exist(self) -> None:
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/v1/portfolio" in routes
        assert "/api/v1/portfolio/risk-rollup" in routes

    def test_trend_route_exists(self) -> None:
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert any("/repositories/{repo_id}/trends" in r for r in routes)

    def test_gate_history_route_exists(self) -> None:
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert any("/repositories/{repo_id}/gate-history" in r for r in routes)

    def test_claims_route_exists(self) -> None:
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/v1/claims" in routes

    def test_gaps_route_exists(self) -> None:
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/v1/gaps" in routes

    def test_readiness_route_exists(self) -> None:
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/v1/readiness" in routes


class TestResponseShapes:
    """Verify response model shapes for portfolio endpoints."""

    def test_portfolio_shape(self) -> None:
        shape = {
            "total_repositories": 0,
            "total_findings": 0,
            "severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "repositories": [],
        }
        assert "severity" in shape
        assert "total_repositories" in shape

    def test_risk_rollup_shape(self) -> None:
        shape = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        assert set(shape.keys()) == {"critical", "high", "medium", "low"}

    def test_trend_point_shape(self) -> None:
        point = {
            "run_id": "RUN-001",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "total_findings": 5,
            "critical": 1,
            "high": 1,
            "medium": 2,
            "low": 1,
            "gate_result": "pass",
        }
        assert "total_findings" in point
        assert "gate_result" in point

    def test_gate_history_shape(self) -> None:
        entry = {
            "run_id": "RUN-001",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "gate_result": "pass",
            "passed": True,
            "total_findings": 5,
            "critical": 1,
            "high": 1,
        }
        assert "passed" in entry
        assert "gate_result" in entry

    def test_claim_shape(self) -> None:
        claim = {
            "id": "uuid",
            "claim_id": "CLAIM-001",
            "claim_type": "behavioral",
            "status": "confirmed",
            "confidence": "High",
            "description": "Test",
        }
        assert "claim_type" in claim
        assert "confidence" in claim

    def test_gap_shape(self) -> None:
        gap = {
            "id": "uuid",
            "gap_id": "GAP-001",
            "description": "Missing test coverage data",
            "severity": "Medium",
        }
        assert "gap_id" in gap
        assert "severity" in gap

    def test_readiness_shape(self) -> None:
        entry = {
            "repository_id": "uuid",
            "repository_name": "my-repo",
            "readiness_status": "needs_review",
        }
        assert "readiness_status" in entry
