"""Tests for GitHub Issues export bundle generator (W43-S04)."""

from __future__ import annotations

from pathlib import Path

from pharabius.core.export_bundles_github import (
    generate_github_issues_export_bundle,
)
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
        title="Fix auth boundary",
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


class TestGitHubMarkdown:
    def test_generates_markdown(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "github-issues"
        generate_github_issues_export_bundle(td, out)
        md = (out / "github-issues-ticket-drafts.md").read_text(encoding="utf-8")
        assert "# GitHub Issues Ticket Draft Export" in md
        assert "TICKET-WP-001" in md

    def test_markdown_includes_labels(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "github-issues"
        generate_github_issues_export_bundle(td, out)
        md = (out / "github-issues-ticket-drafts.md").read_text(encoding="utf-8")
        assert "TD-ARCH" in md

    def test_markdown_includes_linked_findings(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "github-issues"
        generate_github_issues_export_bundle(td, out)
        md = (out / "github-issues-ticket-drafts.md").read_text(encoding="utf-8")
        assert "TD-ARCH-001" in md

    def test_markdown_states_local_only(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "github-issues"
        generate_github_issues_export_bundle(td, out)
        md = (out / "github-issues-ticket-drafts.md").read_text(encoding="utf-8")
        assert "Repository-local" in md


class TestGitHubYAML:
    def test_generates_yaml_per_issue(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "github-issues"
        generate_github_issues_export_bundle(td, out)
        yaml_path = out / "issues" / "TICKET-WP-001.yaml"
        assert yaml_path.exists()

    def test_yaml_includes_schema_version(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "github-issues"
        generate_github_issues_export_bundle(td, out)
        content = (out / "issues" / "TICKET-WP-001.yaml").read_text(encoding="utf-8")
        assert "schema_version: '1.0'" in content

    def test_yaml_includes_title(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "github-issues"
        generate_github_issues_export_bundle(td, out)
        content = (out / "issues" / "TICKET-WP-001.yaml").read_text(encoding="utf-8")
        assert "title: 'Fix auth boundary'" in content

    def test_yaml_includes_labels(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "github-issues"
        generate_github_issues_export_bundle(td, out)
        content = (out / "issues" / "TICKET-WP-001.yaml").read_text(encoding="utf-8")
        assert "TD-ARCH" in content

    def test_yaml_includes_body(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "github-issues"
        generate_github_issues_export_bundle(td, out)
        content = (out / "issues" / "TICKET-WP-001.yaml").read_text(encoding="utf-8")
        assert "body: |" in content
        assert "auth boundary" in content

    def test_yaml_no_assignee(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "github-issues"
        generate_github_issues_export_bundle(td, out)
        content = (out / "issues" / "TICKET-WP-001.yaml").read_text(encoding="utf-8")
        assert "assignee" not in content

    def test_yaml_no_milestone(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "github-issues"
        generate_github_issues_export_bundle(td, out)
        content = (out / "issues" / "TICKET-WP-001.yaml").read_text(encoding="utf-8")
        assert "milestone" not in content

    def test_yaml_escapes_single_quotes(self, tmp_path: Path) -> None:
        draft = TicketDraft(
            ticket_id="TICKET-WP-002",
            title="Fix O'Brien's bug",
            source_type="work_package",
            source_id="WP-002",
            artifact_path=".ai-debt/ticket-drafts/TICKET-WP-002.md",
            status="draft",
            labels=[],
            external_system=None,
            external_id=None,
            content_hash="sha256:abc",
        )
        td = _make_ticket_dir(tmp_path, [draft])
        out = tmp_path / ".ai-debt" / "export-bundles" / "github-issues"
        generate_github_issues_export_bundle(td, out)
        content = (out / "issues" / "TICKET-WP-002.yaml").read_text(encoding="utf-8")
        assert "O''Brien''s" in content


class TestGitHubReadme:
    def test_readme_exists(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "github-issues"
        generate_github_issues_export_bundle(td, out)
        assert (out / "README.md").exists()

    def test_readme_states_no_api(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "github-issues"
        generate_github_issues_export_bundle(td, out)
        readme = (out / "README.md").read_text(encoding="utf-8")
        lower = readme.lower()
        assert "does not call" in lower
        assert "github" in lower


class TestGitHubManifest:
    def test_artifacts_returned(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "github-issues"
        arts = generate_github_issues_export_bundle(td, out)
        assert len(arts) == 2  # Markdown + YAML
        assert all(a.tracker == TrackerKind.GITHUB_ISSUES for a in arts)
        formats = {a.format for a in arts}
        assert ExportBundleFormat.MARKDOWN in formats
        assert ExportBundleFormat.YAML in formats


class TestGitHubEdgeCases:
    def test_empty_ticket_dir(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path, [])
        out = tmp_path / ".ai-debt" / "export-bundles" / "github-issues"
        arts = generate_github_issues_export_bundle(td, out)
        assert arts[0].ticket_count == 0
        assert len(arts) == 1  # Only Markdown, no YAML for empty

    def test_missing_index(self, tmp_path: Path) -> None:
        td = tmp_path / ".ai-debt" / "ticket-drafts"
        td.mkdir(parents=True)
        out = tmp_path / ".ai-debt" / "export-bundles" / "github-issues"
        arts = generate_github_issues_export_bundle(td, out)
        assert all(a.ticket_count == 0 for a in arts)

    def test_no_canonical_mutation(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        index_path = td / "ticket-drafts.json"
        before = index_path.read_text(encoding="utf-8")
        out = tmp_path / ".ai-debt" / "export-bundles" / "github-issues"
        generate_github_issues_export_bundle(td, out)
        assert index_path.read_text(encoding="utf-8") == before
