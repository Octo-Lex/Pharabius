from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pharabius.core.analyzer import write_debt_register
from pharabius.core.init_workspace import initialize_workspace
from pharabius.core.planner import write_plan
from pharabius.core.profiler import write_repository_profile
from pharabius.core.reporter import write_reports
from pharabius.core.scanner import write_evidence_store
from pharabius.schemas.run_metadata import RunMetadata, RunSummary


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    if isinstance(value, dict):
        return value

    return {}


def _git_value(root: Path, args: list[str]) -> str:
    import subprocess

    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return ""

    if result.returncode != 0:
        return ""

    return result.stdout.strip()


def _collect_files(workspace: Path) -> list[str]:
    files: list[Path] = []

    for path in sorted(workspace.rglob("*")):
        if path.is_dir():
            continue

        if ".git" in path.relative_to(workspace).parts:
            continue

        files.append(path)

    return [path.relative_to(workspace).as_posix() for path in files]


def _load_profile_limitations(root: Path) -> list[str]:
    path = root / ".ai-debt" / "project-profile.json"
    data = _load_json(path)

    if not data:
        return []

    limitations = data.get("limitations")

    if not isinstance(limitations, list):
        return []

    return [item for item in limitations if isinstance(item, str)]


def _load_evidence_count(root: Path) -> int:
    path = root / ".ai-debt" / "evidence.json"
    data = _load_json(path)

    evidence = data.get("evidence")

    if not isinstance(evidence, list):
        return 0

    return len(evidence)


def _load_debt_summary(root: Path) -> RunSummary:
    path = root / ".ai-debt" / "debt-register.json"
    data = _load_json(path)

    summary_data = data.get("summary", {})

    if not isinstance(summary_data, dict):
        return RunSummary()

    return RunSummary(
        evidence_count=_load_evidence_count(root),
        finding_count=summary_data.get("total_findings", 0),
        work_package_count=len(list((root / ".ai-debt" / "work-packages").glob("WP-*.md"))),
        critical_findings=summary_data.get("critical", 0),
        high_findings=summary_data.get("high", 0),
        medium_findings=summary_data.get("medium", 0),
        low_findings=summary_data.get("low", 0),
    )


def execute_run(repository_root: Path) -> RunMetadata:
    root = repository_root.resolve()
    workspace = root / ".ai-debt"

    commands_run = [
        "init",
        "profile",
        "scan",
        "analyze --no-ai",
        "report",
        "plan",
    ]

    initialize_workspace(root, force=True)
    write_repository_profile(root)
    write_evidence_store(root)
    write_debt_register(root)
    write_reports(root)
    write_plan(root)

    branch = _git_value(root, ["rev-parse", "--abbrev-ref", "HEAD"])
    commit = _git_value(root, ["rev-parse", "HEAD"])

    files_written = _collect_files(workspace) if workspace.exists() else []
    limitations = _load_profile_limitations(root)
    summary = _load_debt_summary(root)

    metadata = RunMetadata(
        repository=str(root),
        commit=commit,
        branch=branch,
        commands_run=commands_run,
        files_written=files_written,
        limitations=limitations,
        summary=summary,
    )

    runs_dir = workspace / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    output_path = runs_dir / f"{metadata.run_id}.json"
    output_path.write_text(
        metadata.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )

    return metadata
