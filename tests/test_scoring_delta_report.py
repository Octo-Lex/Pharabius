"""Tests for scoring delta report rendering (W40-S02)."""

from __future__ import annotations

from pharabius.core.scoring import (
    ScoringDeltaConfig,
    ScoringDeltaFactorDetail,
    ScoringDeltaReport,
    ScoringDeltaRow,
    render_scoring_delta_markdown,
)


def _make_report(
    rows: list[ScoringDeltaRow] | None = None,
    factors: list[ScoringDeltaFactorDetail] | None = None,
    warnings: list[str] | None = None,
    total: int = 6,
) -> ScoringDeltaReport:
    return ScoringDeltaReport(
        config=ScoringDeltaConfig(
            enhanced=True,
            use_centrality=True,
            use_frequency=True,
            git_cap=1000,
            path_cap=5000,
            git_timeout=10,
            graph_timeout=5,
        ),
        rows=rows or [],
        factor_details=factors or [],
        warnings=warnings or [],
        total_findings=total,
    )


class TestScoringDeltaReportRendering:
    def test_header(self) -> None:
        md = render_scoring_delta_markdown(_make_report())
        assert md.startswith("# Scoring Delta Report")

    def test_configuration_table(self) -> None:
        md = render_scoring_delta_markdown(_make_report())
        assert "## Configuration" in md
        assert "| Enhanced scoring | enabled |" in md
        assert "| Architecture centrality | enabled |" in md
        assert "| Change frequency | enabled |" in md
        assert "| Git cap | 1000 commits |" in md
        assert "| Path cap | 5000 paths |" in md
        assert "| Git timeout | 10s |" in md
        assert "| Graph timeout | 5s |" in md

    def test_summary_table(self) -> None:
        md = render_scoring_delta_markdown(_make_report())
        assert "## Summary" in md
        assert "| Total findings | 6 |" in md
        assert "| Scores changed | 0 |" in md
        assert "| Scores unchanged | 6 |" in md

    def test_priority_movement_no_changes(self) -> None:
        md = render_scoring_delta_markdown(_make_report())
        assert "## Priority Movement" in md
        assert "| No priority change | 6 |" in md

    def test_priority_movement_with_changes(self) -> None:
        row = ScoringDeltaRow(
            finding_id="TD-ARCH-001",
            title="High fan-in module",
            category="TD-ARCH",
            before_score=18,
            after_score=22,
            before_priority="Medium",
            after_priority="High",
            changed_factors=["architecture_centrality"],
        )
        md = render_scoring_delta_markdown(_make_report(rows=[row], total=3))
        assert "| Medium → High | 1 |" in md
        assert "| No priority change | 2 |" in md

    def test_changed_findings_table(self) -> None:
        row = ScoringDeltaRow(
            finding_id="TD-ARCH-001",
            title="High fan-in module",
            category="TD-ARCH",
            before_score=18,
            after_score=22,
            before_priority="Medium",
            after_priority="High",
            changed_factors=["architecture_centrality"],
        )
        md = render_scoring_delta_markdown(_make_report(rows=[row]))
        assert "## Changed Findings" in md
        assert "| TD-ARCH-001 | TD-ARCH | 18 → 22 | Medium → High | architecture_centrality |" in md

    def test_changed_findings_empty(self) -> None:
        md = render_scoring_delta_markdown(_make_report())
        assert "## Changed Findings" in md
        assert "No score changes." in md

    def test_factor_details_section(self) -> None:
        factor = ScoringDeltaFactorDetail(
            finding_id="TD-ARCH-001",
            factor="architecture_centrality",
            before_level="Low",
            before_value=1,
            after_level="High",
            after_value=5,
            source="architecture-graph.json",
            reason="fan_in=8; top_10_percent_hub=true",
        )
        md = render_scoring_delta_markdown(_make_report(factors=[factor]))
        assert "## Factor Details" in md
        assert "### TD-ARCH-001" in md
        assert "| architecture_centrality | Low (1) | High (5) | architecture-graph.json |" in md

    def test_factor_details_section_hidden_when_empty(self) -> None:
        md = render_scoring_delta_markdown(_make_report())
        assert "## Factor Details" not in md

    def test_warnings_present(self) -> None:
        md = render_scoring_delta_markdown(
            _make_report(warnings=["TD-DEP-001: fallback to Low — no graph"])
        )
        assert "## Warnings and Fallbacks" in md
        assert "- TD-DEP-001: fallback to Low — no graph" in md

    def test_warnings_empty(self) -> None:
        md = render_scoring_delta_markdown(_make_report())
        assert "## Warnings and Fallbacks" in md
        assert "No warnings." in md

    def test_reviewer_notes(self) -> None:
        md = render_scoring_delta_markdown(_make_report())
        assert "## Reviewer Notes" in md
        assert "Enhanced scoring is opt-in." in md

    def test_rendering_does_not_recompute_scores(self) -> None:
        """Renderer is pure presentation — same inputs always produce same output."""
        report = _make_report()
        md1 = render_scoring_delta_markdown(report)
        md2 = render_scoring_delta_markdown(report)
        assert md1 == md2


class TestScoringDeltaReportDataclasses:
    def test_row_frozen(self) -> None:
        row = ScoringDeltaRow(
            finding_id="TD-001",
            title="test",
            category="TD-DEP",
            before_score=10,
            after_score=15,
            before_priority="Low",
            after_priority="Medium",
            changed_factors=["change_frequency"],
        )
        import pytest

        with pytest.raises(AttributeError):
            row.finding_id = "TD-002"  # type: ignore[misc]

    def test_factor_detail_frozen(self) -> None:
        fd = ScoringDeltaFactorDetail(
            finding_id="TD-001",
            factor="change_frequency",
            before_level="Low",
            before_value=1,
            after_level="Medium",
            after_value=3,
            source="git log",
            reason="commits_touching_path=50",
        )
        import pytest

        with pytest.raises(AttributeError):
            fd.factor = "other"  # type: ignore[misc]
