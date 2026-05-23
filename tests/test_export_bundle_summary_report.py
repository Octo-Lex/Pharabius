"""Tests for export bundle summary report (W44-S05)."""

from __future__ import annotations

from pathlib import Path

from pharabius.core.export_bundle_reports import (
    render_export_bundle_summary,
    write_export_bundle_summary,
)
from pharabius.schemas.export_bundles import (
    ExportBundleArtifact,
    ExportBundleFormat,
    ExportBundleManifest,
    ExportBundleSummary,
    TrackerKind,
)

MANIFEST = ExportBundleManifest(
    schema_version="1.0",
    tool_version="1.7.1",
    generated_at="2026-05-23T00:00:00Z",
    repository="test-repo",
    summary=ExportBundleSummary(
        total_bundles=2,
        total_artifacts=4,
        total_tickets=6,
        trackers=[TrackerKind.JIRA, TrackerKind.LINEAR],
    ),
    artifacts=[
        ExportBundleArtifact(
            tracker=TrackerKind.JIRA,
            format=ExportBundleFormat.MARKDOWN,
            relative_path="jira/jira-ticket-drafts.md",
            ticket_count=3,
        ),
        ExportBundleArtifact(
            tracker=TrackerKind.JIRA,
            format=ExportBundleFormat.CSV,
            relative_path="jira/jira-ticket-drafts.csv",
            ticket_count=3,
        ),
        ExportBundleArtifact(
            tracker=TrackerKind.LINEAR,
            format=ExportBundleFormat.MARKDOWN,
            relative_path="linear/linear-ticket-drafts.md",
            ticket_count=3,
        ),
        ExportBundleArtifact(
            tracker=TrackerKind.LINEAR,
            format=ExportBundleFormat.CSV,
            relative_path="linear/linear-ticket-drafts.csv",
            ticket_count=3,
        ),
    ],
)


def _make_bundle_dir(tmp_path: Path) -> Path:
    d = tmp_path / ".ai-debt" / "export-bundles"
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(MANIFEST.model_dump_json(indent=2), encoding="utf-8")
    # Create artifact files and tracker dirs
    for art in MANIFEST.artifacts:
        p = d / art.relative_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("content", encoding="utf-8")
        readme = p.parent / "README.md"
        if not readme.exists():
            readme.write_text("# README\n", encoding="utf-8")
    return d


class TestSummaryReportStructure:
    def test_contains_generation_summary(self, tmp_path: Path) -> None:
        d = _make_bundle_dir(tmp_path)
        md = render_export_bundle_summary(d, MANIFEST)
        assert "## Generation Summary" in md

    def test_contains_artifacts_table(self, tmp_path: Path) -> None:
        d = _make_bundle_dir(tmp_path)
        md = render_export_bundle_summary(d, MANIFEST)
        assert "## Generated Artifacts" in md
        assert "jira" in md.lower()

    def test_contains_completeness(self, tmp_path: Path) -> None:
        d = _make_bundle_dir(tmp_path)
        md = render_export_bundle_summary(d, MANIFEST)
        assert "## Completeness" in md

    def test_contains_safety_boundary(self, tmp_path: Path) -> None:
        d = _make_bundle_dir(tmp_path)
        md = render_export_bundle_summary(d, MANIFEST)
        assert "## Safety Boundary" in md
        assert "No external tracker APIs were called" in md

    def test_contains_no_api_statement(self, tmp_path: Path) -> None:
        d = _make_bundle_dir(tmp_path)
        md = render_export_bundle_summary(d, MANIFEST)
        assert "no issues were created" in md.lower()

    def test_includes_tracker_names(self, tmp_path: Path) -> None:
        d = _make_bundle_dir(tmp_path)
        md = render_export_bundle_summary(d, MANIFEST)
        assert "jira" in md.lower()
        assert "linear" in md.lower()


class TestSummaryReportWriter:
    def test_writes_report(self, tmp_path: Path) -> None:
        d = _make_bundle_dir(tmp_path)
        reports = tmp_path / ".ai-debt" / "reports"
        path = write_export_bundle_summary(d, reports, MANIFEST)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "# Export Bundle Summary" in content

    def test_creates_reports_dir(self, tmp_path: Path) -> None:
        d = _make_bundle_dir(tmp_path)
        reports = tmp_path / ".ai-debt" / "reports"
        assert not reports.exists()
        write_export_bundle_summary(d, reports, MANIFEST)
        assert reports.exists()


class TestSummaryReportDeterminism:
    def test_deterministic_output(self, tmp_path: Path) -> None:
        d = _make_bundle_dir(tmp_path)
        md1 = render_export_bundle_summary(d, MANIFEST)
        md2 = render_export_bundle_summary(d, MANIFEST)
        assert md1 == md2


class TestSummaryReportNoMutation:
    def test_does_not_mutate_manifest(self, tmp_path: Path) -> None:
        d = _make_bundle_dir(tmp_path)
        before = (d / "manifest.json").read_text(encoding="utf-8")
        render_export_bundle_summary(d, MANIFEST)
        assert (d / "manifest.json").read_text(encoding="utf-8") == before
