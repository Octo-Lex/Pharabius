"""Tests for Azure DevOps export bundle generator (W43-S05)."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from pharabius.core.export_bundles_azure import (
    generate_azure_devops_export_bundle,
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


def _csv_rows(path: Path) -> list[list[str]]:
    return [r for r in csv.reader(io.StringIO(path.read_text(encoding="utf-8"))) if r]


class TestAzureMarkdown:
    def test_generates_markdown(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "azure-devops"
        generate_azure_devops_export_bundle(td, out)
        md = (out / "azure-devops-ticket-drafts.md").read_text(encoding="utf-8")
        assert "# Azure DevOps Ticket Draft Export" in md
        assert "TICKET-WP-001" in md

    def test_markdown_includes_work_item_type(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "azure-devops"
        generate_azure_devops_export_bundle(td, out)
        md = (out / "azure-devops-ticket-drafts.md").read_text(encoding="utf-8")
        assert "User Story" in md

    def test_markdown_uses_semicolon_tags(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "azure-devops"
        generate_azure_devops_export_bundle(td, out)
        md = (out / "azure-devops-ticket-drafts.md").read_text(encoding="utf-8")
        assert "TD-ARCH; pharabius" in md

    def test_markdown_states_local_only(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "azure-devops"
        generate_azure_devops_export_bundle(td, out)
        md = (out / "azure-devops-ticket-drafts.md").read_text(encoding="utf-8")
        assert "Repository-local" in md


class TestAzureCSV:
    def test_generates_csv(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "azure-devops"
        generate_azure_devops_export_bundle(td, out)
        rows = _csv_rows(out / "azure-devops-ticket-drafts.csv")
        assert rows[0][0] == "Title"
        assert len(rows) == 2

    def test_csv_work_item_type(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "azure-devops"
        generate_azure_devops_export_bundle(td, out)
        rows = _csv_rows(out / "azure-devops-ticket-drafts.csv")
        # Work Item Type is column 1
        assert rows[1][1] == "User Story"

    def test_csv_semicolon_tags(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "azure-devops"
        generate_azure_devops_export_bundle(td, out)
        rows = _csv_rows(out / "azure-devops-ticket-drafts.csv")
        # Tags is column 4
        assert "TD-ARCH" in rows[1][4]
        assert "pharabius" in rows[1][4]

    def test_csv_no_assigned_to(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "azure-devops"
        generate_azure_devops_export_bundle(td, out)
        rows = _csv_rows(out / "azure-devops-ticket-drafts.csv")
        header = rows[0]
        assert "Assigned To" not in header

    def test_csv_no_area_path(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "azure-devops"
        generate_azure_devops_export_bundle(td, out)
        rows = _csv_rows(out / "azure-devops-ticket-drafts.csv")
        header = rows[0]
        assert "Area Path" not in header

    def test_csv_no_iteration_path(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "azure-devops"
        generate_azure_devops_export_bundle(td, out)
        rows = _csv_rows(out / "azure-devops-ticket-drafts.csv")
        header = rows[0]
        assert "Iteration Path" not in header


class TestAzureReadme:
    def test_readme_exists(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "azure-devops"
        generate_azure_devops_export_bundle(td, out)
        assert (out / "README.md").exists()

    def test_readme_states_no_api(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "azure-devops"
        generate_azure_devops_export_bundle(td, out)
        readme = (out / "README.md").read_text(encoding="utf-8")
        lower = readme.lower()
        assert "does not call" in lower
        assert "azure" in lower


class TestAzureManifest:
    def test_artifacts_returned(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "azure-devops"
        arts = generate_azure_devops_export_bundle(td, out)
        assert len(arts) == 2
        assert all(a.tracker == TrackerKind.AZURE_DEVOPS for a in arts)
        formats = {a.format for a in arts}
        assert ExportBundleFormat.MARKDOWN in formats
        assert ExportBundleFormat.CSV in formats

    def test_ticket_count(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        out = tmp_path / ".ai-debt" / "export-bundles" / "azure-devops"
        arts = generate_azure_devops_export_bundle(td, out)
        assert arts[0].ticket_count == 1


class TestAzureEdgeCases:
    def test_empty_ticket_dir(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path, [])
        out = tmp_path / ".ai-debt" / "export-bundles" / "azure-devops"
        arts = generate_azure_devops_export_bundle(td, out)
        assert all(a.ticket_count == 0 for a in arts)

    def test_missing_index(self, tmp_path: Path) -> None:
        td = tmp_path / ".ai-debt" / "ticket-drafts"
        td.mkdir(parents=True)
        out = tmp_path / ".ai-debt" / "export-bundles" / "azure-devops"
        arts = generate_azure_devops_export_bundle(td, out)
        assert all(a.ticket_count == 0 for a in arts)

    def test_no_canonical_mutation(self, tmp_path: Path) -> None:
        td = _make_ticket_dir(tmp_path)
        index_path = td / "ticket-drafts.json"
        before = index_path.read_text(encoding="utf-8")
        out = tmp_path / ".ai-debt" / "export-bundles" / "azure-devops"
        generate_azure_devops_export_bundle(td, out)
        assert index_path.read_text(encoding="utf-8") == before
