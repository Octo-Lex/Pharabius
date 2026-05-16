"""
Pharabius validation script.

Runs the full Pharabius pipeline against a repository and prints a summary
from the generated run metadata.

Usage:
    python scripts/validate_repo.py /path/to/repository
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def find_run_metadata(workspace: Path) -> Path | None:
    """Find the most recent RUN-*.json in .ai-debt/runs/."""
    runs_dir = workspace / ".ai-debt" / "runs"

    if not runs_dir.exists():
        return None

    run_files = sorted(runs_dir.glob("RUN-*.json"), reverse=True)

    if not run_files:
        return None

    return run_files[0]


def load_run_metadata(path: Path) -> dict | None:
    """Load and return run metadata JSON."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    if isinstance(data, dict):
        return data

    return None


def print_summary(metadata: dict) -> None:
    """Print a concise validation summary."""
    summary = metadata.get("summary", {})

    print()
    print("=" * 60)
    print("  Pharabius Validation Summary")
    print("=" * 60)
    print(f"  Run ID:            {metadata.get('run_id', 'N/A')}")
    print(f"  Timestamp:         {metadata.get('timestamp', 'N/A')}")
    print(f"  Repository:        {metadata.get('repository', 'N/A')}")
    print(f"  Branch:            {metadata.get('branch') or 'Unknown'}")
    print(f"  Commit:            {metadata.get('commit') or 'Unknown'}")
    print(f"  Tool version:      {metadata.get('tool_version', 'N/A')}")
    print(f"  Analysis mode:     {metadata.get('analysis_mode', 'N/A')}")
    print("-" * 60)
    print(f"  Evidence count:    {summary.get('evidence_count', 0)}")
    print(f"  Finding count:     {summary.get('finding_count', 0)}")
    print(f"  Work packages:     {summary.get('work_package_count', 0)}")
    print("-" * 60)
    print(f"  Critical:          {summary.get('critical_findings', 0)}")
    print(f"  High:              {summary.get('high_findings', 0)}")
    print(f"  Medium:            {summary.get('medium_findings', 0)}")
    print(f"  Low:               {summary.get('low_findings', 0)}")
    print("=" * 60)
    print()

    files_written = metadata.get("files_written", [])
    if files_written:
        print(f"  Files written:     {len(files_written)}")
        for f in files_written:
            print(f"    - {f}")
        print()

    limitations = metadata.get("limitations", [])
    if limitations:
        print("  Limitations:")
        for limitation in limitations:
            print(f"    - {limitation}")
        print()


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_repo.py <repository_path>")
        return 1

    repo_path = Path(sys.argv[1]).resolve()

    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}")
        return 1

    print(f"Running Pharabius validation against: {repo_path}")
    print()

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pharabius.cli",
                "run",
                "--repository-root",
                str(repo_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        print("Error: ai-debt run timed out after 120 seconds.")
        return 1

    if result.returncode != 0:
        print(f"Error: ai-debt run failed with exit code {result.returncode}")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return 1

    if result.stdout:
        print(result.stdout)

    metadata_path = find_run_metadata(repo_path)

    if metadata_path is None:
        print("Error: No run metadata file found after ai-debt run.")
        return 1

    metadata = load_run_metadata(metadata_path)

    if metadata is None:
        print(f"Error: Could not parse run metadata: {metadata_path}")
        return 1

    print_summary(metadata)

    return 0


if __name__ == "__main__":
    sys.exit(main())
