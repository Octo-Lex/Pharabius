"""Tests for ticket Markdown draft generation (W41-S02)."""

from __future__ import annotations

from pathlib import Path

from pharabius.core.tickets import (
    generate_ticket_markdown_drafts,
    parse_work_package_markdown,
)


def _make_workspace(tmp_path: Path, wps: dict[str, str], register: dict | None = None) -> Path:
    """Create a minimal .ai-debt workspace for testing."""
    ws = tmp_path / ".ai-debt"
    ws.mkdir()
    wp_dir = ws / "work-packages"
    wp_dir.mkdir()
    for name, content in wps.items():
        (wp_dir / name).write_text(content, encoding="utf-8")
    if register:
        (ws / "debt-register.json").write_text(__import__("json").dumps(register), encoding="utf-8")
    return ws


WP_MD = """# Work Package: WP-001 Reduce dependency risk

## Status

Ready for Product Engineering review

## Linked Debt Items

- `TD-DEP-001`

## Objective

Address missing lockfile evidence for reproducible builds.

## Current Risk

Missing lockfile may reduce dependency reproducibility.

## Recommended Engineering Approach

1. Confirm dependency management policy.
2. Add lockfile.
3. Update CI.

## Expected Affected Areas

- `pyproject.toml`

## Verification Recommendations

- Run dependency install in clean environment.
- Verify CI uses lockfile.

## Risks and Cautions

- Some repos intentionally skip lockfiles.

## Definition of Done

- Lockfile present and committed.
- CI passes with lockfile.

## Evidence

- `EVD-000138`

## Estimated Effort

Small
"""

REGISTER = {
    "findings": [
        {
            "id": "TD-DEP-001",
            "category": "TD-DEP",
            "risk_score": 15,
            "priority": "Medium",
            "evidence_ids": ["EVD-000138"],
            "title": "Dependency manifest without lockfile",
        }
    ]
}


class TestParseWorkPackage:
    def test_parses_id_from_filename(self, tmp_path: Path) -> None:
        p = tmp_path / "WP-001-slug.md"
        p.write_text(WP_MD, encoding="utf-8")
        parsed = parse_work_package_markdown(p)
        assert parsed.id == "WP-001"

    def test_parses_title(self, tmp_path: Path) -> None:
        p = tmp_path / "WP-001-slug.md"
        p.write_text(WP_MD, encoding="utf-8")
        parsed = parse_work_package_markdown(p)
        assert "WP-001" in parsed.title
        assert "dependency" in parsed.title.lower()

    def test_parses_linked_debt_items(self, tmp_path: Path) -> None:
        p = tmp_path / "WP-001-slug.md"
        p.write_text(WP_MD, encoding="utf-8")
        parsed = parse_work_package_markdown(p)
        assert parsed.linked_debt_items == ["TD-DEP-001"]

    def test_parses_objective(self, tmp_path: Path) -> None:
        p = tmp_path / "WP-001-slug.md"
        p.write_text(WP_MD, encoding="utf-8")
        parsed = parse_work_package_markdown(p)
        assert parsed.objective is not None
        assert "lockfile" in parsed.objective.lower()

    def test_parses_approach(self, tmp_path: Path) -> None:
        p = tmp_path / "WP-001-slug.md"
        p.write_text(WP_MD, encoding="utf-8")
        parsed = parse_work_package_markdown(p)
        assert len(parsed.recommended_engineering_approach) == 3

    def test_parses_evidence(self, tmp_path: Path) -> None:
        p = tmp_path / "WP-001-slug.md"
        p.write_text(WP_MD, encoding="utf-8")
        parsed = parse_work_package_markdown(p)
        assert "EVD-000138" in parsed.evidence


