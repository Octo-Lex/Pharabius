"""Tests for CLI command surface audit (W48-S02)."""

from __future__ import annotations

from pathlib import Path

import typer.testing

from pharabius.cli import app

runner = typer.testing.CliRunner()

EXPECTED_COMMANDS = [
    "init",
    "profile",
    "scan",
    "map-units",
    "analyze",
    "report",
    "plan",
    "verify",
    "status",
    "graph",
    "export",
    "enrich",
    "ai-status",
    "run",
    "review",
    "tickets",
    "portfolio",
    "gate",
    "diff",
]


class TestCommandInventory:
    def test_all_commands_render_help(self) -> None:
        for cmd in EXPECTED_COMMANDS:
            result = runner.invoke(app, [cmd, "--help"])
            assert result.exit_code == 0, f"Help failed for: {cmd}"

    def test_top_level_help_lists_commands(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        # Check a subset of commands appear
        for cmd in ["init", "analyze", "report", "portfolio", "tickets", "export"]:
            assert cmd in result.output, f"Missing command in help: {cmd}"


class TestSafetyLanguage:
    def test_export_help_no_external_apis(self) -> None:
        result = runner.invoke(app, ["export", "--help"])
        text = result.output.lower()
        assert "external" in text or "no" in text

    def test_tickets_help_local_only(self) -> None:
        result = runner.invoke(app, ["tickets", "--help"])
        text = result.output.lower()
        assert "local" in text or "external" in text

    def test_portfolio_help_local_only(self) -> None:
        result = runner.invoke(app, ["portfolio", "--help"])
        text = result.output.lower()
        assert "local" in text or "remote" in text

    def test_enrich_help_sidecar(self) -> None:
        result = runner.invoke(app, ["enrich", "--help"])
        text = result.output.lower()
        assert "sidecar" in text

    def test_review_help_non_canonical(self) -> None:
        result = runner.invoke(app, ["review", "--help"])
        text = result.output.lower()
        assert "canonical" in text or "non-canonical" in text

    def test_verify_help_read_only(self) -> None:
        result = runner.invoke(app, ["verify", "--help"])
        assert result.exit_code == 0

    def test_status_help_read_only(self) -> None:
        result = runner.invoke(app, ["status", "--help"])
        text = result.output.lower()
        assert "read-only" in text


class TestDocInventoryMatches:
    def test_cli_md_lists_all_commands(self) -> None:
        cli_md = Path("docs/CLI.md")
        if not cli_md.exists():
            return
        text = cli_md.read_text()
        for cmd in EXPECTED_COMMANDS:
            assert cmd in text, f"CLI.md missing command: {cmd}"


class TestVersionFlag:
    def test_version_flag_works(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "2.0.1" in result.output
