"""Tests for context preview feature (v0.8.0)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from pharabius.ai.enricher import format_context_preview, preview_context
from pharabius.cli import app


def _make_repo(
    tmp_path: Path,
    *,
    n_findings: int = 2,
    evidence_per_finding: int = 2,
) -> Path:
    """Create a minimal repo with evidence and findings."""
    ai = tmp_path / ".ai-debt"
    ai.mkdir()

    ev_list = []
    for i in range(n_findings):
        for j in range(evidence_per_finding):
            ev_list.append(
                {
                    "evidence_id": f"EVD-{i:03d}-{j:03d}",
                    "type": "test",
                    "location": {"file": f"a{i}.py"},
                    "raw_observation": f"obs {i}-{j}",
                }
            )

    (ai / "evidence.json").write_text(
        json.dumps({"schema_version": "1.0", "evidence": ev_list}), encoding="utf-8"
    )

    findings = [
        {
            "id": f"TD-DEP-{i:03d}",
            "category": "TD-DEP",
            "title": f"Test finding {i}",
            "severity": "Medium",
            "evidence_ids": [f"EVD-{i:03d}-{j:03d}" for j in range(evidence_per_finding)],
            "analysis_unit_ids": [],
        }
        for i in range(n_findings)
    ]

    (ai / "debt-register.json").write_text(
        json.dumps({"schema_version": "1.0", "findings": findings}), encoding="utf-8"
    )

    return tmp_path


# ── Context preview unit tests ─────────────────────────────────────────


class TestContextPreview:
    """Tests for preview_context() and format_context_preview()."""

    def test_preview_assembles_context(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, n_findings=3)
        preview = preview_context(repo)
        assert len(preview["findings"]) == 3
        assert preview["no_provider_called"] is True
        assert preview["no_files_written"] is True

    def test_preview_does_not_write_files(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        files_before = set(repo.rglob("*"))
        preview_context(repo)
        files_after = set(repo.rglob("*"))
        assert files_before == files_after

    def test_preview_empty_register(self, tmp_path: Path) -> None:
        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        (ai / "evidence.json").write_text(
            json.dumps({"schema_version": "1.0", "evidence": []}), encoding="utf-8"
        )
        (ai / "debt-register.json").write_text(
            json.dumps({"schema_version": "1.0", "findings": []}), encoding="utf-8"
        )
        preview = preview_context(tmp_path)
        assert len(preview["findings"]) == 0
        assert preview["no_provider_called"] is True

    def test_preview_with_finding_id(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, n_findings=3)
        preview = preview_context(repo, finding_id="TD-DEP-001")
        assert len(preview["findings"]) == 1
        assert preview["findings"][0]["id"] == "TD-DEP-001"

    def test_preview_with_max_findings(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, n_findings=5)
        preview = preview_context(repo, max_findings=2)
        assert len(preview["findings"]) == 2

    def test_format_preview_readable(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, n_findings=2, evidence_per_finding=3)
        preview = preview_context(repo)
        text = format_context_preview(preview)
        assert "Context Preview" in text
        assert "No provider was called" in text
        assert "No files were written" in text
        assert "Findings selected: 2" in text
        assert "TD-DEP-000" in text
        assert "TD-DEP-001" in text
        assert "Evidence included:" in text
        assert "Evidence omitted:" in text

    def test_format_preview_shows_omissions(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, n_findings=1, evidence_per_finding=30)
        # Budget only allows 20 items
        preview = preview_context(repo)
        text = format_context_preview(preview)
        assert "Evidence omitted:" in text or "evidence omitted" in text.lower()

    def test_format_preview_shows_budget(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        preview = preview_context(repo)
        text = format_context_preview(preview)
        assert "Budget limit:" in text


# ── Context preview CLI tests ──────────────────────────────────────────


runner = CliRunner()


class TestContextPreviewCLI:
    """Tests for 'ai-debt enrich --context-preview' CLI command."""

    def test_context_preview_basic(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        result = runner.invoke(app, ["enrich", "--context-preview", "-r", str(repo)])
        assert result.exit_code == 0
        assert "Context Preview" in result.output
        assert "No provider was called" in result.output
        assert "No files were written" in result.output

    def test_context_preview_no_write(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        files_before = set(repo.rglob("*"))
        runner.invoke(app, ["enrich", "--context-preview", "-r", str(repo)])
        files_after = set(repo.rglob("*"))
        assert files_before == files_after

    def test_context_preview_works_without_provider(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        # No --provider flag — should work with default disabled
        result = runner.invoke(app, ["enrich", "--context-preview", "-r", str(repo)])
        assert result.exit_code == 0
        assert "Context Preview" in result.output

    def test_context_preview_works_with_mock_provider(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        result = runner.invoke(
            app, ["enrich", "--provider", "mock", "--context-preview", "-r", str(repo)]
        )
        assert result.exit_code == 0
        assert "Context Preview" in result.output
        # Should NOT call the mock provider
        assert "No provider was called" in result.output

    def test_context_preview_missing_register(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["enrich", "--context-preview", "-r", str(tmp_path)])
        assert result.exit_code == 1
        assert "debt-register.json not found" in result.output

    def test_context_preview_missing_evidence(self, tmp_path: Path) -> None:
        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        (ai / "debt-register.json").write_text(
            json.dumps({"schema_version": "1.0", "findings": []}), encoding="utf-8"
        )
        result = runner.invoke(app, ["enrich", "--context-preview", "-r", str(tmp_path)])
        assert result.exit_code == 1
        assert "evidence.json not found" in result.output

    def test_context_preview_unknown_finding_id(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        result = runner.invoke(
            app,
            [
                "enrich",
                "--context-preview",
                "--finding-id",
                "NONEXISTENT",
                "-r",
                str(repo),
            ],
        )
        assert result.exit_code == 1
        assert "NONEXISTENT" in result.output

    def test_context_preview_with_finding_id(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, n_findings=3)
        result = runner.invoke(
            app,
            [
                "enrich",
                "--context-preview",
                "--finding-id",
                "TD-DEP-001",
                "-r",
                str(repo),
            ],
        )
        assert result.exit_code == 0
        assert "TD-DEP-001" in result.output

    def test_context_preview_with_max_findings(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, n_findings=5)
        result = runner.invoke(
            app,
            ["enrich", "--context-preview", "--max-findings", "2", "-r", str(repo)],
        )
        assert result.exit_code == 0
        assert "Findings selected: 2" in result.output
