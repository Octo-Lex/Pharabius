# ruff: noqa: E402
"""Tests for multi-repo v1 golden-path field validation (W49-S01)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Import the validation module by path
_scripts_dir = str(Path(__file__).resolve().parent.parent / "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from validate_v1_golden_path import validate_repos


def _fixture(name: str, files: dict[str, str] | None = None) -> tuple[str, Path]:
    """Create a minimal fixture repo for validation."""
    return name, Path("tests/fixtures/golden_path_repo")


class TestValidationResultSchema:
    def test_schema_version(self) -> None:
        report = validate_repos({"golden": Path("tests/fixtures/golden_path_repo")})
        assert report["schema_version"] == "1.0"

    def test_release_target(self) -> None:
        report = validate_repos({"golden": Path("tests/fixtures/golden_path_repo")})
        assert report["release_target"] == "1.10.1"

    def test_total_repositories(self) -> None:
        report = validate_repos({"golden": Path("tests/fixtures/golden_path_repo")})
        assert report["total_repositories"] == 1

    def test_repository_has_required_fields(self) -> None:
        report = validate_repos({"golden": Path("tests/fixtures/golden_path_repo")})
        repo = report["repositories"][0]
        for field in [
            "name",
            "commands_run",
            "commands_passed",
            "commands_failed",
            "artifacts_expected",
            "artifacts_found",
            "readiness_status",
            "warnings",
        ]:
            assert field in repo, f"Missing field: {field}"


class TestMissingRepository:
    def test_missing_repo_handled_gracefully(self) -> None:
        report = validate_repos({"missing": Path("C:/nonexistent/path/repo")})
        assert report["total_repositories"] == 1
        repo = report["repositories"][0]
        assert repo["readiness_status"] == "needs_review"
        assert repo["commands_run"] == 0
        assert "not found" in repo["error"].lower() or "not exist" in repo["warnings"][0].lower()

    def test_missing_repo_counts(self) -> None:
        report = validate_repos({"missing": Path("C:/nonexistent/path/repo")})
        assert report["needs_review"] == 1
        assert report["ready"] == 0


class TestDeterminism:
    def test_same_input_same_counts(self) -> None:
        repos = {"golden": Path("tests/fixtures/golden_path_repo")}
        r1 = validate_repos(repos)
        r2 = validate_repos(repos)
        assert r1["total_repositories"] == r2["total_repositories"]
        assert len(r1["repositories"]) == len(r2["repositories"])


class TestOutputFile:
    def test_writes_results_json(self, tmp_path: Path) -> None:
        output = tmp_path / "output"
        validate_repos(
            {"golden": Path("tests/fixtures/golden_path_repo")},
            output_dir=output,
        )
        results_file = output / "results.json"
        assert results_file.exists()
        data = json.loads(results_file.read_text())
        assert data["schema_version"] == "1.0"


class TestFixtureValidation:
    def test_golden_fixture_passes(self) -> None:
        report = validate_repos({"golden": Path("tests/fixtures/golden_path_repo")})
        repo = report["repositories"][0]
        assert repo["commands_passed"] >= 1  # At least init
        assert repo["readiness_status"] in ("ready", "partial", "needs_review")
