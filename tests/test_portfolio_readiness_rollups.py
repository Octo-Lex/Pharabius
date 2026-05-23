"""Tests for portfolio readiness and validation rollups (W45-S04)."""

from __future__ import annotations

from pathlib import Path

from pharabius.core.portfolio import (
    compute_readiness_rollup,
    render_validation_rollup_markdown,
    write_validation_rollup,
)
from pharabius.schemas.portfolio import PortfolioRepositoryEntry


def _entry(
    repo_id: str,
    status: str = "complete",
    tickets: bool = False,
    exports: bool = False,
    limitations: list[str] | None = None,
) -> PortfolioRepositoryEntry:
    return PortfolioRepositoryEntry(
        repository_id=repo_id,
        project_name=repo_id,
        repository_path=f"/repos/{repo_id}",
        validation_status=status,  # type: ignore[arg-type]
        has_ticket_drafts=tickets,
        has_export_bundles=exports,
        limitations=limitations or [],
    )


class TestReadinessRollup:
    def test_complete_repository(self) -> None:
        entries = [_entry("a", status="complete", tickets=True, exports=True)]
        rollup = compute_readiness_rollup(entries)
        assert rollup.total_repositories == 1
        assert rollup.with_ticket_drafts == 1
        assert rollup.with_export_bundles == 1
        assert rollup.status_counts["complete"] == 1
        assert rollup.repositories_needing_review == []

    def test_partial_repository(self) -> None:
        entries = [_entry("b", status="partial")]
        rollup = compute_readiness_rollup(entries)
        assert rollup.status_counts["partial"] == 1
        assert rollup.with_ticket_drafts == 0

    def test_needs_review_repository(self) -> None:
        entries = [_entry("c", status="needs_review", limitations=["Missing X"])]
        rollup = compute_readiness_rollup(entries)
        assert "c" in rollup.repositories_needing_review
        assert any("Missing X" in w for w in rollup.warnings)

    def test_unknown_repository(self) -> None:
        entries = [_entry("d", status="unknown")]
        rollup = compute_readiness_rollup(entries)
        assert "d" in rollup.repositories_needing_review

    def test_ticket_and_bundle_counts(self) -> None:
        entries = [
            _entry("a", tickets=True),
            _entry("b", tickets=True, exports=True),
            _entry("c"),
        ]
        rollup = compute_readiness_rollup(entries)
        assert rollup.with_ticket_drafts == 2
        assert rollup.with_export_bundles == 1

    def test_empty_entries(self) -> None:
        rollup = compute_readiness_rollup([])
        assert rollup.total_repositories == 0
        assert rollup.repositories_needing_review == []

    def test_limitations_aggregated(self) -> None:
        entries = [
            _entry("x", limitations=["Issue A"]),
            _entry("y", limitations=["Issue B"]),
        ]
        rollup = compute_readiness_rollup(entries)
        assert len(rollup.warnings) == 2


class TestValidationRollupMarkdown:
    def test_contains_summary(self) -> None:
        entries = [_entry("a", status="complete", tickets=True)]
        md = render_validation_rollup_markdown(entries)
        assert "## Summary" in md
        assert "**Total repositories**: 1" in md

    def test_contains_readiness_table(self) -> None:
        entries = [_entry("a", status="complete")]
        md = render_validation_rollup_markdown(entries)
        assert "## Readiness by Repository" in md
        assert "a" in md

    def test_contains_needing_review(self) -> None:
        entries = [_entry("bad", status="needs_review")]
        md = render_validation_rollup_markdown(entries)
        assert "## Repositories Needing Review" in md
        assert "bad" in md

    def test_contains_warnings(self) -> None:
        entries = [_entry("x", limitations=["Missing register"])]
        md = render_validation_rollup_markdown(entries)
        assert "## Warnings and Limitations" in md
        assert "Missing register" in md

    def test_deterministic(self) -> None:
        entries = [_entry("a", status="complete"), _entry("b", status="partial")]
        md1 = render_validation_rollup_markdown(entries)
        md2 = render_validation_rollup_markdown(entries)
        assert md1 == md2


class TestValidationRollupWriter:
    def test_writes_file(self, tmp_path: Path) -> None:
        entries = [_entry("a", status="complete")]
        path = write_validation_rollup(tmp_path / "portfolio", entries)
        assert path.exists()
        assert path.name == "validation-rollup.md"

    def test_creates_directory(self, tmp_path: Path) -> None:
        d = tmp_path / "portfolio"
        assert not d.exists()
        write_validation_rollup(d, [_entry("a")])
        assert d.exists()


class TestNoMutation:
    def test_readiness_does_not_mutate_entries(self) -> None:
        entries = [_entry("a", limitations=["test"])]
        compute_readiness_rollup(entries)
        assert entries[0].limitations == ["test"]
