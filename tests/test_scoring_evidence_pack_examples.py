"""Tests for scoring evidence pack example artifacts (W40-S01)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "docs" / "examples"


class TestScoringEvidencePackExampleJSON:
    """Validate the example JSON artifact is syntactically valid and complete."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.path = EXAMPLES_DIR / "scoring-evidence-pack.example.json"
        if not self.path.exists():
            pytest.skip("Example JSON not found")
        self.data = json.loads(self.path.read_text(encoding="utf-8"))

    def test_is_valid_json(self) -> None:
        """Example JSON parses without error."""
        assert isinstance(self.data, dict)

    def test_top_level_required_fields(self) -> None:
        for field in (
            "schema_version",
            "tool_version",
            "generated_at",
            "analysis_mode",
            "repositories",
            "summary",
        ):
            assert field in self.data, f"Missing top-level field: {field}"

    def test_analysis_mode(self) -> None:
        assert self.data["analysis_mode"] == "enhanced_scoring_validation"

    def test_repositories_is_list(self) -> None:
        assert isinstance(self.data["repositories"], list)
        assert len(self.data["repositories"]) >= 1

    def test_repository_entry_fields(self) -> None:
        repo = self.data["repositories"][0]
        for field in (
            "name",
            "path",
            "commit",
            "default_findings",
            "enhanced_findings",
            "finding_ids_stable",
            "evidence_ids_stable",
            "canonical_mutation_in_preview",
            "score_changes",
            "warnings",
            "runtime_seconds",
        ):
            assert field in repo, f"Missing repo field: {field}"

    def test_score_change_entry_fields(self) -> None:
        if not self.data["repositories"]:
            pytest.skip("No repositories in example")
        repo = self.data["repositories"][0]
        if not repo["score_changes"]:
            pytest.skip("No score changes in example")
        change = repo["score_changes"][0]
        for field in (
            "finding_id",
            "title",
            "category",
            "before_score",
            "after_score",
            "before_priority",
            "after_priority",
            "changed_factors",
        ):
            assert field in change, f"Missing score change field: {field}"

    def test_changed_factor_entry_fields(self) -> None:
        repo = self.data["repositories"][0]
        if not repo["score_changes"]:
            pytest.skip("No score changes")
        change = repo["score_changes"][0]
        if not change["changed_factors"]:
            pytest.skip("No changed factors")
        factor = change["changed_factors"][0]
        for field in (
            "factor",
            "before_level",
            "after_level",
            "before_value",
            "after_value",
            "source",
            "reason",
        ):
            assert field in factor, f"Missing factor field: {field}"

    def test_summary_fields(self) -> None:
        for field in (
            "repositories_checked",
            "repositories_passed",
            "score_changes_total",
            "priority_changes_total",
            "preview_mutation_failures",
            "id_stability_failures",
        ):
            assert field in self.data["summary"], f"Missing summary field: {field}"

    def test_preview_mutation_failures_zero(self) -> None:
        assert self.data["summary"]["preview_mutation_failures"] == 0

    def test_id_stability_failures_zero(self) -> None:
        assert self.data["summary"]["id_stability_failures"] == 0


class TestScoringEvidencePackExampleMarkdown:
    """Validate the example Markdown artifact exists and is readable."""

    def test_exists(self) -> None:
        path = EXAMPLES_DIR / "scoring-evidence-pack.example.md"
        assert path.exists()

    def test_has_title(self) -> None:
        path = EXAMPLES_DIR / "scoring-evidence-pack.example.md"
        content = path.read_text(encoding="utf-8")
        assert content.strip().startswith("# Scoring Evidence Pack")

    def test_has_summary_section(self) -> None:
        path = EXAMPLES_DIR / "scoring-evidence-pack.example.md"
        content = path.read_text(encoding="utf-8")
        assert "## Summary" in content

    def test_has_score_changes_section(self) -> None:
        path = EXAMPLES_DIR / "scoring-evidence-pack.example.md"
        content = path.read_text(encoding="utf-8")
        assert "## Score Changes" in content
