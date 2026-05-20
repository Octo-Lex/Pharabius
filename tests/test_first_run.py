"""First-run smoke test — verifies the full CLI workflow on a tiny fixture repo.

Uses a minimal temporary repository with one source file and one dependency
manifest. No network, no credentials, no real provider.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pharabius.cli import app

runner = CliRunner()


@pytest.fixture()
def tiny_repo(tmp_path: Path) -> Path:
    """Create a minimal repository for first-run testing."""
    # Source file
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("def hello():\n    print('hello')\n", encoding="utf-8")
    (src / "__init__.py").write_text("", encoding="utf-8")

    # Dependency manifest
    (tmp_path / "requirements.txt").write_text("flask==2.0\n", encoding="utf-8")

    # README
    (tmp_path / "README.md").write_text("# Test Project\n", encoding="utf-8")
    return tmp_path


class TestFirstRunWorkflow:
    """End-to-end first-run workflow on a tiny fixture repo."""

    def test_init_creates_workspace(self, tiny_repo: Path) -> None:
        result = runner.invoke(app, ["init", "-r", str(tiny_repo)])
        assert result.exit_code == 0
        assert (tiny_repo / ".ai-debt").exists()
        assert (tiny_repo / ".ai-debt" / "config.yaml").exists()

    def test_scan_produces_evidence(self, tiny_repo: Path) -> None:
        runner.invoke(app, ["init", "-r", str(tiny_repo)])
        result = runner.invoke(app, ["scan", "-r", str(tiny_repo)])
        assert result.exit_code == 0
        ev_path = tiny_repo / ".ai-debt" / "evidence.json"
        assert ev_path.exists()
        evidence = json.loads(ev_path.read_text())
        assert len(evidence.get("evidence", [])) > 0

    def test_analyze_produces_register(self, tiny_repo: Path) -> None:
        runner.invoke(app, ["init", "-r", str(tiny_repo)])
        runner.invoke(app, ["scan", "-r", str(tiny_repo)])
        result = runner.invoke(app, ["analyze", "--no-ai", "-r", str(tiny_repo)])
        assert result.exit_code == 0
        reg_path = tiny_repo / ".ai-debt" / "debt-register.json"
        assert reg_path.exists()
        register = json.loads(reg_path.read_text())
        assert "findings" in register
        # Tiny repo should produce at least TD-BUILD, TD-DOC, TD-DEP
        categories = {f["category"] for f in register["findings"]}
        assert "TD-DEP" in categories
        assert len(register["findings"]) > 0

    def test_report_produces_markdown_reports(self, tiny_repo: Path) -> None:
        runner.invoke(app, ["init", "-r", str(tiny_repo)])
        runner.invoke(app, ["scan", "-r", str(tiny_repo)])
        runner.invoke(app, ["analyze", "--no-ai", "-r", str(tiny_repo)])
        result = runner.invoke(app, ["report", "-r", str(tiny_repo)])
        assert result.exit_code == 0
        # Report produces these markdown files
        for expected in [
            "architecture-map.md",
            "dependency-health.md",
            "test-health.md",
            "security-exposure.md",
            "business-risk-proxy.md",
        ]:
            assert (tiny_repo / ".ai-debt" / expected).exists(), f"Missing {expected}"

    def test_plan_produces_roadmap_and_work_packages(self, tiny_repo: Path) -> None:
        runner.invoke(app, ["init", "-r", str(tiny_repo)])
        runner.invoke(app, ["scan", "-r", str(tiny_repo)])
        runner.invoke(app, ["analyze", "--no-ai", "-r", str(tiny_repo)])
        result = runner.invoke(app, ["plan", "-r", str(tiny_repo)])
        assert result.exit_code == 0
        # Plan produces these (NOT report)
        assert (tiny_repo / ".ai-debt" / "remediation-roadmap.md").exists()
        assert (tiny_repo / ".ai-debt" / "handoff-summary.md").exists()
        wp_dir = tiny_repo / ".ai-debt" / "work-packages"
        assert wp_dir.exists()

    def test_export_produces_all_formats(self, tiny_repo: Path) -> None:
        runner.invoke(app, ["init", "-r", str(tiny_repo)])
        runner.invoke(app, ["scan", "-r", str(tiny_repo)])
        runner.invoke(app, ["analyze", "--no-ai", "-r", str(tiny_repo)])
        result = runner.invoke(app, ["export", "--format", "all", "-r", str(tiny_repo)])
        assert result.exit_code == 0

    def test_status_exits_cleanly(self, tiny_repo: Path) -> None:
        runner.invoke(app, ["init", "-r", str(tiny_repo)])
        runner.invoke(app, ["scan", "-r", str(tiny_repo)])
        runner.invoke(app, ["analyze", "--no-ai", "-r", str(tiny_repo)])
        result = runner.invoke(app, ["status", "-r", str(tiny_repo)])
        assert result.exit_code == 0

    def test_enrich_mock_produces_sidecar(self, tiny_repo: Path) -> None:
        runner.invoke(app, ["init", "-r", str(tiny_repo)])
        runner.invoke(app, ["scan", "-r", str(tiny_repo)])
        runner.invoke(app, ["analyze", "--no-ai", "-r", str(tiny_repo)])
        result = runner.invoke(app, ["enrich", "--provider", "mock", "-r", str(tiny_repo)])
        assert result.exit_code == 0

    def test_ai_status_reads_sidecar(self, tiny_repo: Path) -> None:
        runner.invoke(app, ["init", "-r", str(tiny_repo)])
        runner.invoke(app, ["scan", "-r", str(tiny_repo)])
        runner.invoke(app, ["analyze", "--no-ai", "-r", str(tiny_repo)])
        runner.invoke(app, ["enrich", "--provider", "mock", "-r", str(tiny_repo)])
        result = runner.invoke(app, ["ai-status", "-r", str(tiny_repo)])
        assert result.exit_code == 0

    def test_help_lists_all_commands(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for cmd in [
            "init",
            "profile",
            "scan",
            "map",
            "graph",
            "analyze",
            "report",
            "plan",
            "verify",
            "status",
            "export",
            "enrich",
            "ai-status",
            "run",
            "review",
        ]:
            assert cmd in result.output, f"Command '{cmd}' not in --help"

    def test_version_flag(self) -> None:
        """--version prints version and exits 0."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "Pharabius" in result.output
        # Should contain a version-like pattern (e.g. 1.1.0 or 0.x.y)
        import re

        assert re.search(r"\d+\.\d+", result.output), f"No version in: {result.output}"

    def test_no_args_shows_help(self) -> None:
        """Running ai-debt with no args shows help."""
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Commands" in result.output
