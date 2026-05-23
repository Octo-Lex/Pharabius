"""Tests for ticket draft summary report improvements (W42-S01)."""

from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.tickets import (
    generate_ticket_draft_index,
    generate_ticket_markdown_drafts,
    render_ticket_draft_summary,
)

WP_MD = """# Work Package: WP-001 Fix risk

## Linked Debt Items

- `TD-DEP-001`

## Objective

Fix it.

## Current Risk

Bad.

## Recommended Engineering Approach

1. Fix.

## Verification Recommendations

- Test.

## Risks and Cautions

- None.

## Definition of Done

- Done.
"""

REGISTER = {
    "findings": [
        {
            "id": "TD-DEP-001",
            "category": "TD-DEP",
            "risk_score": 15,
            "priority": "Medium",
            "evidence_ids": ["EVD-001"],
        }
    ]
}


def _make_workspace(tmp_path: Path, review_decisions: list[dict] | None = None) -> Path:
    ws = tmp_path / ".ai-debt"
    ws.mkdir(parents=True)
    wp_dir = ws / "work-packages"
    wp_dir.mkdir()
    (wp_dir / "WP-001-slug.md").write_text(WP_MD, encoding="utf-8")
    (ws / "debt-register.json").write_text(json.dumps(REGISTER), encoding="utf-8")
    if review_decisions is not None:
        review_dir = ws / "review"
        review_dir.mkdir()
        (review_dir / "decisions.json").write_text(
            json.dumps({"decisions": review_decisions}), encoding="utf-8"
        )
    return ws


class TestSummaryReportStructure:
    def test_contains_generation_summary(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        md = render_ticket_draft_summary(index)
        assert "## Generation Summary" in md
        assert "Work packages scanned" in md
        assert "Ticket drafts generated" in md

    def test_contains_output_artifacts(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        md = render_ticket_draft_summary(index)
        assert "## Output Artifacts" in md
        assert "ticket-drafts.json" in md

    def test_contains_draft_table(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        md = render_ticket_draft_summary(index)
        assert "## Drafts" in md
        assert "TICKET-WP-001" in md

    def test_contains_warnings_section(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        md = render_ticket_draft_summary(index)
        assert "## Warnings and Limitations" in md
        assert "local planning artifacts" in md.lower()

    def test_shows_skipped_items(self, tmp_path: Path) -> None:
        ws = _make_workspace(
            tmp_path,
            [{"finding_id": "TD-DEP-001", "status": "rejected"}],
        )
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        md = render_ticket_draft_summary(index)
        assert "## Skipped Items" in md
        assert "WP-001" in md
        assert "rejected" in md

    def test_no_skipped_section_when_all_included(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        md = render_ticket_draft_summary(index)
        assert "## Skipped Items" not in md

    def test_review_decision_summary(self, tmp_path: Path) -> None:
        ws = _make_workspace(
            tmp_path,
            [{"finding_id": "TD-DEP-001", "status": "accepted"}],
        )
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        md = render_ticket_draft_summary(index)
        assert "## Review Decision Summary" in md
        assert "accepted" in md
        assert "Drafted" in md

    def test_no_review_section_when_no_reviews(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        md = render_ticket_draft_summary(index)
        assert "## Review Decision Summary" not in md

    def test_unreviewed_count_in_warnings(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        md = render_ticket_draft_summary(index)
        assert "have not been reviewed" in md


class TestSummaryDeterminism:
    def test_deterministic_output(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        md1 = render_ticket_draft_summary(index)
        md2 = render_ticket_draft_summary(index)
        # Drafts table content should be identical (generated_at may differ)
        assert md1 == md2

    def test_does_not_mutate_debt_register(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        reg_before = (ws / "debt-register.json").read_text(encoding="utf-8")
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        render_ticket_draft_summary(index)
        assert (ws / "debt-register.json").read_text(encoding="utf-8") == reg_before

    def test_does_not_mutate_work_packages(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        wp_before = (ws / "work-packages" / "WP-001-slug.md").read_text(encoding="utf-8")
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        render_ticket_draft_summary(index)
        assert (ws / "work-packages" / "WP-001-slug.md").read_text() == wp_before
