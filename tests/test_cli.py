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


class TestEnrichCLI:
    """CLI integration tests for ai-debt enrich command."""

    def _setup_repo(self, tmp_path: Path) -> Path:
        """Create minimal repo with deterministic artifacts."""
        import json

        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir(exist_ok=True)

        (ai_debt / "evidence.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "evidence": [
                        {
                            "evidence_id": "EVD-001",
                            "type": "manifest_detected",
                            "location": {"file": "pyproject.toml"},
                            "raw_observation": "test",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        (ai_debt / "debt-register.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "findings": [
                        {
                            "id": "TD-DEP-001",
                            "category": "TD-DEP",
                            "title": "Test",
                            "severity": "Medium",
                            "evidence_ids": ["EVD-001"],
                            "analysis_unit_ids": [],
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        (ai_debt / "project-profile.json").write_text("{}", encoding="utf-8")
        return tmp_path

    def test_default_disabled_writes_nothing(self, tmp_path: Path):
        repo = self._setup_repo(tmp_path)
        result = runner.invoke(app, ["enrich", "-r", str(repo)])
        assert result.exit_code == 0
        assert "disabled" in result.output.lower()
        assert not (repo / ".ai-debt" / "ai").exists()

    def test_mock_writes_sidecars(self, tmp_path: Path):
        repo = self._setup_repo(tmp_path)
        result = runner.invoke(app, ["enrich", "--provider", "mock", "-r", str(repo)])
        assert result.exit_code == 0
        assert "AI enrichment complete" in result.output
        assert (repo / ".ai-debt" / "ai" / "enrichment-report.json").exists()
        assert (repo / ".ai-debt" / "ai" / "enrichment-report.md").exists()
        assert (repo / ".ai-debt" / "ai" / "finding-enrichments.json").exists()
        assert (repo / ".ai-debt" / "ai" / "rejected-ai-output.json").exists()

    def test_dry_run_writes_nothing(self, tmp_path: Path):
        repo = self._setup_repo(tmp_path)
        result = runner.invoke(app, ["enrich", "--provider", "mock", "--dry-run", "-r", str(repo)])
        assert result.exit_code == 0
        assert not (repo / ".ai-debt" / "ai").exists()

    def test_finding_id_limits_output(self, tmp_path: Path):
        repo = self._setup_repo(tmp_path)
        result = runner.invoke(
            app, ["enrich", "--provider", "mock", "--finding-id", "TD-DEP-001", "-r", str(repo)]
        )
        assert result.exit_code == 0
        assert "Enriched:   1 finding(s)" in result.output

    def test_unknown_finding_id_fails_clear(self, tmp_path: Path):
        repo = self._setup_repo(tmp_path)
        result = runner.invoke(
            app, ["enrich", "--provider", "mock", "--finding-id", "NONEXISTENT", "-r", str(repo)]
        )
        assert result.exit_code == 1
        assert "NONEXISTENT" in result.output
        assert "not found" in result.output.lower()

    def test_missing_debt_register_fails(self, tmp_path: Path):
        repo = tmp_path  # No .ai-debt at all
        result = runner.invoke(app, ["enrich", "-r", str(repo)])
        assert result.exit_code == 1
        assert "debt-register.json" in result.output

    def test_missing_evidence_fails(self, tmp_path: Path):
        import json

        repo = tmp_path
        ai_debt = repo / ".ai-debt"
        ai_debt.mkdir(exist_ok=True)
        (ai_debt / "debt-register.json").write_text(json.dumps({"findings": []}), encoding="utf-8")
        result = runner.invoke(app, ["enrich", "-r", str(repo)])
        assert result.exit_code == 1
        assert "evidence.json" in result.output

    def test_invalid_provider_fails(self, tmp_path: Path):
        repo = self._setup_repo(tmp_path)
        result = runner.invoke(app, ["enrich", "--provider", "openai", "-r", str(repo)])
        assert result.exit_code == 1
        assert "not available" in result.output

    def test_strict_mock_exits_0(self, tmp_path: Path):
        repo = self._setup_repo(tmp_path)
        result = runner.invoke(app, ["enrich", "--provider", "mock", "--strict", "-r", str(repo)])
        assert result.exit_code == 0
        assert "Enriched:   1 finding(s)" in result.output

    def test_max_findings_lower_bound(self, tmp_path: Path):
        repo = self._setup_repo(tmp_path)
        # max_findings=0 should be rejected by Typer min=1
        result = runner.invoke(
            app, ["enrich", "--provider", "mock", "--max-findings", "0", "-r", str(repo)]
        )
        assert result.exit_code != 0


# ── Review CLI tests ─────────────────────────────────────────────


def _setup_repo_for_review(tmp_path: Path) -> Path:
    """Create a minimal workspace with findings for review testing."""
    from typer.testing import CliRunner

    runner = CliRunner()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "requirements.txt").write_text("flask\n")

    runner.invoke(app, ["init", "-r", str(repo)])
    runner.invoke(app, ["run", "-r", str(repo)])
    runner.invoke(app, ["analyze", "--no-ai", "-r", str(repo)])
    return repo


class TestReviewCLI:
    def test_review_init_creates_sidecar(self, tmp_path: Path) -> None:
        repo = _setup_repo_for_review(tmp_path)
        runner = CliRunner()

        result = runner.invoke(app, ["review", "--init", "-r", str(repo)])
        assert result.exit_code == 0
        assert (repo / ".ai-debt" / "review" / "decisions.json").exists()

    def test_review_init_refuses_overwrite(self, tmp_path: Path) -> None:
        repo = _setup_repo_for_review(tmp_path)
        runner = CliRunner()

        runner.invoke(app, ["review", "--init", "-r", str(repo)])
        result = runner.invoke(app, ["review", "--init", "-r", str(repo)])
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_review_status_no_sidecar(self, tmp_path: Path) -> None:
        repo = _setup_repo_for_review(tmp_path)
        runner = CliRunner()

        result = runner.invoke(app, ["review", "--status", "-r", str(repo)])
        assert result.exit_code == 0
        assert "No review sidecar" in result.output or "not found" in result.output.lower()

    def test_review_status_with_decisions(self, tmp_path: Path) -> None:
        repo = _setup_repo_for_review(tmp_path)
        runner = CliRunner()

        runner.invoke(app, ["review", "--init", "-r", str(repo)])

        # Add a decision manually
        import json

        path = repo / ".ai-debt" / "review" / "decisions.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["decisions"].append(
            {
                "finding_id": "TD-DEP-001",
                "status": "accepted",
                "reviewed_at": "2026-05-20T12:00:00Z",
                "reviewer": "platform-team",
                "rationale": "",
                "ticket_url": "",
                "owner_area": "",
                "target_release": "",
                "notes": "",
            }
        )
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        result = runner.invoke(app, ["review", "--status", "-r", str(repo)])
        assert result.exit_code == 0
        assert "TD-DEP-001" in result.output
        assert "accepted" in result.output

    def test_review_validate_valid(self, tmp_path: Path) -> None:
        repo = _setup_repo_for_review(tmp_path)
        runner = CliRunner()

        runner.invoke(app, ["review", "--init", "-r", str(repo)])
        result = runner.invoke(app, ["review", "--validate", "-r", str(repo)])
        assert result.exit_code == 0
        assert "Validation passed" in result.output

    def test_review_validate_invalid_status(self, tmp_path: Path) -> None:
        repo = _setup_repo_for_review(tmp_path)
        runner = CliRunner()

        runner.invoke(app, ["review", "--init", "-r", str(repo)])

        import json

        path = repo / ".ai-debt" / "review" / "decisions.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["decisions"].append(
            {
                "finding_id": "TD-DEP-001",
                "status": "invalid",
                "reviewed_at": "2026-05-20T12:00:00Z",
            }
        )
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        result = runner.invoke(app, ["review", "--validate", "-r", str(repo)])
        assert result.exit_code == 1
        assert "Validation failed" in result.output

    def test_review_validate_no_sidecar(self, tmp_path: Path) -> None:
        repo = _setup_repo_for_review(tmp_path)
        runner = CliRunner()

        result = runner.invoke(app, ["review", "--validate", "-r", str(repo)])
        assert result.exit_code == 1

    def test_review_default_is_status(self, tmp_path: Path) -> None:
        repo = _setup_repo_for_review(tmp_path)
        runner = CliRunner()

        result = runner.invoke(app, ["review", "-r", str(repo)])
        assert result.exit_code == 0
        assert "Review Decision Summary" in result.output
