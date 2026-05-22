"""Tests for ai-debt tickets CLI command (W41-S05)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from pharabius.cli import app

runner = CliRunner()

WP_MD = """# Work Package: WP-001 Fix dependency risk

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


def _make_repo(tmp_path: Path) -> Path:
    ws = tmp_path / ".ai-debt"
    ws.mkdir()
    wp_dir = ws / "work-packages"
    wp_dir.mkdir()
    (wp_dir / "WP-001-slug.md").write_text(WP_MD, encoding="utf-8")
    (ws / "debt-register.json").write_text(json.dumps(REGISTER), encoding="utf-8")
    return tmp_path


class TestTicketsHelp:
    def test_help_succeeds(self) -> None:
        result = runner.invoke(app, ["tickets", "--help"])
        assert result.exit_code == 0
        assert "ticket" in result.output.lower()


class TestTicketsGeneration:
    def test_generates_artifacts(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        result = runner.invoke(app, ["tickets", "-r", str(repo)])
        assert result.exit_code == 0
        assert (repo / ".ai-debt" / "ticket-drafts" / "TICKET-WP-001.md").exists()
        assert (repo / ".ai-debt" / "ticket-drafts" / "ticket-drafts.json").exists()
        assert (repo / ".ai-debt" / "reports" / "ticket-draft-summary.md").exists()

    def test_output_states_zero_external(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        result = runner.invoke(app, ["tickets", "-r", str(repo)])
        assert result.exit_code == 0
        assert "External tickets created: 0" in result.output

    def test_no_workspace_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["tickets", "-r", str(tmp_path)])
        assert result.exit_code == 1
        assert "No .ai-debt workspace" in result.output

    def test_no_work_packages_fails(self, tmp_path: Path) -> None:
        ws = tmp_path / ".ai-debt"
        ws.mkdir()
        result = runner.invoke(app, ["tickets", "-r", str(tmp_path)])
        assert result.exit_code == 1
        assert "No work packages found" in result.output

    def test_existing_without_force(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        # First run
        result = runner.invoke(app, ["tickets", "-r", str(repo)])
        assert result.exit_code == 0
        # Second run without force
        result = runner.invoke(app, ["tickets", "-r", str(repo)])
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_force_overwrites(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        result = runner.invoke(app, ["tickets", "-r", str(repo)])
        assert result.exit_code == 0
        result = runner.invoke(app, ["tickets", "-r", str(repo), "--force"])
        assert result.exit_code == 0

    def test_include_deferred(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        review_dir = repo / ".ai-debt" / "review"
        review_dir.mkdir()
        (review_dir / "decisions.json").write_text(
            json.dumps({"decisions": [{"finding_id": "TD-DEP-001", "status": "deferred"}]}),
            encoding="utf-8",
        )
        # Default: excluded
        result = runner.invoke(app, ["tickets", "-r", str(repo)])
        assert result.exit_code == 0
        assert "Excluded by review: 1" in result.output
        # With flag: included
        result = runner.invoke(app, ["tickets", "-r", str(repo), "--force", "--include-deferred"])
        assert result.exit_code == 0
        assert "Markdown drafts: 1" in result.output

    def test_does_not_mutate_debt_register(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        reg_before = (repo / ".ai-debt" / "debt-register.json").read_text(encoding="utf-8")
        runner.invoke(app, ["tickets", "-r", str(repo)])
        reg_after = (repo / ".ai-debt" / "debt-register.json").read_text(encoding="utf-8")
        assert reg_before == reg_after

    def test_does_not_mutate_work_packages(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        wp_before = (repo / ".ai-debt" / "work-packages" / "WP-001-slug.md").read_text(
            encoding="utf-8"
        )
        runner.invoke(app, ["tickets", "-r", str(repo)])
        wp_after = (repo / ".ai-debt" / "work-packages" / "WP-001-slug.md").read_text(
            encoding="utf-8"
        )
        assert wp_before == wp_after
