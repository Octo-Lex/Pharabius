from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.run_metadata import execute_run
from pharabius.schemas.run_metadata import RunMetadata, RunSummary, generate_run_id


def test_generate_run_id_format() -> None:
    run_id = generate_run_id()

    assert run_id.startswith("RUN-")
    assert len(run_id) == len("RUN-YYYYMMDD-HHMMSS")


def test_run_metadata_schema_validates() -> None:
    metadata = RunMetadata(
        repository="/path/to/repo",
        commit="abc123",
        branch="main",
        commands_run=["init", "profile", "scan", "analyze --no-ai", "report", "plan"],
        files_written=["config.yaml", "evidence.json"],
        limitations=["No coverage report available."],
        summary=RunSummary(
            evidence_count=50,
            finding_count=2,
            work_package_count=1,
            critical_findings=0,
            high_findings=1,
            medium_findings=1,
            low_findings=0,
        ),
    )

    serialized = metadata.model_dump_json(indent=2)
    parsed = json.loads(serialized)

    assert parsed["run_id"].startswith("RUN-")
    assert parsed["analysis_mode"] == "deterministic-no-ai"
    assert parsed["summary"]["evidence_count"] == 50
    assert parsed["summary"]["finding_count"] == 2

    validated = RunMetadata.model_validate(parsed)
    assert validated.summary.evidence_count == 50


def test_execute_run_creates_metadata_file(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'example'\n",
        encoding="utf-8",
    )

    metadata = execute_run(tmp_path)

    workspace = tmp_path / ".ai-debt"

    assert (workspace / "config.yaml").exists()
    assert (workspace / "project-profile.json").exists()
    assert (workspace / "evidence.json").exists()
    assert (workspace / "debt-register.json").exists()
    assert (workspace / "debt-register.md").exists()
    assert (workspace / "remediation-roadmap.md").exists()
    assert (workspace / "handoff-summary.md").exists()

    runs_dir = workspace / "runs"
    metadata_path = runs_dir / f"{metadata.run_id}.json"

    assert metadata_path.exists()

    written = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert written["run_id"] == metadata.run_id
    assert written["repository"] == str(tmp_path.resolve())
    assert written["analysis_mode"] == "deterministic-no-ai"
    assert "init" in written["commands_run"]
    assert "profile" in written["commands_run"]
    assert "scan" in written["commands_run"]
    assert "analyze --no-ai" in written["commands_run"]
    assert "report" in written["commands_run"]
    assert "plan" in written["commands_run"]

    assert isinstance(written["summary"]["evidence_count"], int)
    assert isinstance(written["summary"]["finding_count"], int)
    assert isinstance(written["summary"]["work_package_count"], int)

    assert written["summary"]["evidence_count"] > 0
    assert len(written["files_written"]) > 0
