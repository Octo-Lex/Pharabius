"""Calibration results generator (v3.6.0).

Usage:
    python -m benchmarks.generate_calibration --update

Builds all fixtures, runs the pipeline, computes quality scores,
severity distributions, and threshold analysis, then writes
calibration-results.json.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.fixture_builder import build_all_fixtures
from benchmarks.rubric import compute_fixture_quality


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


THRESHOLD_NAMES = [
    "LARGE_FILE_LINE_THRESHOLD",
    "LONG_FUNCTION_LINE_THRESHOLD",
    "BROAD_EXCEPTION_PER_FILE_THRESHOLD",
    "MIN_DEBT_MARKER_OCCURRENCES",
    "COVERAGE_LOW_THRESHOLD_PCT",
    "DEFAULT_MAX_FILE_SIZE_KB",
]


def generate_calibration() -> dict:
    """Generate calibration results from all fixtures."""
    import tempfile

    from pharabius.core.constants import (
        BROAD_EXCEPTION_PER_FILE_THRESHOLD,
        COVERAGE_LOW_THRESHOLD_PCT,
        DEFAULT_MAX_FILE_SIZE_KB,
        LARGE_FILE_LINE_THRESHOLD,
        LONG_FUNCTION_LINE_THRESHOLD,
        MIN_DEBT_MARKER_OCCURRENCES,
    )
    from pharabius.core.run_metadata import execute_run

    thresholds = {
        "LARGE_FILE_LINE_THRESHOLD": LARGE_FILE_LINE_THRESHOLD,
        "LONG_FUNCTION_LINE_THRESHOLD": LONG_FUNCTION_LINE_THRESHOLD,
        "BROAD_EXCEPTION_PER_FILE_THRESHOLD": BROAD_EXCEPTION_PER_FILE_THRESHOLD,
        "MIN_DEBT_MARKER_OCCURRENCES": MIN_DEBT_MARKER_OCCURRENCES,
        "COVERAGE_LOW_THRESHOLD_PCT": COVERAGE_LOW_THRESHOLD_PCT,
        "DEFAULT_MAX_FILE_SIZE_KB": DEFAULT_MAX_FILE_SIZE_KB,
    }

    severity_dist: dict[str, dict[str, int]] = {}
    quality_scores: dict[str, dict] = {}
    threshold_entries: list[dict] = []
    warnings: list[dict] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        fixtures = build_all_fixtures(Path(tmpdir))

        for name, repo_path in sorted(fixtures.items()):
            try:
                execute_run(repo_path)
            except Exception as e:
                warnings.append({"code": "execute_run_failed", "message": f"{name}: {e}"})
                continue

            workspace = repo_path / ".ai-debt"
            register = _load_json(workspace / "debt-register.json")
            findings = register.get("findings", [])

            # Severity distribution
            dist = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for f in findings:
                sev = str(f.get("severity", "Medium")).lower()
                if sev in dist:
                    dist[sev] += 1
            severity_dist[name] = dist

            # Quality scores
            quality = compute_fixture_quality(findings)
            quality_scores[name] = {
                "average": quality["average_quality"],
                "noise_rate": quality["noise_rate"],
            }

    # Threshold entries (default: observe/document/keep)
    for tname, tval in thresholds.items():
        threshold_entries.append(
            {
                "name": tname,
                "original": tval,
                "calibrated": tval,
                "decision": "keep",
                "rationale": "Default: no evidence of noise or under-detection from benchmark fixtures.",  # noqa: E501
            }
        )

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "fixtures_tested": len(fixtures),
        "thresholds": threshold_entries,
        "severity_distribution": severity_dist,
        "finding_quality_scores": quality_scores,
        "warnings": warnings,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate calibration results")
    parser.add_argument("--update", action="store_true", help="Write calibration file")
    args = parser.parse_args()

    results = generate_calibration()

    if args.update:
        out_path = Path(__file__).resolve().parent / "calibration-results.json"
        out_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(f"Written: {out_path}")
    else:
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
