"""Tests for portfolio example files (W45-S06)."""

from __future__ import annotations

import json
from pathlib import Path

EXAMPLES = Path("docs/examples/portfolio")


class TestPortfolioExamples:
    def test_summary_json_parses(self) -> None:
        data = json.loads((EXAMPLES / "portfolio-summary.example.json").read_text())
        assert data["schema_version"] == "1.0"
        assert len(data["repositories"]) == 2

    def test_repository_index_parses(self) -> None:
        data = json.loads((EXAMPLES / "repository-index.example.json").read_text())
        assert len(data) == 2
        assert data[0]["repository_id"] == "service-a"

    def test_summary_md_exists(self) -> None:
        assert (EXAMPLES / "portfolio-summary.example.md").exists()

    def test_validation_rollup_md_exists(self) -> None:
        assert (EXAMPLES / "validation-rollup.example.md").exists()


class TestDocsSafety:
    def test_portfolio_docs_no_api_claims(self) -> None:
        md = Path("docs/PORTFOLIO.md").read_text().lower()
        assert "does not crawl" in md
        assert "does not call" in md
        assert "no external apis" in md
