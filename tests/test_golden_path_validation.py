"""Tests for end-to-end golden path validation (W48-S03)."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from pharabius.cli import app
import typer.testing

FIXTURE = Path("tests/fixtures/golden_path_repo")

PIPELINE_COMMANDS = [
    "init",
    "profile",
    "scan",
    "map-units",
    "graph",
    "analyze",
    "review",
    "report",
    "plan",
    "tickets",
    "export",
    "portfolio",
]


@pytest.fixture()
def work_dir(tmp_path: Path) -> Path:
    """Create a working copy of the golden path fixture."""
    dest = tmp_path / "golden"
    shutil.copytree(FIXTURE, dest)
    return dest


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _run_pipeline(work_dir: Path) -> None:
    """Run the full golden path pipeline."""
    r = typer.testing.CliRunner()
    for cmd in [
        ["init", "-r", str(work_dir)],
        ["profile", "-r", str(work_dir)],
        ["scan", "-r", str(work_dir)],
        ["map-units", "-r", str(work_dir)],
        ["graph", "-r", str(work_dir)],
        ["analyze", "--no-ai", "-r", str(work_dir)],
        ["review", "--init", "-r", str(work_dir)],
        ["report", "-r", str(work_dir)],
        ["plan", "-r", str(work_dir)],
        ["tickets", "-r", str(work_dir)],
        ["export", "-r", str(work_dir)],
        ["portfolio", "--repo", str(work_dir)],
    ]:
        result = r.invoke(app, cmd)
        assert result.exit_code == 0, (
            f"Failed: {' '.join(cmd)}\n{result.output[:300]}"
        )


runner = typer.testing.CliRunner()


class TestGoldenPathCommands:
    def test_init(self, work_dir: Path) -> None:
        r = runner.invoke(app, ["init", "-r", str(work_dir)])
        assert r.exit_code == 0

    def test_full_pipeline(self, work_dir: Path) -> None:
        _run_pipeline(work_dir)


class TestGoldenPathArtifacts:
    @pytest.fixture(autouse=True)
    def _setup(self, work_dir: Path) -> None:
        _run_pipeline(work_dir)

    def test_canonical_json_artifacts(self, work_dir: Path) -> None:
        ai = work_dir / ".ai-debt"
        for name in [
            "evidence.json",
            "debt-register.json",
            "project-profile.json",
            "analysis-units.json",
            "architecture-graph.json",
        ]:
            p = ai / name
            assert p.exists(), f"Missing: {name}"
            json.loads(p.read_text())

    def test_sidecar_json_artifacts(self, work_dir: Path) -> None:
        ai = work_dir / ".ai-debt"
        for name in [
            "review/decisions.json",
            "ticket-drafts/ticket-drafts.json",
            "portfolio/portfolio-summary.json",
            "portfolio/repository-index.json",
        ]:
            p = ai / name
            assert p.exists(), f"Missing: {name}"
            json.loads(p.read_text())

    def test_markdown_artifacts_nonempty(self, work_dir: Path) -> None:
        ai = work_dir / ".ai-debt"
        for name in [
            "debt-register.md",
            "reports/foundation-audit-report.md",
            "remediation-roadmap.md",
            "handoff-summary.md",
            "reports/ticket-draft-summary.md",
            "portfolio/portfolio-summary.md",
            "portfolio/validation-rollup.md",
        ]:
            p = ai / name
            assert p.exists(), f"Missing: {name}"
            assert len(p.read_text().strip()) > 0, f"Empty: {name}"


class TestGoldenPathSafety:
    def test_source_files_not_modified(self, work_dir: Path) -> None:
        src_before = _sha256(FIXTURE / "src" / "index.js")
        for cmd in [
            ["init", "-r", str(work_dir)],
            ["profile", "-r", str(work_dir)],
            ["scan", "-r", str(work_dir)],
            ["analyze", "--no-ai", "-r", str(work_dir)],
        ]:
            runner.invoke(app, cmd)
        src_after = _sha256(work_dir / "src" / "index.js")
        assert src_before == src_after, "Source file was modified!"
