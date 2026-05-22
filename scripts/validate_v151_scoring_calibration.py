#!/usr/bin/env python3
"""v1.5.1 Scoring Calibration Field Validation.

Runs enhanced scoring validation across repositories and emits
scoring evidence pack artifacts per W40-S01 format.

Usage:
    python scripts/validate_v151_scoring_calibration.py \\
        --repo Pharabius=. \\
        --repo validation-java=../validation-java \\
        --output .ai-debt/reports/scoring-evidence-pack.json \\
        --markdown-output .ai-debt/reports/scoring-evidence-pack.md

Exit codes:
    0 — all invariants pass
    1 — one or more invariants failed
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def find_ai_debt() -> str:
    """Find the ai-debt CLI entry point."""
    # Check if running from within the Pharabius repo
    venv = Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "ai-debt.exe"
    if venv.exists():
        return str(venv)
    return "ai-debt"


def run_command(
    args: list[str], cwd: Path, timeout_seconds: int = 120
) -> subprocess.CompletedProcess[str]:
    """Run a command and return the result."""
    return subprocess.run(
        args, capture_output=True, text=True, cwd=str(cwd), timeout=timeout_seconds
    )


def hash_file(path: Path) -> str:
    """SHA-256 hash of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_debt_register(repo: Path) -> dict[str, Any]:
    """Load debt-register.json from a repo."""
    path = repo / ".ai-debt" / "debt-register.json"
    return json.loads(path.read_text(encoding="utf-8"))


def get_commit(repo: Path) -> str:
    """Get HEAD commit SHA."""
    r = run_command(["git", "rev-parse", "HEAD"], cwd=repo, timeout_seconds=5)
    if r.returncode == 0:
        return r.stdout.strip()
    return "unknown"


