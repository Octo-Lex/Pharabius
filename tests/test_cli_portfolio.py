"""Tests for ai-debt portfolio CLI command (W45-S05)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from pharabius.cli import app

runner = CliRunner()


def _write_debt_register(repo: Path, name: str = "test") -> None:
    ai = repo / ".ai-debt"
    ai.mkdir(parents=True, exist_ok=True)
    register = {
        "schema_version": "1.0",
        "project_name": name,
        "repository": name,
        "commit": "abc123",
        "branch": "main",
        "generated_at": "2026-05-24T00:00:00Z",
        "summary": {"total_findings": 2, "high": 1, "low": 1},
        "findings": [
            {"category": "TD-ARCH", "priority": "High"},
            {"category": "TD-DEP", "priority": "Low"},
        ],
    }
    (ai / "debt-register.json").write_text(json.dumps(register), encoding="utf-8")


class TestPortfolioCLIHelp:
    def test_portfolio_in_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "portfolio" in result.output

    def test_portfolio_help(self) -> None:
        result = runner.invoke(app, ["portfolio", "--help"])
        assert result.exit_code == 0
        assert "--repo" in result.output
        assert "--output" in result.output


class TestPortfolioSingleRepo:
    def test_default_single_repo(self, tmp_path: Path) -> None:
        _write_debt_register(tmp_path, "alpha")
        result = runner.invoke(app, ["portfolio", "--repo", str(tmp_path)])
        assert result.exit_code == 0
        assert "Portfolio summary generated" in result.output
        assert "Repositories: 1" in result.output
        assert "Total findings: 2" in result.output

    def test_generates_json(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _write_debt_register(repo, "beta")
        out = tmp_path / "output"
        result = runner.invoke(app, ["portfolio", "--repo", str(repo), "--output", str(out)])
        assert result.exit_code == 0
        assert (out / "portfolio-summary.json").exists()
        data = json.loads((out / "portfolio-summary.json").read_text())
        assert data["schema_version"] == "1.0"

    def test_generates_markdown(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _write_debt_register(repo, "gamma")
        out = tmp_path / "output"
        result = runner.invoke(app, ["portfolio", "--repo", str(repo), "--output", str(out)])
        assert result.exit_code == 0
        assert (out / "portfolio-summary.md").exists()

    def test_generates_repository_index(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _write_debt_register(repo, "delta")
        out = tmp_path / "output"
        result = runner.invoke(app, ["portfolio", "--repo", str(repo), "--output", str(out)])
        assert result.exit_code == 0
        assert (out / "repository-index.json").exists()

    def test_generates_validation_rollup(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _write_debt_register(repo, "epsilon")
        out = tmp_path / "output"
        result = runner.invoke(app, ["portfolio", "--repo", str(repo), "--output", str(out)])
        assert result.exit_code == 0
        assert (out / "validation-rollup.md").exists()


class TestPortfolioMultipleRepos:
    def test_multiple_repos(self, tmp_path: Path) -> None:
        r1 = tmp_path / "alpha"
        r2 = tmp_path / "beta"
        _write_debt_register(r1, "alpha")
        _write_debt_register(r2, "beta")
        out = tmp_path / "portfolio"
        result = runner.invoke(
            app,
            [
                "portfolio",
                "--repo",
                str(r1),
                "--repo",
                str(r2),
                "--output",
                str(out),
            ],
        )
        assert result.exit_code == 0
        assert "Repositories: 2" in result.output
        index = json.loads((out / "repository-index.json").read_text())
        assert len(index) == 2


class TestPortfolioEdgeCases:
    def test_missing_repo_path(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent"
        result = runner.invoke(app, ["portfolio", "--repo", str(missing)])
        assert "Skipping" in result.output or result.exit_code == 1

    def test_no_valid_paths(self) -> None:
        result = runner.invoke(app, ["portfolio", "--repo", "/nonexistent/path"])
        assert result.exit_code == 1

    def test_output_dir_created(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _write_debt_register(repo, "test")
        out = tmp_path / "nested" / "output"
        result = runner.invoke(app, ["portfolio", "--repo", str(repo), "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()


class TestPortfolioNoMutation:
    def test_does_not_mutate_debt_register(self, tmp_path: Path) -> None:
        repo = tmp_path / "safe"
        _write_debt_register(repo, "safe")
        dr = repo / ".ai-debt" / "debt-register.json"
        before = dr.read_text(encoding="utf-8")
        out = tmp_path / "output"
        runner.invoke(app, ["portfolio", "--repo", str(repo), "--output", str(out)])
        assert dr.read_text(encoding="utf-8") == before
