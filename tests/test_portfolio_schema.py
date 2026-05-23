"""Tests for portfolio summary schemas and helpers (W45-S01)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pharabius.core.portfolio import (
    render_portfolio_markdown,
    write_portfolio_json,
    write_portfolio_markdown,
    write_repository_index,
)
from pharabius.schemas.portfolio import (
    PortfolioCategoryRollup,
    PortfolioReadinessRollup,
    PortfolioRepositoryEntry,
    PortfolioRiskRollup,
    PortfolioSummary,
)


def _make_summary() -> PortfolioSummary:
    return PortfolioSummary(
        schema_version="1.0",
        tool_version="1.8.0",
        generated_at="2026-05-24T00:00:00Z",
        portfolio_id="portfolio-test",
        repositories=[
            PortfolioRepositoryEntry(
                repository_id="repo-1",
                project_name="alpha",
                repository_path="/repos/alpha",
                branch="main",
                commit="abc123",
                total_findings=5,
                priority_counts={"High": 2, "Low": 3},
                top_categories=["TD-ARCH", "TD-DEP"],
                highest_priority="High",
                has_ticket_drafts=True,
                has_export_bundles=False,
                validation_status="complete",
            ),
            PortfolioRepositoryEntry(
                repository_id="repo-2",
                project_name="beta",
                repository_path="/repos/beta",
                total_findings=0,
                validation_status="complete",
            ),
        ],
        risk_rollup=PortfolioRiskRollup(
            total_repositories=2,
            total_findings=5,
            priority_counts={"High": 2, "Low": 3},
            highest_priority="High",
        ),
        category_rollup=PortfolioCategoryRollup(
            category_counts={"TD-ARCH": 2, "TD-DEP": 3},
            top_categories=["TD-ARCH", "TD-DEP"],
        ),
        readiness_rollup=PortfolioReadinessRollup(
            total_repositories=2,
            status_counts={"complete": 2},
            repositories_needing_review=[],
        ),
    )


# --- Schema tests ---


class TestPortfolioSchema:
    def test_minimal_valid(self) -> None:
        s = PortfolioSummary()
        assert s.schema_version == "1.0"
        assert s.repositories == []

    def test_rejects_invalid_validation_status(self) -> None:
        with pytest.raises(ValidationError):
            PortfolioRepositoryEntry(
                repository_id="x",
                project_name="x",
                repository_path="/x",
                validation_status="invalid",  # type: ignore[arg-type]
            )

    def test_entry_defaults_safe(self) -> None:
        e = PortfolioRepositoryEntry(
            repository_id="r1",
            project_name="r1",
            repository_path="/r1",
        )
        assert e.total_findings == 0
        assert e.priority_counts == {}
        assert e.top_categories == []
        assert e.highest_priority is None
        assert e.has_ticket_drafts is False
        assert e.has_export_bundles is False
        assert e.validation_status == "unknown"
        assert e.limitations == []

    def test_json_serializable(self) -> None:
        s = _make_summary()
        raw = s.model_dump_json()
        data = json.loads(raw)
        assert data["schema_version"] == "1.0"
        assert len(data["repositories"]) == 2

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PortfolioSummary(unexpected_field="x")  # type: ignore[call-arg]

    def test_risk_rollup_defaults(self) -> None:
        rr = PortfolioRiskRollup()
        assert rr.total_repositories == 0
        assert rr.priority_counts == {}

    def test_category_rollup_defaults(self) -> None:
        cr = PortfolioCategoryRollup()
        assert cr.category_counts == {}

    def test_readiness_rollup_defaults(self) -> None:
        rdr = PortfolioReadinessRollup()
        assert rdr.status_counts == {}


# --- Writer tests ---


class TestPortfolioWriters:
    def test_write_json(self, tmp_path: Path) -> None:
        d = tmp_path / "portfolio"
        s = _make_summary()
        path = write_portfolio_json(d, s)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.0"

    def test_write_repository_index(self, tmp_path: Path) -> None:
        d = tmp_path / "portfolio"
        s = _make_summary()
        path = write_repository_index(d, s)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data) == 2
        assert data[0]["repository_id"] == "repo-1"

    def test_write_markdown(self, tmp_path: Path) -> None:
        d = tmp_path / "portfolio"
        s = _make_summary()
        path = write_portfolio_markdown(d, s)
        assert path.exists()
        md = path.read_text(encoding="utf-8")
        assert "# Portfolio Summary" in md


# --- Markdown rendering tests ---


class TestPortfolioMarkdown:
    def test_deterministic_output(self) -> None:
        s = _make_summary()
        md1 = render_portfolio_markdown(s)
        md2 = render_portfolio_markdown(s)
        assert md1 == md2

    def test_contains_repositories(self) -> None:
        s = _make_summary()
        md = render_portfolio_markdown(s)
        assert "## Repositories" in md
        assert "alpha" in md
        assert "beta" in md

    def test_contains_aggregate_risk(self) -> None:
        s = _make_summary()
        md = render_portfolio_markdown(s)
        assert "## Aggregate Risk" in md
        assert "High" in md

    def test_contains_category_rollup(self) -> None:
        s = _make_summary()
        md = render_portfolio_markdown(s)
        assert "## Category Rollup" in md

    def test_empty_summary_no_crash(self) -> None:
        s = PortfolioSummary()
        md = render_portfolio_markdown(s)
        assert "# Portfolio Summary" in md

    def test_artifact_paths_stable(self, tmp_path: Path) -> None:
        d = tmp_path / "portfolio"
        s = _make_summary()
        p1 = write_portfolio_json(d, s)
        p2 = write_portfolio_markdown(d, s)
        p3 = write_repository_index(d, s)
        assert p1.name == "portfolio-summary.json"
        assert p2.name == "portfolio-summary.md"
        assert p3.name == "repository-index.json"


class TestNoMutation:
    def test_writing_does_not_mutate_summary(self, tmp_path: Path) -> None:
        d = tmp_path / "portfolio"
        s = _make_summary()
        original_json = s.model_dump_json()
        write_portfolio_json(d, s)
        write_portfolio_markdown(d, s)
        write_repository_index(d, s)
        assert s.model_dump_json() == original_json
