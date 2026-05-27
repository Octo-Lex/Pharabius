"""Multi-repo v1 golden-path field validation.

Runs the v1 command sequence against representative repositories and
produces a structured result file. No external API calls. No source
code modification.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import typer.testing

from pharabius.cli import app

runner = typer.testing.CliRunner()


def _validate_repo(repo_path: Path, name: str, temp_dir: Path) -> dict[str, Any]:
    """Validate a single repository against the v1 golden path."""
    # Create working copy
    work = temp_dir / name
    shutil.copytree(
        repo_path,
        work,
        ignore=shutil.ignore_patterns(
            ".git",
            "__pycache__",
            "node_modules",
            ".ai-debt",
            ".venv",
        ),
    )

    commands = [
        ["init", "-r", str(work)],
        ["profile", "-r", str(work)],
        ["scan", "-r", str(work)],
        ["map-units", "-r", str(work)],
        ["graph", "-r", str(work)],
        ["analyze", "--no-ai", "-r", str(work)],
        ["review", "--init", "-r", str(work)],
        ["report", "-r", str(work)],
        ["plan", "-r", str(work)],
        ["tickets", "-r", str(work)],
        ["export", "-r", str(work)],
        ["portfolio", "--repo", str(work)],
    ]

    results: list[dict[str, Any]] = []
    passed = 0
    failed = 0

    for cmd in commands:
        label = cmd[0]
        t0 = time.monotonic()
        result = runner.invoke(app, cmd)
        elapsed = time.monotonic() - t0
        ok = result.exit_code == 0
        if ok:
            passed += 1
        else:
            failed += 1
        results.append(
            {
                "command": label,
                "exit_code": result.exit_code,
                "success": ok,
                "elapsed_s": round(elapsed, 2),
            }
        )

    # Artifact presence check
    ai = work / ".ai-debt"
    expected = [
        "evidence.json",
        "debt-register.json",
        "project-profile.json",
        "debt-register.md",
        "reports/foundation-audit-report.md",
        "remediation-roadmap.md",
        "handoff-summary.md",
    ]
    artifacts_found = sum(1 for a in expected if (ai / a).exists())

    # Readiness
    readiness_status = "needs_review"
    if failed == 0 and artifacts_found == len(expected):
        readiness_status = "ready"
    elif failed == 0:
        readiness_status = "partial"

    warnings: list[str] = []
    if failed > 0:
        warnings.append(f"{failed} command(s) failed")
    if artifacts_found < len(expected):
        missing = len(expected) - artifacts_found
        warnings.append(f"{missing} expected artifact(s) missing")

    return {
        "name": name,
        "path": str(repo_path),
        "commands_run": len(commands),
        "commands_passed": passed,
        "commands_failed": failed,
        "artifacts_expected": len(expected),
        "artifacts_found": artifacts_found,
        "readiness_status": readiness_status,
        "command_results": results,
        "warnings": warnings,
        "limitations": [],
    }


def validate_repos(repos: dict[str, Path], output_dir: Path | None = None) -> dict[str, Any]:
    """Validate multiple repositories and produce results."""
    with tempfile.TemporaryDirectory(prefix="pharabius-v1-val-") as tmp:
        temp = Path(tmp)
        repo_results = []

        for name, path in repos.items():
            if not path.exists():
                repo_results.append(
                    {
                        "name": name,
                        "path": str(path),
                        "error": "Repository not found",
                        "readiness_status": "needs_review",
                        "commands_run": 0,
                        "commands_passed": 0,
                        "commands_failed": 0,
                        "artifacts_expected": 0,
                        "artifacts_found": 0,
                        "warnings": ["Repository path does not exist"],
                        "limitations": [],
                    }
                )
                continue
            repo_results.append(_validate_repo(path, name, temp))

    ready = sum(1 for r in repo_results if r.get("readiness_status") == "ready")
    partial = sum(1 for r in repo_results if r.get("readiness_status") == "partial")
    needs_review = sum(1 for r in repo_results if r.get("readiness_status") == "needs_review")

    report = {
        "schema_version": "1.0",
        "release_target": "1.10.1",
        "total_repositories": len(repo_results),
        "ready": ready,
        "partial": partial,
        "needs_review": needs_review,
        "repositories": repo_results,
    }

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "results.json").write_text(
            json.dumps(report, indent=2, default=str), encoding="utf-8"
        )

    return report


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Multi-repo v1 golden-path field validation")
    parser.add_argument("--output", "-o", default=None, help="Output directory for results")
    args = parser.parse_args()

    default_repos = {
        "pharabius": Path("C:/Next-Era/Pharabius/pharabius"),
        "validation-java": Path("C:/Next-Era/validation-java"),
        "validation-empty": Path("C:/Next-Era/validation-empty"),
        "validation-dotnet": Path("C:/Next-Era/validation-dotnet"),
    }

    output_dir = Path(args.output) if args.output else None
    report = validate_repos(default_repos, output_dir)

    print(f"Repositories: {report['total_repositories']}")
    print(f"Ready: {report['ready']}")
    print(f"Partial: {report['partial']}")
    print(f"Needs review: {report['needs_review']}")

    for r in report["repositories"]:
        status = r.get("readiness_status", "unknown")
        passed = r.get("commands_passed", 0)
        total = r.get("commands_run", 0)
        print(f"  {r['name']}: {status} ({passed}/{total} commands)")

    if output_dir:
        print(f"Output: {output_dir / 'results.json'}")

    if report["needs_review"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
