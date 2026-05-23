"""Tests for export bundle schema and core (W43-S01)."""

from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.export_bundles import (
    build_manifest_from_artifacts,
    export_bundles_root,
    tracker_output_dir,
    tracker_slug,
    write_export_bundle_manifest,
)
from pharabius.schemas.export_bundles import (
    ExportBundleArtifact,
    ExportBundleFormat,
    ExportBundleManifest,
    TrackerKind,
)


class TestTrackerKind:
    def test_jira(self) -> None:
        assert TrackerKind.JIRA.value == "jira"

    def test_linear(self) -> None:
        assert TrackerKind.LINEAR.value == "linear"

    def test_github_issues(self) -> None:
        assert TrackerKind.GITHUB_ISSUES.value == "github-issues"

    def test_azure_devops(self) -> None:
        assert TrackerKind.AZURE_DEVOPS.value == "azure-devops"

    def test_all_four_trackers(self) -> None:
        assert len(TrackerKind) == 4


class TestExportBundleFormat:
    def test_markdown(self) -> None:
        assert ExportBundleFormat.MARKDOWN.value == "markdown"

    def test_csv(self) -> None:
        assert ExportBundleFormat.CSV.value == "csv"

    def test_yaml(self) -> None:
        assert ExportBundleFormat.YAML.value == "yaml"

    def test_json(self) -> None:
        assert ExportBundleFormat.JSON.value == "json"

    def test_all_four_formats(self) -> None:
        assert len(ExportBundleFormat) == 4


class TestExportBundleManifestSchema:
    def test_default_schema_version(self) -> None:
        m = ExportBundleManifest()
        assert m.schema_version == "1.0"

    def test_empty_manifest(self) -> None:
        m = ExportBundleManifest()
        assert m.artifacts == []
        assert m.summary.total_bundles == 0
        assert m.summary.total_artifacts == 0
        assert m.summary.total_tickets == 0

    def test_manifest_with_artifacts(self) -> None:
        art = ExportBundleArtifact(
            tracker=TrackerKind.JIRA,
            format=ExportBundleFormat.CSV,
            relative_path="jira/jira-ticket-drafts.csv",
            description="Jira CSV export",
            ticket_count=3,
        )
        m = build_manifest_from_artifacts(
            [art], tool_version="1.7.0", generated_at="2026-05-23T00:00:00Z"
        )
        assert len(m.artifacts) == 1
        assert m.summary.total_tickets == 3
        assert m.summary.total_bundles == 1

    def test_serialization_roundtrip(self) -> None:
        art = ExportBundleArtifact(
            tracker=TrackerKind.LINEAR,
            format=ExportBundleFormat.MARKDOWN,
            relative_path="linear/linear-ticket-drafts.md",
            ticket_count=2,
        )
        m = ExportBundleManifest(artifacts=[art])
        data = json.loads(m.model_dump_json())
        m2 = ExportBundleManifest.model_validate(data)
        assert m2.schema_version == m.schema_version
        assert len(m2.artifacts) == 1
        assert m2.artifacts[0].tracker == TrackerKind.LINEAR

    def test_source_ticket_drafts_default(self) -> None:
        m = ExportBundleManifest()
        assert m.source_ticket_drafts == ".ai-debt/ticket-drafts/ticket-drafts.json"


class TestCoreHelpers:
    def test_tracker_slug(self) -> None:
        assert tracker_slug(TrackerKind.JIRA) == "jira"
        assert tracker_slug(TrackerKind.GITHUB_ISSUES) == "github-issues"

    def test_export_bundles_root(self, tmp_path: Path) -> None:
        workspace = tmp_path / ".ai-debt"
        result = export_bundles_root(workspace)
        assert result == workspace / "export-bundles"

    def test_tracker_output_dir(self, tmp_path: Path) -> None:
        workspace = tmp_path / ".ai-debt"
        result = tracker_output_dir(workspace, TrackerKind.JIRA)
        assert result == workspace / "export-bundles" / "jira"


class TestManifestWriter:
    def test_writes_manifest_json(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "export-bundles"
        m = ExportBundleManifest(tool_version="1.7.0")
        path = write_export_bundle_manifest(output_dir, m)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.0"
        assert data["tool_version"] == "1.7.0"

    def test_creates_directory(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "nested" / "export-bundles"
        m = ExportBundleManifest()
        path = write_export_bundle_manifest(output_dir, m)
        assert output_dir.exists()
        assert path.exists()

    def test_deterministic_output(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "export-bundles"
        m = ExportBundleManifest(tool_version="1.7.0", generated_at="2026-05-23T00:00:00Z")
        path1 = write_export_bundle_manifest(output_dir, m)
        content1 = path1.read_text(encoding="utf-8")
        path2 = write_export_bundle_manifest(output_dir, m)
        content2 = path2.read_text(encoding="utf-8")
        assert content1 == content2


class TestBuildManifest:
    def test_build_from_empty(self) -> None:
        m = build_manifest_from_artifacts([])
        assert m.summary.total_bundles == 0
        assert m.summary.total_artifacts == 0

    def test_build_from_artifacts(self) -> None:
        arts = [
            ExportBundleArtifact(
                tracker=TrackerKind.JIRA,
                format=ExportBundleFormat.CSV,
                relative_path="jira/jira-ticket-drafts.csv",
                ticket_count=3,
            ),
            ExportBundleArtifact(
                tracker=TrackerKind.JIRA,
                format=ExportBundleFormat.MARKDOWN,
                relative_path="jira/jira-ticket-drafts.md",
                ticket_count=3,
            ),
            ExportBundleArtifact(
                tracker=TrackerKind.LINEAR,
                format=ExportBundleFormat.CSV,
                relative_path="linear/linear-ticket-drafts.csv",
                ticket_count=2,
            ),
        ]
        m = build_manifest_from_artifacts(arts, tool_version="1.7.0")
        assert m.summary.total_bundles == 2  # Jira + Linear
        assert m.summary.total_artifacts == 3
        assert m.summary.total_tickets == 8  # 3 + 3 + 2
        assert len(m.summary.trackers) == 2


class TestNoCanonicalMutation:
    def test_manifest_writer_does_not_mutate_debt_register(self, tmp_path: Path) -> None:
        workspace = tmp_path / ".ai-debt"
        workspace.mkdir()
        reg = workspace / "debt-register.json"
        reg.write_text('{"findings": []}', encoding="utf-8")
        output_dir = workspace / "export-bundles"
        m = ExportBundleManifest()
        write_export_bundle_manifest(output_dir, m)
        assert reg.read_text(encoding="utf-8") == '{"findings": []}'


class TestExampleManifest:
    def test_example_manifest_validates(self) -> None:
        import json
        from pathlib import Path

        example = Path("docs/examples/export-bundles/manifest.example.json")
        if not example.exists():
            return
        data = json.loads(example.read_text(encoding="utf-8"))
        m = ExportBundleManifest.model_validate(data)
        assert m.schema_version == "1.0"
        assert len(m.artifacts) == 8
        assert len(m.summary.trackers) == 4

    def test_example_github_yaml_parses(self) -> None:
        from pathlib import Path

        example = Path("docs/examples/export-bundles/TICKET-WP-001.example.yaml")
        if not example.exists():
            return
        content = example.read_text(encoding="utf-8")
        assert "schema_version: '1.0'" in content
        assert "title:" in content
        assert "body: |" in content
        assert "assignee" not in content
        assert "milestone" not in content
