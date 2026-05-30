"""Golden snapshot generator (v3.6.0).

Usage:
    python -m benchmarks.generate_golden --update

Builds all fixtures, runs the full pipeline on each, captures expected
high-level output bounds, and writes golden JSON files.

Volatile fields (timestamps, run IDs, absolute paths) are excluded from
golden assertions. All comparisons are bounded (min/max), not exact.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.fixture_builder import build_all_fixtures


def generate_golden_snapshot(fixture_name: str, repo_root: Path) -> dict:
    """Run the full pipeline on a fixture and capture expected bounds."""
    from pharabius.core.run_metadata import execute_run

    metadata = execute_run(repo_root)
    workspace = repo_root / ".ai-debt"

    # Load outputs
    register = _load_json(workspace / "debt-register.json")
    evidence = _load_json(workspace / "evidence.json")
    claims = _load_json(workspace / "claims" / "operational-claims.json")
    trace_quality = _load_json(workspace / "traceability" / "traceability-quality.json")

    findings = register.get("findings", [])
    evidence_items = evidence.get("evidence", [])
    summary = register.get("summary", {})

    # Category set
    categories = sorted(set(str(f.get("category", "")) for f in findings if f.get("category")))

    # Severity distribution
    severity_dist = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    risk_scores = []
    for f in findings:
        sev = str(f.get("severity", "Medium")).lower()
        if sev in severity_dist:
            severity_dist[sev] += 1
        score = int(f.get("risk_score", 0) or 0)
        risk_scores.append(score)

    return {
        "fixture": fixture_name,
        "pharabius_version": metadata.tool_version,
        "volatile_fields_ignored": ["generated_at", "run_id", "repository"],
        "path_normalization": "strip absolute prefix",
        "expected": {
            "finding_count_min": max(0, len(findings) - 2),
            "finding_count_max": len(findings) + 2,
            "categories": categories,
            "evidence_count_min": max(0, len(evidence_items) - 5),
            "work_package_count_min": 0,
            "claim_count_min": 0,
            "severity_distribution": {
                "critical_max": severity_dist["critical"] + 1,
                "high_max": severity_dist["high"] + 2,
                "medium_min": max(0, severity_dist["medium"] - 1),
            },
            "risk_score_range": {
                "min": min(risk_scores) if risk_scores else 0,
                "max": max(risk_scores) if risk_scores else 0,
            },
            "traceability_grade_allowed": ["partial", "usable", "complete", "weak"],
            "history_snapshot_enriched": True,
        },
    }


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def main() -> None:
    """Generate golden snapshots for all fixtures."""
    import argparse
    import tempfile

    parser = argparse.ArgumentParser(description="Generate golden snapshots")
    parser.add_argument("--update", action="store_true", help="Write golden files to disk")
    args = parser.parse_args()

    golden_dir = Path(__file__).resolve().parent / "golden"
    golden_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        fixtures = build_all_fixtures(Path(tmpdir))

        for name, repo_path in sorted(fixtures.items()):
            print(f"Generating golden for {name}...")
            try:
                snapshot = generate_golden_snapshot(name, repo_path)
            except Exception as e:
                print(f"  ERROR: {e}")
                continue

            if args.update:
                out_path = golden_dir / f"{name}.json"
                out_path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
                print(f"  Written: {out_path}")
            else:
                print(f"  {json.dumps(snapshot['expected'], indent=2)}")


if __name__ == "__main__":
    main()
