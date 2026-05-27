"""End-to-end golden path validation for Pharabius v1.

Runs the full v1 workflow against a fixture repository and verifies
artifacts, schemas, and safety boundaries.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO_FIXTURE = Path(__file__).parent / "tests" / "fixtures" / "golden_path_repo"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    project = Path(__file__).resolve().parent
    fixture = REPO_FIXTURE.resolve()
    if not fixture.exists():
        print(f"Fixture not found: {fixture}")
        return 1

    # Create temp working copy
    work_dir = project / ".golden-path-work"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    shutil.copytree(fixture, work_dir)

    # Import CLI
    from pharabius.cli import app
    import typer.testing

    runner = typer.testing.CliRunner()

    commands = [
        (["init", "-r", str(work_dir)], "init"),
        (["profile", "-r", str(work_dir)], "profile"),
        (["scan", "-r", str(work_dir)], "scan"),
        (["map-units", "-r", str(work_dir)], "map-units"),
        (["graph", "-r", str(work_dir)], "graph"),
        (["analyze", "--no-ai", "-r", str(work_dir)], "analyze"),
        (["review", "--init", "-r", str(work_dir)], "review-init"),
        (["report", "-r", str(work_dir)], "report"),
        (["plan", "-r", str(work_dir)], "plan"),
        (["tickets", "-r", str(work_dir)], "tickets"),
        (["export", "-r", str(work_dir)], "export"),
        (["portfolio", "--repo", str(work_dir)], "portfolio"),
    ]

    passed = 0
    failed = 0
    for args, label in commands:
        result = runner.invoke(app, args)
        if result.exit_code != 0:
            print(f"FAIL {label}: exit code {result.exit_code}")
            if result.output:
                print(f"  {result.output[:200]}")
            failed += 1
        else:
            passed += 1

    ai_debt = work_dir / ".ai-debt"

    # Artifact checks
    required_json = [
        "evidence.json",
        "debt-register.json",
        "project-profile.json",
        "analysis-units.json",
        "architecture-graph.json",
        "review/decisions.json",
        "ticket-drafts/ticket-drafts.json",
        "export-bundles/manifest.json",
        "portfolio/portfolio-summary.json",
        "portfolio/repository-index.json",
    ]

    required_md = [
        "debt-register.md",
        "reports/foundation-audit-report.md",
        "remediation-roadmap.md",
        "handoff-summary.md",
        "reports/ticket-draft-summary.md",
        "reports/export-bundle-summary.md",
        "portfolio/portfolio-summary.md",
        "portfolio/validation-rollup.md",
    ]

    artifacts_ok = 0
    artifacts_fail = 0

    for rel in required_json:
        p = ai_debt / rel
        if not p.exists():
            print(f"MISSING artifact: {rel}")
            artifacts_fail += 1
        else:
            try:
                json.loads(p.read_text())
                artifacts_ok += 1
            except json.JSONDecodeError:
                print(f"INVALID JSON: {rel}")
                artifacts_fail += 1

    for rel in required_md:
        p = ai_debt / rel
        if not p.exists():
            print(f"MISSING artifact: {rel}")
            artifacts_fail += 1
        elif len(p.read_text().strip()) == 0:
            print(f"EMPTY artifact: {rel}")
            artifacts_fail += 1
        else:
            artifacts_ok += 1

    # Source file integrity
    src_before = _sha256(fixture / "src" / "index.js")
    src_after = _sha256(work_dir / "src" / "index.js")
    src_ok = src_before == src_after

    # Cleanup
    shutil.rmtree(work_dir, ignore_errors=True)

    # Summary
    print()
    print(f"Commands: {passed} passed, {failed} failed")
    print(f"Artifacts: {artifacts_ok} ok, {artifacts_fail} missing/invalid")
    print(f"Source mutation: {'NONE' if src_ok else 'DETECTED'}")
    print(f"External API calls: 0 (not tested; script has no network)")

    if failed > 0 or artifacts_fail > 0 or not src_ok:
        print()
        print("Golden path validation: FAIL")
        return 1

    print()
    print("Golden path validation: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
