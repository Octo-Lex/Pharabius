"""Tests for Jira export bundle generator (W43-S02)."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from pharabius.core.export_bundles_jira import generate_jira_export_bundle
from pharabius.schemas.export_bundles import ExportBundleFormat, TrackerKind
from pharabius.schemas.tickets import (
    TicketDraft,
    TicketDraftIndex,
    TicketDraftSourceArtifacts,
)

SA = TicketDraftSourceArtifacts(
    debt_register=".ai-debt/debt-register.json",
    work_packages_dir=".ai-debt/work-packages",
)

DRAFTS = [
    TicketDraft(
        ticket_id="TICKET-WP-001",
        title="Fix authentication boundary",
        source_type="work_package",
        source_id="WP-001",
        artifact_path=".ai-debt/ticket-drafts/TICKET-WP-001.md",
        linked_debt_items=["TD-ARCH-001"],
        categories=["TD-ARCH"],
        priority="High",
        risk_score=24,
        review_decision="accepted",
        status="draft",
        labels=["TD-ARCH", "pharabius"],
        external_system=None,
        external_id=None,
        content_hash="sha256:abc",
        body_markdown="Objective: Fix the auth boundary.",
    )
]


def _make_ticket_dir(tmp_path: Path, drafts: list[TicketDraft] | None = None) -> Path:
    td = tmp_path / ".ai-debt" / "ticket-drafts"
    td.mkdir(parents=True)
    idx = TicketDraftIndex(
        schema_version="1.0",
        tool_version="1.7.0",
        generated_at="2026-05-23T00:00:00Z",
        repository="test-repo",
        source_artifacts=SA,
        drafts=drafts if drafts is not None else DRAFTS,
    )
    (td / "ticket-drafts.json").write_text(idx.model_dump_json(indent=2), encoding="utf-8")
    return td


def _csv_rows(path: Path) -> list[list[str]]:
    content = path.read_text(encoding="utf-8")
    return [r for r in csv.reader(io.StringIO(content)) if r]


class TestJiraMarkdown:
    def test_generates_markdown(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "jira"
        generate_jira_export_bundle(td, out)
        md = (out / "jira-ticket-drafts.md").read_text(encoding="utf-8")
        assert "# Jira Ticket Draft Export" in md
        assert "TICKET-WP-001" in md

    def test_markdown_includes_work_package(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "jira"
        generate_jira_export_bundle(td, out)
        md = (out / "jira-ticket-drafts.md").read_text(encoding="utf-8")
        assert "WP-001" in md

    def test_markdown_includes_linked_findings(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "jira"
        generate_jira_export_bundle(td, out)
        md = (out / "jira-ticket-drafts.md").read_text(encoding="utf-8")
        assert "TD-ARCH-001" in md

    def test_markdown_includes_completeness(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "jira"
        generate_jira_export_bundle(td, out)
        md = (out / "jira-ticket-drafts.md").read_text(encoding="utf-8")
        assert "Completeness" in md

    def test_markdown_states_local_only(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "jira"
        generate_jira_export_bundle(td, out)
        md = (out / "jira-ticket-drafts.md").read_text(encoding="utf-8")
        assert "Repository-local" in md


class TestJiraCSV:
    def test_generates_csv_with_header(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "jira"
        generate_jira_export_bundle(td, out)
        rows = _csv_rows(out / "jira-ticket-drafts.csv")
        assert rows[0][0] == "Summary"
        assert len(rows) == 2  # header + 1 draft

    def test_csv_required_columns(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "jira"
        generate_jira_export_bundle(td, out)
        rows = _csv_rows(out / "jira-ticket-drafts.csv")
        assert "Summary" in rows[0]
        assert "Priority" in rows[0]
        assert "Labels" in rows[0]

    def test_csv_escapes_commas(self, tmp_path: Path) -> None:
        draft = TicketDraft(
            ticket_id="TICKET-WP-002",
            title="Fix A, B, and C",
            source_type="work_package",
            source_id="WP-002",
            artifact_path=".ai-debt/ticket-drafts/TICKET-WP-002.md",
            status="draft",
            labels=["pharabius"],
            external_system=None,
            external_id=None,
            content_hash="sha256:abc",
        )
        td = _make_ticket_dir(tmp_path, [draft])
        out = tmp_path / ".ai-debt" / "export-bundles" / "jira"
        generate_jira_export_bundle(td, out)
        rows = _csv_rows(out / "jira-ticket-drafts.csv")
        assert rows[1][0] == "Fix A, B, and C"

    def test_csv_escapes_quotes(self, tmp_path: Path) -> None:
        draft = TicketDraft(
            ticket_id="TICKET-WP-003",
            title='Fix "quoted" title',
            source_type="work_package",
            source_id="WP-003",
            artifact_path=".ai-debt/ticket-drafts/TICKET-WP-003.md",
            status="draft",
            labels=["pharabius"],
            external_system=None,
            external_id=None,
            content_hash="sha256:abc",
        )
        td = _make_ticket_dir(tmp_path, [draft])
        out = tmp_path / ".ai-debt" / "export-bundles" / "jira"
        generate_jira_export_bundle(td, out)
        rows = _csv_rows(out / "jira-ticket-drafts.csv")
        assert rows[1][0] == 'Fix "quoted" title'


class TestJiraReadme:
    def test_readme_exists(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "jira"
        generate_jira_export_bundle(td, out)
        assert (out / "README.md").exists()

    def test_readme_states_no_api(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "jira"
        generate_jira_export_bundle(td, out)
        readme = (out / "README.md").read_text(encoding="utf-8")
        lower = readme.lower()
        assert "does not call" in lower
        assert "jira" in lower


class TestJiraManifest:
    def test_artifacts_returned(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "jira"
        arts = generate_jira_export_bundle(td, out)
        assert len(arts) == 2
        assert all(a.tracker == TrackerKind.JIRA for a in arts)
        formats = {a.format for a in arts}
        assert ExportBundleFormat.MARKDOWN in formats
        assert ExportBundleFormat.CSV in formats

    def test_ticket_count(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "jira"
        arts = generate_jira_export_bundle(td, out)
        assert arts[0].ticket_count == 1


class TestJiraEdgeCases:
    def test_empty_ticket_dir(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path, [])
        out = tmp_path / ".ai-debt" / "export-bundles" / "jira"
        arts = generate_jira_export_bundle(td, out)
        assert all(a.ticket_count == 0 for a in arts)

    def test_missing_index(self, tmp_path: Path) -> None:
        td = tmp_path / ".ai-debt" / "ticket-drafts"
        td.mkdir(parents=True)
        out = tmp_path / ".ai-debt" / "export-bundles" / "jira"
        arts = generate_jira_export_bundle(td, out)
        assert all(a.ticket_count == 0 for a in arts)

    def test_no_canonical_mutation(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        index_path = td / "ticket-drafts.json"
        before = index_path.read_text(encoding="utf-8")
        out = tmp_path / ".ai-debt" / "export-bundles" / "jira"
        generate_jira_export_bundle(td, out)
        assert index_path.read_text(encoding="utf-8") == before
