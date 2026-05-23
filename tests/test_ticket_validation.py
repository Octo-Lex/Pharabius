"""Tests for malformed/missing work package validation (W42-S03)."""

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


def _make_workspace(
    tmp_path: Path,
    work_packages: dict[str, str] | None = None,
    review_decisions: list[dict] | None = None,
) -> Path:
    ws = tmp_path / ".ai-debt"
    ws.mkdir(parents=True)
    wp_dir = ws / "work-packages"
    if work_packages is not None:
        wp_dir.mkdir(parents=True)
        for name, content in work_packages.items():
            (wp_dir / name).write_text(content, encoding="utf-8")
    (ws / "debt-register.json").write_text(json.dumps(REGISTER), encoding="utf-8")
    if review_decisions is not None:
        review_dir = ws / "review"
        review_dir.mkdir()
        (review_dir / "decisions.json").write_text(
            json.dumps({"decisions": review_decisions}), encoding="utf-8"
        )
    return ws


class TestMissingWorkPackages:
    def test_missing_directory_returns_empty(self, tmp_path: Path) -> None:
        ws = tmp_path / ".ai-debt"
        ws.mkdir()
        (ws / "debt-register.json").write_text(json.dumps(REGISTER), encoding="utf-8")
        drafts, issues = generate_ticket_markdown_drafts(ws)
        assert drafts == []
        assert len(issues) == 1
        assert issues[0].code == "missing_work_packages_directory"

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {})
        drafts, issues = generate_ticket_markdown_drafts(ws)
        assert drafts == []
        assert len(issues) == 1
        assert issues[0].code == "empty_work_packages_directory"

    def test_missing_directory_no_crash(self, tmp_path: Path) -> None:
        ws = tmp_path / ".ai-debt"
        ws.mkdir()
        (ws / "debt-register.json").write_text("{}", encoding="utf-8")
        drafts, issues = generate_ticket_markdown_drafts(ws)
        assert isinstance(drafts, list)
        assert isinstance(issues, list)


class TestMalformedWorkPackages:
    def test_non_wp_prefixed_file_skipped(self, tmp_path: Path) -> None:
        """Files without WP- prefix get a non-WP ID and are skipped."""
        bad_md = "# Some random markdown\n\nNo work package ID here."
        ws = _make_workspace(tmp_path, {"notes.md": bad_md})
        drafts, issues = generate_ticket_markdown_drafts(ws)
        assert len(drafts) == 0
        assert any(i.code == "missing_work_package_id" for i in issues)

    def test_mixed_valid_and_invalid(self, tmp_path: Path) -> None:
        bad_md = "# Not a WP\n"
        ws = _make_workspace(tmp_path, {"WP-001-good.md": WP_MD, "notes.md": bad_md})
        drafts, issues = generate_ticket_markdown_drafts(ws)
        assert len(drafts) == 1
        assert drafts[0].ticket_id == "TICKET-WP-001"
        assert any(i.code == "missing_work_package_id" for i in issues)

    def test_no_mutation_of_malformed_source(self, tmp_path: Path) -> None:
        bad_md = "# Original bad content\n"
        ws = _make_workspace(tmp_path, {"notes.md": bad_md})
        bad_path = ws / "work-packages" / "notes.md"
        before = bad_path.read_text(encoding="utf-8")
        generate_ticket_markdown_drafts(ws)
        assert bad_path.read_text(encoding="utf-8") == before

    def test_unreadable_file_skipped(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-good.md": WP_MD})
        # Create a file with invalid UTF-8 bytes
        bad_path = ws / "work-packages" / "WP-002-bad.md"
        bad_path.write_bytes(b"\xff\xfe Invalid UTF-8 \x80\x81")
        drafts, issues = generate_ticket_markdown_drafts(ws)
        assert len(drafts) == 1
        assert any(i.code == "unreadable_work_package" for i in issues)


class TestValidationIssuesInIndex:
    def test_validation_issues_in_json_index(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-good.md": WP_MD, "notes.md": "# Not WP\n"})
        drafts, issues = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts, issues)
        assert len(index.validation_issues) >= 1
        assert index.validation_issues[0].code == "missing_work_package_id"

    def test_validation_issues_in_summary(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-good.md": WP_MD, "notes.md": "# Not WP\n"})
        drafts, issues = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts, issues)
        md = render_ticket_draft_summary(index)
        assert "## Validation Issues" in md
        assert "missing_work_package_id" in md

    def test_no_validation_section_when_clean(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-good.md": WP_MD})
        drafts, issues = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts, issues)
        md = render_ticket_draft_summary(index)
        assert "## Validation Issues" not in md

    def test_no_debt_register_mutation(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-good.md": WP_MD, "notes.md": "# Not WP\n"})
        reg_before = (ws / "debt-register.json").read_text(encoding="utf-8")
        generate_ticket_markdown_drafts(ws)
        assert (ws / "debt-register.json").read_text(encoding="utf-8") == reg_before
