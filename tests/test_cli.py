from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from pharabius.cli import app

runner = CliRunner()


def test_init_command(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", "--repository-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Initialized Pharabius workspace" in result.stdout
    assert (tmp_path / ".ai-debt" / "config.yaml").exists()
    assert (tmp_path / ".ai-debt" / "project-profile.json").exists()


def test_init_command_force(tmp_path: Path) -> None:
    result1 = runner.invoke(app, ["init", "--repository-root", str(tmp_path)])
    assert result1.exit_code == 0

    result2 = runner.invoke(app, ["init", "--repository-root", str(tmp_path)])
    assert result2.exit_code == 0

    result3 = runner.invoke(app, ["init", "--repository-root", str(tmp_path), "--force"])
    assert result3.exit_code == 0
    assert "Initialized Pharabius workspace" in result3.stdout


def test_profile_command(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("flask\n", encoding="utf-8")

    result = runner.invoke(app, ["profile", "--repository-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "Generated repository profile" in result.stdout
    assert (tmp_path / ".ai-debt" / "project-profile.json").exists()


def test_scan_command_writes_evidence_json(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("import json\n", encoding="utf-8")

    init_result = runner.invoke(app, ["init", "--repository-root", str(tmp_path)])
    assert init_result.exit_code == 0

    scan_result = runner.invoke(app, ["scan", "--repository-root", str(tmp_path)])
    assert scan_result.exit_code == 0

    output_path = tmp_path / ".ai-debt" / "evidence.json"
    written = json.loads(output_path.read_text(encoding="utf-8"))

    assert output_path.exists()
    assert written["schema_version"] == "1.0"
    assert len(written["evidence"]) > 0
    assert "Generated evidence store" in scan_result.output


def test_analyze_command_writes_debt_register(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")

    init_result = runner.invoke(app, ["init", "--repository-root", str(tmp_path)])
    assert init_result.exit_code == 0

    scan_result = runner.invoke(app, ["scan", "--repository-root", str(tmp_path)])
    assert scan_result.exit_code == 0

    analyze_result = runner.invoke(
        app,
        ["analyze", "--no-ai", "--repository-root", str(tmp_path)],
    )
    assert analyze_result.exit_code == 0

    json_output = tmp_path / ".ai-debt" / "debt-register.json"
    markdown_output = tmp_path / ".ai-debt" / "debt-register.md"

    assert json_output.exists()
    assert markdown_output.exists()
    assert "Generated debt register" in analyze_result.output


def test_report_command_writes_reports(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")

    init_result = runner.invoke(app, ["init", "--repository-root", str(tmp_path)])
    assert init_result.exit_code == 0

    profile_result = runner.invoke(
        app,
        ["profile", "--repository-root", str(tmp_path)],
    )
    assert profile_result.exit_code == 0

    scan_result = runner.invoke(app, ["scan", "--repository-root", str(tmp_path)])
    assert scan_result.exit_code == 0

    analyze_result = runner.invoke(
        app,
        ["analyze", "--no-ai", "--repository-root", str(tmp_path)],
    )
    assert analyze_result.exit_code == 0

    report_result = runner.invoke(
        app,
        ["report", "--repository-root", str(tmp_path)],
    )
    assert report_result.exit_code == 0

    assert (tmp_path / ".ai-debt" / "architecture-map.md").exists()
    assert (tmp_path / ".ai-debt" / "dependency-health.md").exists()
    assert (tmp_path / ".ai-debt" / "test-health.md").exists()
    assert (tmp_path / ".ai-debt" / "security-exposure.md").exists()
    assert (tmp_path / ".ai-debt" / "business-risk-proxy.md").exists()
    assert (tmp_path / ".ai-debt" / "reports" / "foundation-audit-report.md").exists()
    assert "Generated reports" in report_result.output


def test_plan_command_writes_planning_artifacts(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"dependencies":{"express":"^4.0.0"}}',
        encoding="utf-8",
    )

    init_result = runner.invoke(app, ["init", "--repository-root", str(tmp_path)])
    assert init_result.exit_code == 0

    profile_result = runner.invoke(
        app,
        ["profile", "--repository-root", str(tmp_path)],
    )
    assert profile_result.exit_code == 0

    scan_result = runner.invoke(app, ["scan", "--repository-root", str(tmp_path)])
    assert scan_result.exit_code == 0

    analyze_result = runner.invoke(
        app,
        ["analyze", "--no-ai", "--repository-root", str(tmp_path)],
    )
    assert analyze_result.exit_code == 0

    report_result = runner.invoke(
        app,
        ["report", "--repository-root", str(tmp_path)],
    )
    assert report_result.exit_code == 0

    plan_result = runner.invoke(
        app,
        ["plan", "--repository-root", str(tmp_path)],
    )
    assert plan_result.exit_code == 0

    assert (tmp_path / ".ai-debt" / "remediation-roadmap.md").exists()
    assert (tmp_path / ".ai-debt" / "handoff-summary.md").exists()

    work_packages = list((tmp_path / ".ai-debt" / "work-packages").glob("WP-*.md"))

    assert work_packages
    assert "Generated remediation plan" in plan_result.output


def test_run_command_creates_run_metadata(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'example'\n",
        encoding="utf-8",
    )

    init_result = runner.invoke(app, ["init", "--repository-root", str(tmp_path)])
    assert init_result.exit_code == 0

    run_result = runner.invoke(
        app,
        ["run", "--repository-root", str(tmp_path)],
    )
    assert run_result.exit_code == 0
    assert "Completed deterministic pipeline run" in run_result.output

    runs_dir = tmp_path / ".ai-debt" / "runs"
    run_files = list(runs_dir.glob("RUN-*.json"))
    assert run_files

    metadata = json.loads(run_files[0].read_text(encoding="utf-8"))
    assert metadata["analysis_mode"] == "deterministic-no-ai"
    assert metadata["summary"]["evidence_count"] > 0
