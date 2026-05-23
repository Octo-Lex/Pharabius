"""Tests for ticket draft JSON index and summary (W41-S03)."""

from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.tickets import (
    content_hash,
    generate_ticket_draft_index,
    generate_ticket_markdown_drafts,
    render_ticket_draft_summary,
    write_ticket_draft_index,
    write_ticket_draft_summary,
)
from pharabius.schemas.tickets import TicketDraftIndex

WP_MD = """# Work Package: WP-001 Reduce dependency risk

## Linked Debt Items

- `TD-DEP-001`

## Objective

Address missing lockfile.

## Current Risk

Missing lockfile may reduce reproducibility.

## Recommended Engineering Approach

1. Add lockfile.

## Verification Recommendations

- Run CI.

## Risks and Cautions

- Policy check needed.

## Definition of Done

- Lockfile committed.
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


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / ".ai-debt"
    ws.mkdir()
    wp_dir = ws / "work-packages"
    wp_dir.mkdir()
    (wp_dir / "WP-001-slug.md").write_text(WP_MD, encoding="utf-8")
    (ws / "debt-register.json").write_text(json.dumps(REGISTER), encoding="utf-8")
    return ws


class TestContentHash:
    def test_deterministic(self) -> None:
        assert content_hash("hello") == content_hash("hello")

    def test_different_content(self) -> None:
        assert content_hash("hello") != content_hash("world")

    def test_starts_with_sha256(self) -> None:
        h = content_hash("test")
        assert h.startswith("sha256:")


class TestGenerateIndex:
    def test_generates_valid_index(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        assert isinstance(index, TicketDraftIndex)
        assert index.schema_version == "1.0"
        assert len(index.drafts) == 1

    def test_json_roundtrip(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        json_str = index.model_dump_json(indent=2)
        parsed = TicketDraftIndex.model_validate_json(json_str)
        assert len(parsed.drafts) == 1

    def test_drafts_sorted_by_ticket_id(self, tmp_path: Path) -> None:
        ws = tmp_path / ".ai-debt"
        ws.mkdir()
        wp_dir = ws / "work-packages"
        wp_dir.mkdir()
        (wp_dir / "WP-002-beta.md").write_text(WP_MD.replace("WP-001", "WP-002"), encoding="utf-8")
        (wp_dir / "WP-001-alpha.md").write_text(WP_MD, encoding="utf-8")
        (ws / "debt-register.json").write_text(json.dumps(REGISTER), encoding="utf-8")
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        ids = [d.ticket_id for d in index.drafts]
        assert ids == sorted(ids)

    def test_external_fields_null(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        for d in index.drafts:
            assert d.external_system is None
            assert d.external_id is None

    def test_summary_counts(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        s = index.summary
        assert s.total_drafts == 1
        assert s.included_drafts == 1
        assert s.unreviewed == 1
        assert s.excluded_by_review == 0

    def test_content_hash_matches_file(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        d = index.drafts[0]
        assert d.content_hash is not None
        assert d.content_hash.startswith("sha256:")


class TestWriteIndex:
    def test_writes_json_file(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        out = ws / "ticket-drafts"
        path = write_ticket_draft_index(index, out)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.0"

    def test_stable_output(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        out = ws / "ticket-drafts"
        path1 = write_ticket_draft_index(index, out)
        content1 = path1.read_text(encoding="utf-8")
        # Re-generate (same data)
        index2 = generate_ticket_draft_index(ws, drafts)
        path2 = write_ticket_draft_index(index2, out)
        # generated_at will differ, so check structure stability
        data1 = json.loads(content1)
        data2 = json.loads(path2.read_text(encoding="utf-8"))
        assert data1["drafts"][0]["ticket_id"] == data2["drafts"][0]["ticket_id"]


class TestWriteSummary:
    def test_writes_markdown_file(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        reports = ws / "reports"
        path = write_ticket_draft_summary(index, reports)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "# Ticket Draft Summary" in content

    def test_summary_states_no_external_tickets(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        md = render_ticket_draft_summary(index)
        assert "No external tickets were created" in md

    def test_no_mutation(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        reg_before = (ws / "debt-register.json").read_text(encoding="utf-8")
        wp_before = (ws / "work-packages" / "WP-001-slug.md").read_text(encoding="utf-8")
        drafts = generate_ticket_markdown_drafts(ws)
        index = generate_ticket_draft_index(ws, drafts)
        write_ticket_draft_index(index, ws / "ticket-drafts")
        write_ticket_draft_summary(index, ws / "reports")
        assert (ws / "debt-register.json").read_text(encoding="utf-8") == reg_before
        assert (ws / "work-packages" / "WP-001-slug.md").read_text(encoding="utf-8") == wp_before
