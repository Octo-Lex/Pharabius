"""Tests for PET review sidecar filtering in ticket drafts (W41-S04)."""

from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.tickets import (
    classify_work_package_for_ticketing,
    generate_ticket_markdown_drafts,
    load_review_decisions,
)

WP_MD = """# Work Package: WP-001 Reduce risk

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


class TestLoadReviewDecisions:
    def test_no_sidecar_returns_empty(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        decisions = load_review_decisions(ws)
        assert decisions == {}

    def test_loads_decisions(self, tmp_path: Path) -> None:
        ws = _make_workspace(
            tmp_path,
            [{"finding_id": "TD-DEP-001", "status": "accepted"}],
        )
        decisions = load_review_decisions(ws)
        assert decisions["TD-DEP-001"] == "accepted"


class TestClassifyWorkPackage:
    def test_no_review_includes_all(self) -> None:
        label, include, _, _ = classify_work_package_for_ticketing(["TD-001"], {})
        assert include is True
        assert label == "not_reviewed"

    def test_accepted_included(self) -> None:
        label, include, _, _ = classify_work_package_for_ticketing(
            ["TD-001"], {"TD-001": "accepted"}
        )
        assert include is True
        assert label == "accepted"

    def test_needs_investigation_included(self) -> None:
        _label, include, _, _ = classify_work_package_for_ticketing(
            ["TD-001"], {"TD-001": "needs-investigation"}
        )
        assert include is True

    def test_deferred_excluded_by_default(self) -> None:
        _label, include, _, _ = classify_work_package_for_ticketing(
            ["TD-001"], {"TD-001": "deferred"}
        )
        assert include is False

    def test_deferred_included_with_flag(self) -> None:
        _label, include, _, _ = classify_work_package_for_ticketing(
            ["TD-001"], {"TD-001": "deferred"}, include_deferred=True
        )
        assert include is True

    def test_rejected_excluded(self) -> None:
        _label, include, _, _ = classify_work_package_for_ticketing(
            ["TD-001"], {"TD-001": "rejected"}
        )
        assert include is False

    def test_duplicate_excluded(self) -> None:
        _label, include, _, _ = classify_work_package_for_ticketing(
            ["TD-001"], {"TD-001": "duplicate"}
        )
        assert include is False

    def test_mixed_accepted_deferred_included(self) -> None:
        label, include, summary, _excluded = classify_work_package_for_ticketing(
            ["TD-001", "TD-002"],
            {"TD-001": "accepted", "TD-002": "deferred"},
        )
        assert include is True
        assert label == "mixed"
        assert "accepted" in summary

    def test_mixed_accepted_rejected_included(self) -> None:
        _label, include, _, excluded = classify_work_package_for_ticketing(
            ["TD-001", "TD-002"],
            {"TD-001": "accepted", "TD-002": "rejected"},
        )
        assert include is True
        assert "TD-002" in excluded

    def test_all_rejected_excluded(self) -> None:
        _label, include, _, _ = classify_work_package_for_ticketing(
            ["TD-001", "TD-002"],
            {"TD-001": "rejected", "TD-002": "rejected"},
        )
        assert include is False


class TestReviewFilteringIntegration:
    def test_no_sidecar_includes_all_as_not_reviewed(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        drafts, _ = generate_ticket_markdown_drafts(ws)
        assert len(drafts) == 1
        assert drafts[0].review_decision == "not_reviewed"
        assert drafts[0].status == "draft"

    def test_accepted_included(self, tmp_path: Path) -> None:
        ws = _make_workspace(
            tmp_path,
            [{"finding_id": "TD-DEP-001", "status": "accepted"}],
        )
        drafts, _ = generate_ticket_markdown_drafts(ws)
        assert len(drafts) == 1
        assert drafts[0].review_decision == "accepted"
        assert drafts[0].status == "draft"

    def test_rejected_excluded(self, tmp_path: Path) -> None:
        ws = _make_workspace(
            tmp_path,
            [{"finding_id": "TD-DEP-001", "status": "rejected"}],
        )
        drafts, _ = generate_ticket_markdown_drafts(ws)
        assert len(drafts) == 1
        assert drafts[0].status == "excluded"

    def test_deferred_excluded_by_default(self, tmp_path: Path) -> None:
        ws = _make_workspace(
            tmp_path,
            [{"finding_id": "TD-DEP-001", "status": "deferred"}],
        )
        drafts, _ = generate_ticket_markdown_drafts(ws)
        assert len(drafts) == 1
        assert drafts[0].status == "excluded"

    def test_deferred_included_with_flag(self, tmp_path: Path) -> None:
        ws = _make_workspace(
            tmp_path,
            [{"finding_id": "TD-DEP-001", "status": "deferred"}],
        )
        drafts, _ = generate_ticket_markdown_drafts(ws, include_deferred=True)
        assert len(drafts) == 1
        assert drafts[0].status == "draft"
        assert drafts[0].review_decision == "deferred"

    def test_review_does_not_change_risk_score(self, tmp_path: Path) -> None:
        ws_no_review = _make_workspace(tmp_path / "a")
        ws_accepted = _make_workspace(
            tmp_path / "b",
            [{"finding_id": "TD-DEP-001", "status": "accepted"}],
        )
        d1, _ = generate_ticket_markdown_drafts(ws_no_review)
        d1 = d1[0]
        d2, _ = generate_ticket_markdown_drafts(ws_accepted)
        d2 = d2[0]
        assert d1.risk_score == d2.risk_score
        assert d1.priority == d2.priority

    def test_review_does_not_mutate_debt_register(self, tmp_path: Path) -> None:
        ws = _make_workspace(
            tmp_path,
            [{"finding_id": "TD-DEP-001", "status": "rejected"}],
        )
        reg_before = (ws / "debt-register.json").read_text(encoding="utf-8")
        generate_ticket_markdown_drafts(ws)
        reg_after = (ws / "debt-register.json").read_text(encoding="utf-8")
        assert reg_before == reg_after

    def test_review_does_not_mutate_work_packages(self, tmp_path: Path) -> None:
        ws = _make_workspace(
            tmp_path,
            [{"finding_id": "TD-DEP-001", "status": "accepted"}],
        )
        wp_before = (ws / "work-packages" / "WP-001-slug.md").read_text(encoding="utf-8")
        generate_ticket_markdown_drafts(ws)
        wp_after = (ws / "work-packages" / "WP-001-slug.md").read_text(encoding="utf-8")
        assert wp_before == wp_after

    def test_markdown_includes_pet_review_status(self, tmp_path: Path) -> None:
        ws = _make_workspace(
            tmp_path,
            [{"finding_id": "TD-DEP-001", "status": "accepted"}],
        )
        generate_ticket_markdown_drafts(ws)
        md = (ws / "ticket-drafts" / "TICKET-WP-001.md").read_text(encoding="utf-8")
        assert "PET Review Status" in md
        assert "accepted" in md
