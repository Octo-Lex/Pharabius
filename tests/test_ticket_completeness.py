"""Tests for ticket draft field completeness checks (W42-S04)."""

from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.tickets import (
    evaluate_ticket_draft_completeness,
    generate_ticket_draft_index,
    generate_ticket_markdown_drafts,
    render_ticket_draft_summary,
)
from pharabius.schemas.tickets import TicketDraft

WP_MD = """# Work Package: WP-001 Fix risk

## Linked Debt Items

- `TD-DEP-001`

## Objective

Fix it properly with good approach.

## Current Risk

Bad.

## Recommended Engineering Approach

1. Fix the architecture.
2. Add tests.

## Verification Recommendations

- Test thoroughly.

## Risks and Cautions

- None.

## Definition of Done

- Done.
"""

WP_MINIMAL = """# Work Package: WP-002 Minimal

## Objective

Fix.

## Current Risk

Bad.
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


def _make_workspace(
    tmp_path: Path,
    work_packages: dict[str, str],
) -> Path:
    ws = tmp_path / ".ai-debt"
    ws.mkdir(parents=True)
    wp_dir = ws / "work-packages"
    wp_dir.mkdir(parents=True)
    for name, content in work_packages.items():
        (wp_dir / name).write_text(content, encoding="utf-8")
    (ws / "debt-register.json").write_text(json.dumps(REGISTER), encoding="utf-8")
    return ws


def _make_complete_draft() -> TicketDraft:
    return TicketDraft(
        ticket_id="TICKET-WP-001",
        title="Fix risk",
        source_type="work_package",
        source_id="WP-001",
        artifact_path=".ai-debt/ticket-drafts/TICKET-WP-001.md",
        linked_debt_items=["TD-DEP-001"],
        categories=["TD-DEP"],
        priority="High",
        risk_score=24,
        review_decision="accepted",
        status="draft",
        labels=["TD-DEP"],
        external_system=None,
        external_id=None,
        content_hash="sha256:abc",
        body_markdown=(
            "# Ticket: Fix risk\n\n"
            "## Objective\nFix it properly with good approach.\n\n"
            "## Recommended Engineering Approach\n1. Fix.\n\n"
            "## Verification Recommendations\n- Test.\n\n"
            "## Risks and Cautions\n- None.\n\n"
            "## Definition of Done\n- Done.\n"
        ),
        review_summary={"accepted": 1},
        excluded_linked_debt_items=[],
    )


class TestCompletenessEvaluator:
    def test_complete_draft(self) -> None:
        draft = _make_complete_draft()
        comp = evaluate_ticket_draft_completeness(draft)
        assert comp.status == "complete"
        assert comp.missing_fields == []
        assert comp.weak_fields == []

    def test_missing_title_needs_review(self) -> None:
        draft = _make_complete_draft()
        draft.title = ""
        comp = evaluate_ticket_draft_completeness(draft)
        assert comp.status == "needs_review"
        assert "title" in comp.missing_fields

    def test_missing_source_id_needs_review(self) -> None:
        draft = _make_complete_draft()
        draft.source_id = ""
        comp = evaluate_ticket_draft_completeness(draft)
        assert comp.status == "needs_review"
        assert "source_work_package_id" in comp.missing_fields

    def test_missing_body_needs_review(self) -> None:
        draft = _make_complete_draft()
        draft.body_markdown = ""
        comp = evaluate_ticket_draft_completeness(draft)
        assert comp.status == "needs_review"
        assert "objective" in comp.missing_fields

    def test_short_body_needs_review(self) -> None:
        draft = _make_complete_draft()
        draft.body_markdown = "## Short"
        comp = evaluate_ticket_draft_completeness(draft)
        assert comp.status == "needs_review"
        assert "objective" in comp.missing_fields

    def test_missing_linked_debt_partial(self) -> None:
        draft = _make_complete_draft()
        draft.linked_debt_items = []
        comp = evaluate_ticket_draft_completeness(draft)
        assert comp.status == "partial"
        assert "linked_debt_items" in comp.weak_fields

    def test_missing_approach_partial(self) -> None:
        draft = _make_complete_draft()
        draft.body_markdown = (
            "# Ticket: Fix risk\n\n## Objective\nFix.\n\n"
            "## Verification Recommendations\n- Test.\n\n"
            "## Definition of Done\n- Done.\n"
        )
        comp = evaluate_ticket_draft_completeness(draft)
        assert comp.status == "partial"
        assert "recommended_approach" in comp.weak_fields

    def test_missing_verification_partial(self) -> None:
        draft = _make_complete_draft()
        draft.body_markdown = (
            "# Ticket: Fix risk\n\n## Objective\nFix.\n\n"
            "## Recommended Engineering Approach\n1. Fix.\n\n"
            "## Definition of Done\n- Done.\n"
        )
        comp = evaluate_ticket_draft_completeness(draft)
        assert comp.status == "partial"
        assert "verification_recommendations" in comp.weak_fields

    def test_missing_dod_partial(self) -> None:
        draft = _make_complete_draft()
        draft.body_markdown = (
            "# Ticket: Fix risk\n\n## Objective\nFix.\n\n"
            "## Recommended Engineering Approach\n1. Fix.\n\n"
            "## Verification Recommendations\n- Test.\n"
        )
        comp = evaluate_ticket_draft_completeness(draft)
        assert comp.status == "partial"
        assert "definition_of_done" in comp.weak_fields

    def test_missing_priority_partial(self) -> None:
        draft = _make_complete_draft()
        draft.priority = None
        comp = evaluate_ticket_draft_completeness(draft)
        assert comp.status == "partial"
        assert "priority" in comp.weak_fields

    def test_deterministic(self) -> None:
        draft = _make_complete_draft()
        comp1 = evaluate_ticket_draft_completeness(draft)
        comp2 = evaluate_ticket_draft_completeness(draft)
        assert comp1 == comp2


class TestCompletenessInGeneration:
    def test_completeness_populated(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-good.md": WP_MD})
        drafts, _ = generate_ticket_markdown_drafts(ws)
        assert len(drafts) == 1
        assert drafts[0].completeness is not None
        assert drafts[0].completeness.status in ("complete", "partial", "needs_review")

    def test_minimal_wp_is_partial(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-002-min.md": WP_MINIMAL})
        drafts, _ = generate_ticket_markdown_drafts(ws)
        assert len(drafts) == 1
        assert drafts[0].completeness is not None
        assert drafts[0].completeness.status in ("partial", "needs_review")

    def test_completeness_in_summary(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-good.md": WP_MD})
        drafts, issues = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts, issues)
        md = render_ticket_draft_summary(index)
        assert "## Draft Completeness" in md
        assert "complete" in md or "partial" in md or "needs_review" in md

    def test_completeness_warnings_in_summary(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-002-min.md": WP_MINIMAL})
        drafts, issues = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts, issues)
        md = render_ticket_draft_summary(index)
        assert "## Field Completeness Warnings" in md

    def test_no_completeness_warnings_when_complete(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-good.md": WP_MD})
        drafts, issues = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts, issues)
        md = render_ticket_draft_summary(index)
        # If the draft is complete, no warnings section
        if all(d.completeness and d.completeness.status == "complete" for d in drafts):
            assert "## Field Completeness Warnings" not in md
