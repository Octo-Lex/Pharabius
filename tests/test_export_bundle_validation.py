"""Tests for export bundle manifest validation (W44-S01)."""

from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.export_bundle_validation import (
    validate_export_bundle_manifest,
)

VALID_MANIFEST = {
    "schema_version": "1.0",
    "tool_version": "1.7.1",
    "generated_at": "2026-05-23T00:00:00Z",
    "source_ticket_drafts": ".ai-debt/ticket-drafts/ticket-drafts.json",
    "summary": {"total_bundles": 1, "total_artifacts": 2, "total_tickets": 1},
    "artifacts": [
        {
            "tracker": "jira",
            "format": "markdown",
            "relative_path": "jira/jira-ticket-drafts.md",
            "ticket_count": 1,
        },
        {
            "tracker": "jira",
            "format": "csv",
            "relative_path": "jira/jira-ticket-drafts.csv",
            "ticket_count": 1,
        },
    ],
}


def _make_bundle_dir(tmp_path: Path, manifest: dict | None = None) -> Path:
    d = tmp_path / ".ai-debt" / "export-bundles"
    d.mkdir(parents=True)
    if manifest is not None:
        (d / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        # Create referenced artifact files
        for art in manifest.get("artifacts", []):
            rel = art.get("relative_path", "")
            if rel:
                p = d / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("content", encoding="utf-8")
        # Create README for tracker dirs
        for art in manifest.get("artifacts", []):
            tracker = art.get("tracker", "")
            if tracker:
                readme = d / tracker / "README.md"
                if not readme.exists():
                    readme.write_text("# README\n", encoding="utf-8")
    return d


class TestValidManifest:
    def test_valid_manifest_passes(self, tmp_path: Path) -> None:
        d = _make_bundle_dir(tmp_path, VALID_MANIFEST)
        result = validate_export_bundle_manifest(d)
        assert result.valid
        assert len(result.errors) == 0


class TestMissingManifest:
    def test_missing_manifest(self, tmp_path: Path) -> None:
        d = tmp_path / ".ai-debt" / "export-bundles"
        d.mkdir(parents=True)
        result = validate_export_bundle_manifest(d)
        assert not result.valid
        assert any(e.code == "missing_manifest" for e in result.errors)


class TestInvalidManifest:
    def test_invalid_json(self, tmp_path: Path) -> None:
        d = tmp_path / ".ai-debt" / "export-bundles"
        d.mkdir(parents=True)
        (d / "manifest.json").write_text("{ not valid json", encoding="utf-8")
        result = validate_export_bundle_manifest(d)
        assert not result.valid
        assert any(e.code == "invalid_manifest_json" for e in result.errors)

    def test_not_a_dict(self, tmp_path: Path) -> None:
        d = tmp_path / ".ai-debt" / "export-bundles"
        d.mkdir(parents=True)
        (d / "manifest.json").write_text("[]", encoding="utf-8")
        result = validate_export_bundle_manifest(d)
        assert not result.valid
        assert any(e.code == "invalid_manifest_structure" for e in result.errors)

    def test_unsupported_schema_version(self, tmp_path: Path) -> None:
        m = {**VALID_MANIFEST, "schema_version": "2.0"}
        d = _make_bundle_dir(tmp_path, m)
        result = validate_export_bundle_manifest(d)
        assert any(e.code == "unsupported_schema_version" for e in result.errors)


class TestUnsupportedTracker:
    def test_unsupported_tracker_name(self, tmp_path: Path) -> None:
        m = {
            **VALID_MANIFEST,
            "artifacts": [
                {
                    "tracker": "asana",
                    "format": "markdown",
                    "relative_path": "asana/asana.md",
                    "ticket_count": 1,
                }
            ],
            "summary": {"total_bundles": 1, "total_artifacts": 1, "total_tickets": 1},
        }
        d = _make_bundle_dir(tmp_path, m)
        result = validate_export_bundle_manifest(d)
        assert any(e.code == "unsupported_tracker" for e in result.errors)


class TestDuplicatePath:
    def test_duplicate_artifact_path(self, tmp_path: Path) -> None:
        m = {
            **VALID_MANIFEST,
            "artifacts": [
                {
                    "tracker": "jira",
                    "format": "markdown",
                    "relative_path": "jira/dup.md",
                    "ticket_count": 1,
                },
                {
                    "tracker": "jira",
                    "format": "csv",
                    "relative_path": "jira/dup.md",
                    "ticket_count": 1,
                },
            ],
            "summary": {"total_bundles": 1, "total_artifacts": 2, "total_tickets": 2},
        }
        d = _make_bundle_dir(tmp_path, m)
        result = validate_export_bundle_manifest(d)
        assert any(e.code == "duplicate_artifact_path" for e in result.errors)


class TestMissingArtifactFile:
    def test_missing_referenced_file(self, tmp_path: Path) -> None:
        m = {
            **VALID_MANIFEST,
            "artifacts": [
                {
                    "tracker": "jira",
                    "format": "markdown",
                    "relative_path": "jira/does-not-exist.md",
                    "ticket_count": 1,
                }
            ],
            "summary": {"total_bundles": 1, "total_artifacts": 1, "total_tickets": 1},
        }
        d = tmp_path / ".ai-debt" / "export-bundles"
        d.mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
        # Don't create the referenced file
        result = validate_export_bundle_manifest(d)
        assert any(e.code == "missing_artifact_file" for e in result.errors)


class TestWarnings:
    def test_missing_tracker_readme(self, tmp_path: Path) -> None:
        m = {
            **VALID_MANIFEST,
            "artifacts": [
                {
                    "tracker": "jira",
                    "format": "markdown",
                    "relative_path": "jira/jira.md",
                    "ticket_count": 1,
                }
            ],
            "summary": {"total_bundles": 1, "total_artifacts": 1, "total_tickets": 1},
        }
        d = tmp_path / ".ai-debt" / "export-bundles"
        d.mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
        jira_dir = d / "jira"
        jira_dir.mkdir()
        (jira_dir / "jira.md").write_text("content", encoding="utf-8")
        # No README.md
        result = validate_export_bundle_manifest(d)
        assert any(w.code == "missing_tracker_readme" for w in result.warnings)

    def test_artifact_count_mismatch(self, tmp_path: Path) -> None:
        m = {
            **VALID_MANIFEST,
            "summary": {"total_bundles": 1, "total_artifacts": 99, "total_tickets": 1},
        }
        d = _make_bundle_dir(tmp_path, m)
        result = validate_export_bundle_manifest(d)
        assert any(w.code == "artifact_count_mismatch" for w in result.warnings)


class TestDeterminism:
    def test_deterministic_output(self, tmp_path: Path) -> None:
        d = _make_bundle_dir(tmp_path, VALID_MANIFEST)
        r1 = validate_export_bundle_manifest(d)
        r2 = validate_export_bundle_manifest(d)
        assert r1.valid == r2.valid
        assert len(r1.errors) == len(r2.errors)
        assert len(r1.warnings) == len(r2.warnings)


class TestNoCanonicalMutation:
    def test_does_not_mutate_manifest(self, tmp_path: Path) -> None:
        d = _make_bundle_dir(tmp_path, VALID_MANIFEST)
        before = (d / "manifest.json").read_text(encoding="utf-8")
        validate_export_bundle_manifest(d)
        assert (d / "manifest.json").read_text(encoding="utf-8") == before

    def test_does_not_mutate_debt_register(self, tmp_path: Path) -> None:
        ws = tmp_path / ".ai-debt"
        ws.mkdir(parents=True)
        reg = ws / "debt-register.json"
        reg.write_text('{"findings": []}', encoding="utf-8")
        d = _make_bundle_dir(tmp_path, VALID_MANIFEST)
        before = reg.read_text(encoding="utf-8")
        validate_export_bundle_manifest(d)
        assert reg.read_text(encoding="utf-8") == before
