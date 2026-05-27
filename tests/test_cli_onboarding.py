"""Tests for CLI onboarding and first-run diagnostics (W50-S02)."""

from __future__ import annotations

from pathlib import Path

from pharabius.cli import app
import typer.testing

runner = typer.testing.CliRunner()


class TestDoctorCommand:
    def test_no_workspace_recommends_init(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["doctor", "-r", str(tmp_path)])
        assert result.exit_code == 0
        assert "needs_init" in result.output
        assert "ai-debt init" in result.output

    def test_with_workspace_shows_status(self, tmp_path: Path) -> None:
        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        # Write required artifacts
        for name, content in {
            "evidence.json": '{"evidence":[]}',
            "debt-register.json": '{"findings":[]}',
            "project-profile.json": '{}',
            "debt-register.md": "# Register",
            "reports/foundation-audit-report.md": "# Report",
            "remediation-roadmap.md": "# Roadmap",
            "handoff-summary.md": "# Handoff",
            "review/decisions.json": '{"decisions":[]}',
            "ticket-drafts/ticket-drafts.json": '{"drafts":[]}',
        }.items():
            p = ai / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)

        result = runner.invoke(app, ["doctor", "-r", str(tmp_path)])
        assert result.exit_code == 0
        assert "Status:" in result.output

    def test_missing_required_shows_blocking(self, tmp_path: Path) -> None:
        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        # Only some required artifacts
        (ai / "evidence.json").write_text("{}")
        result = runner.invoke(app, ["doctor", "-r", str(tmp_path)])
        assert result.exit_code == 0
        assert "Blocking" in result.output or "blocking" in result.output.lower()

    def test_doctor_is_read_only(self, tmp_path: Path) -> None:
        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        before = set(ai.iterdir()) if ai.exists() else set()
        runner.invoke(app, ["doctor", "-r", str(tmp_path)])
        after = set(ai.iterdir()) if ai.exists() else set()
        assert before == after

    def test_recommends_next_command(self, tmp_path: Path) -> None:
        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        result = runner.invoke(app, ["doctor", "-r", str(tmp_path)])
        assert result.exit_code == 0
        assert "Next recommended" in result.output