def extract_finding_snapshot(register: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract finding ID → {score, priority, evidence_ids} snapshot."""
    result: dict[str, dict[str, Any]] = {}
    for f in register.get("findings", []):
        result[f["id"]] = {
            "score": f["risk_score"],
            "priority": f["priority"],
            "evidence_ids": sorted(f.get("evidence_ids", [])),
        }
    return result


def compare_default_to_enhanced(
    default_snap: dict[str, dict[str, Any]],
    enhanced_snap: dict[str, dict[str, Any]],
    default_register: dict[str, Any],
    enhanced_register: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compare finding snapshots and produce score_changes entries."""
    changes: list[dict[str, Any]] = []
    for fid in default_snap:
        if fid not in enhanced_snap:
            continue
        d = default_snap[fid]
        e = enhanced_snap[fid]
        if d["score"] != e["score"] or d["priority"] != e["priority"]:
            # Find finding details
            d_finding = next(
                (f for f in default_register.get("findings", []) if f["id"] == fid), {}
            )
            e_finding = next(
                (f for f in enhanced_register.get("findings", []) if f["id"] == fid), {}
            )
            changed_factors: list[dict[str, Any]] = []
            for factor_key in ("architecture_centrality", "change_frequency"):
                d_finding.get("risk_breakdown", {})
                e_bd = e_finding.get("risk_breakdown", {})
                if isinstance(e_bd.get(factor_key), dict):
                    fdata = e_bd[factor_key]
                    changed_factors.append(
                        {
                            "factor": factor_key,
                            "before_level": "Low",
                            "before_value": 1,
                            "after_level": fdata.get("level", "Low"),
                            "after_value": fdata.get("value", 1),
                            "source": fdata.get("source", ""),
                            "reason": fdata.get("reason", ""),
                        }
                    )

            changes.append(
                {
                    "finding_id": fid,
                    "title": d_finding.get("title", ""),
                    "category": d_finding.get("category", ""),
                    "before_score": d["score"],
                    "after_score": e["score"],
                    "before_priority": d["priority"],
                    "after_priority": e["priority"],
                    "changed_factors": changed_factors,
                }
            )
    return changes


def render_evidence_pack_markdown(
    pack: dict[str, Any],
) -> str:
    """Render evidence pack as Markdown."""
    lines: list[str] = []
    lines.append("# Scoring Evidence Pack")
    lines.append("")

    # Summary
    summary = pack.get("summary", {})
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Repositories checked | {summary.get('repositories_checked', 0)} |")
    lines.append(f"| Repositories passed | {summary.get('repositories_passed', 0)} |")
    lines.append(f"| Score changes | {summary.get('score_changes_total', 0)} |")
    lines.append(f"| Priority changes | {summary.get('priority_changes_total', 0)} |")
    lines.append(f"| Preview mutation failures | {summary.get('preview_mutation_failures', 0)} |")
    lines.append(f"| ID stability failures | {summary.get('id_stability_failures', 0)} |")
    lines.append("")

    # Per-repo sections
    for repo in pack.get("repositories", []):
        lines.append(f"## Repository: {repo['name']}")
        lines.append("")
        lines.append("| Check | Result |")
        lines.append("|---|---|")
        lines.append(
            f"| Finding IDs stable | {'PASS' if repo.get('finding_ids_stable') else 'FAIL'} |"
        )
        lines.append(
            f"| Evidence IDs stable | {'PASS' if repo.get('evidence_ids_stable') else 'FAIL'} |"
        )
        mut = repo.get("canonical_mutation_in_preview", True)
        lines.append(f"| Preview mode mutation | {'PASS — no mutation' if not mut else 'FAIL'} |")
        lines.append(f"| Default findings | {repo.get('default_findings', 0)} |")
        lines.append(f"| Enhanced findings | {repo.get('enhanced_findings', 0)} |")
        lines.append("")

        if repo.get("score_changes"):
            lines.append("### Score Changes")
            lines.append("")
            lines.append("| Finding | Category | Score | Priority | Changed Factors |")
            lines.append("|---|---|---:|---|---|")
            for sc in repo["score_changes"]:
                score_str = f"{sc['before_score']} → {sc['after_score']}"
                pri_str = f"{sc['before_priority']} → {sc['after_priority']}"
                factors = ", ".join(f["factor"] for f in sc.get("changed_factors", []))
                lines.append(
                    f"| {sc['finding_id']} | {sc['category']} "
                    f"| {score_str} | {pri_str} | {factors} |"
                )
            lines.append("")

        if repo.get("warnings"):
            lines.append("### Warnings")
            lines.append("")
            for w in repo["warnings"]:
                lines.append(f"- {w}")
            lines.append("")

    return "\n".join(lines)


def validate_repo(name: str, repo_path: Path, ai_debt: str) -> dict[str, Any]:
    """Run full validation cycle for one repository."""
    ws = repo_path / ".ai-debt"
    commit = get_commit(repo_path)
    warnings: list[str] = []

    # Clean workspace
    if ws.exists():
        shutil.rmtree(ws)

    # Default analysis
    t0 = time.monotonic()
    r = run_command([ai_debt, "init", "-r", str(repo_path)], cwd=repo_path)
    if r.returncode != 0:
        return {"name": name, "error": f"init failed: {r.stderr[:200]}", "commit": commit}
    r = run_command([ai_debt, "run", "-r", str(repo_path)], cwd=repo_path)
    if r.returncode != 0:
        return {"name": name, "error": f"run failed: {r.stderr[:200]}", "commit": commit}

    r = run_command([ai_debt, "analyze", "--no-ai", "-r", str(repo_path)], cwd=repo_path)
    default_runtime = round(time.monotonic() - t0, 2)
    if r.returncode != 0:
        return {
            "name": name,
            "error": f"default analyze failed: {r.stderr[:200]}",
            "commit": commit,
        }

    hash_file(ws / "debt-register.json")
    default_register = load_debt_register(repo_path)
    default_snap = extract_finding_snapshot(default_register)
    default_count = len(default_register.get("findings", []))

    # Enhanced analysis
    t0 = time.monotonic()
    r = run_command(
        [ai_debt, "analyze", "--no-ai", "--enhanced-scoring", "-r", str(repo_path)],
        cwd=repo_path,
    )
    enhanced_runtime = round(time.monotonic() - t0, 2)
    if r.returncode != 0:
        return {
            "name": name,
            "error": f"enhanced analyze failed: {r.stderr[:200]}",
            "commit": commit,
        }

    enhanced_register = load_debt_register(repo_path)
    enhanced_snap = extract_finding_snapshot(enhanced_register)
    enhanced_count = len(enhanced_register.get("findings", []))

    # Score changes
    score_changes = compare_default_to_enhanced(
        default_snap, enhanced_snap, default_register, enhanced_register
    )

    # Reset to default
    r = run_command(
        [ai_debt, "analyze", "--no-ai", "--no-enhanced-scoring", "-r", str(repo_path)],
        cwd=repo_path,
    )
    reset_register = load_debt_register(repo_path)
    reset_snap = extract_finding_snapshot(reset_register)
    scores_restored = all(
        reset_snap.get(fid, {}).get("score") == snap.get("score")
        for fid, snap in default_snap.items()
    )

    # Scoring preview
    t0 = time.monotonic()
    r = run_command(
        [ai_debt, "analyze", "--no-ai", "--scoring-preview", "-r", str(repo_path)],
        cwd=repo_path,
    )
    preview_runtime = round(time.monotonic() - t0, 2)

    # Check canonical unchanged after preview
    preview_hash = hash_file(ws / "debt-register.json")
    canonical_mutation = preview_hash != hash_file(ws / "debt-register.json")

    # Finding ID stability
    finding_ids_stable = set(default_snap.keys()) == set(enhanced_snap.keys())

    # Evidence ID stability
    evidence_stable = all(
        default_snap.get(fid, {}).get("evidence_ids")
        == enhanced_snap.get(fid, {}).get("evidence_ids")
        for fid in default_snap
    )

    # Priority changes
    priority_changes = sum(
        1 for sc in score_changes if sc["before_priority"] != sc["after_priority"]
    )

    # Cleanup
    shutil.rmtree(ws)

    return {
        "name": name,
        "path": str(repo_path),
        "commit": commit,
        "default_findings": default_count,
        "enhanced_findings": enhanced_count,
        "finding_ids_stable": finding_ids_stable,
        "evidence_ids_stable": evidence_stable,
        "canonical_mutation_in_preview": canonical_mutation,
        "scores_restored": scores_restored,
        "score_changes": score_changes,
        "warnings": warnings,
        "runtime_seconds": {
            "default": default_runtime,
            "enhanced": enhanced_runtime,
            "preview": preview_runtime,
        },
        "_priority_changes": priority_changes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="v1.5.1 Scoring Calibration Field Validation")
    parser.add_argument(
        "--repo",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="Repository to validate (name=path format)",
    )
    parser.add_argument(
        "--output",
        default="scoring-evidence-pack.json",
        help="JSON output path",
    )
    parser.add_argument(
        "--markdown-output",
        default="scoring-evidence-pack.md",
        help="Markdown output path",
    )
    args = parser.parse_args()

    if not args.repo:
        print("No repositories specified. Use --repo NAME=PATH")
        return 1

    ai_debt = find_ai_debt()
    print(f"Using: {ai_debt}")

    # Parse repos
    repos: list[tuple[str, Path]] = []
    for spec in args.repo:
        if "=" in spec:
            name, path = spec.split("=", 1)
        else:
            name = Path(spec).name
            path = spec
        repos.append((name, Path(path).resolve()))

    # Validate each repo
    results: list[dict[str, Any]] = []
    for name, repo_path in repos:
        print(f"\n{'=' * 60}")
        print(f"REPO: {name}")
        print(f"{'=' * 60}")
        result = validate_repo(name, repo_path, ai_debt)
        results.append(result)

        if "error" in result:
            print(f"  ERROR: {result['error']}")
        else:
            print(f"  Default findings: {result['default_findings']}")
            print(f"  Enhanced findings: {result['enhanced_findings']}")
            print(f"  Score changes: {len(result['score_changes'])}")
            print(f"  Finding IDs stable: {result['finding_ids_stable']}")
            print(f"  Evidence IDs stable: {result['evidence_ids_stable']}")
            print(f"  Scores restored: {result['scores_restored']}")
            print(f"  Preview mutation: {result['canonical_mutation_in_preview']}")

    # Build evidence pack
    score_changes_total = sum(len(r.get("score_changes", [])) for r in results)
    priority_changes_total = sum(r.get("_priority_changes", 0) for r in results)
    preview_mutation_failures = sum(
        1 for r in results if r.get("canonical_mutation_in_preview", False)
    )
    id_stability_failures = sum(
        1
        for r in results
        if not r.get("finding_ids_stable", True) or not r.get("evidence_ids_stable", True)
    )
    repos_passed = sum(
        1
        for r in results
        if "error" not in r
        and r.get("finding_ids_stable", False)
        and r.get("evidence_ids_stable", False)
        and not r.get("canonical_mutation_in_preview", True)
        and r.get("scores_restored", False)
    )

    # Clean up internal fields
    clean_results = []
    for r in results:
        clean = {k: v for k, v in r.items() if not k.startswith("_")}
        clean_results.append(clean)

    pack: dict[str, Any] = {
        "schema_version": "1.0",
        "tool_version": "1.5.1-dev",
        "generated_at": datetime.now(UTC).isoformat(),
        "analysis_mode": "enhanced_scoring_validation",
        "repositories": clean_results,
        "summary": {
            "repositories_checked": len(results),
            "repositories_passed": repos_passed,
            "score_changes_total": score_changes_total,
            "priority_changes_total": priority_changes_total,
            "preview_mutation_failures": preview_mutation_failures,
            "id_stability_failures": id_stability_failures,
        },
    }

    # Write JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(pack, indent=2) + "\n", encoding="utf-8")
    print(f"\nJSON: {output_path}")

    # Write Markdown
    md_path = Path(args.markdown_output)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_evidence_pack_markdown(pack), encoding="utf-8")
    print(f"Markdown: {md_path}")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"RESULT: {'PASS' if repos_passed == len(results) else 'FAIL'}")
    print(f"  Repositories: {repos_passed}/{len(results)} passed")

    return 0 if repos_passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