class TestGenerateTicketMarkdownDrafts:
    def test_generates_one_draft(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-slug.md": WP_MD}, REGISTER)
        drafts, _ = generate_ticket_markdown_drafts(ws)
        assert len(drafts) == 1
        assert drafts[0].ticket_id == "TICKET-WP-001"

    def test_generates_deterministic_filename(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-slug.md": WP_MD}, REGISTER)
        drafts, _ = generate_ticket_markdown_drafts(ws)
        assert drafts[0].artifact_path.endswith("TICKET-WP-001.md")

    def test_includes_source_work_package_id(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-slug.md": WP_MD}, REGISTER)
        drafts, _ = generate_ticket_markdown_drafts(ws)
        assert drafts[0].source_id == "WP-001"

    def test_includes_linked_debt_items(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-slug.md": WP_MD}, REGISTER)
        drafts, _ = generate_ticket_markdown_drafts(ws)
        assert "TD-DEP-001" in drafts[0].linked_debt_items

    def test_includes_priority_and_risk_score(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-slug.md": WP_MD}, REGISTER)
        drafts, _ = generate_ticket_markdown_drafts(ws)
        assert drafts[0].priority == "Medium"
        assert drafts[0].risk_score == 15

    def test_includes_categories(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-slug.md": WP_MD}, REGISTER)
        drafts, _ = generate_ticket_markdown_drafts(ws)
        assert "TD-DEP" in drafts[0].categories

    def test_writes_markdown_file(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-slug.md": WP_MD}, REGISTER)
        generate_ticket_markdown_drafts(ws)
        md_path = ws / "ticket-drafts" / "TICKET-WP-001.md"
        assert md_path.exists()
        content = md_path.read_text(encoding="utf-8")
        assert "# Ticket:" in content
        assert "TICKET-WP-001" in content
        assert "WP-001" in content

    def test_markdown_includes_approach(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-slug.md": WP_MD}, REGISTER)
        generate_ticket_markdown_drafts(ws)
        content = (ws / "ticket-drafts" / "TICKET-WP-001.md").read_text(encoding="utf-8")
        assert "Recommended Engineering Approach" in content

    def test_markdown_includes_evidence(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-slug.md": WP_MD}, REGISTER)
        generate_ticket_markdown_drafts(ws)
        content = (ws / "ticket-drafts" / "TICKET-WP-001.md").read_text(encoding="utf-8")
        assert "EVD-000138" in content

    def test_no_work_packages_returns_empty(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {})
        drafts, _ = generate_ticket_markdown_drafts(ws)
        assert drafts == []

    def test_handles_missing_finding_gracefully(self, tmp_path: Path) -> None:
        reg = {"findings": []}
        ws = _make_workspace(tmp_path, {"WP-001-slug.md": WP_MD}, reg)
        drafts, _ = generate_ticket_markdown_drafts(ws)
        assert len(drafts) == 1
        assert drafts[0].priority is None
        assert drafts[0].risk_score is None

    def test_stable_output_across_runs(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-slug.md": WP_MD}, REGISTER)
        drafts1, _ = generate_ticket_markdown_drafts(ws)
        content1 = (ws / "ticket-drafts" / "TICKET-WP-001.md").read_text(encoding="utf-8")
        drafts2, _ = generate_ticket_markdown_drafts(ws)
        content2 = (ws / "ticket-drafts" / "TICKET-WP-001.md").read_text(encoding="utf-8")
        assert content1 == content2
        assert drafts1[0].ticket_id == drafts2[0].ticket_id

    def test_does_not_mutate_debt_register(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-slug.md": WP_MD}, REGISTER)
        reg_path = ws / "debt-register.json"
        before = reg_path.read_text(encoding="utf-8")
        generate_ticket_markdown_drafts(ws)
        after = reg_path.read_text(encoding="utf-8")
        assert before == after

    def test_does_not_mutate_work_packages(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path, {"WP-001-slug.md": WP_MD}, REGISTER)
        wp_path = ws / "work-packages" / "WP-001-slug.md"
        before = wp_path.read_text(encoding="utf-8")
        generate_ticket_markdown_drafts(ws)
        after = wp_path.read_text(encoding="utf-8")
        assert before == after
