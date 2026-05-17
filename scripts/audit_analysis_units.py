#!/usr/bin/env python3
"""Analysis Unit Audit Helper.

Lightweight developer utility that reads .ai-debt/analysis-units.json
and prints a summary with warnings.

Usage:
    python scripts/audit_analysis_units.py /path/to/repo

Exit codes:
    0 — success
    1 — analysis-units.json missing
    2 — analysis-units.json cannot be parsed or validated
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

THRESHOLD_LARGE_EVIDENCE = 20
THRESHOLD_MANY_SECURITY = 15
THRESHOLD_MANY_CONFIG = 10


def _load_units(repo_path: str) -> dict:
    """Load and validate analysis-units.json."""
    p = Path(repo_path) / ".ai-debt" / "analysis-units.json"
    if not p.exists():
        print(f"Error: {p} not found", file=sys.stderr)
        print("Run 'ai-debt map' first.", file=sys.stderr)
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: failed to parse {p}: {exc}", file=sys.stderr)
        return {}

    if "units" not in data or not isinstance(data["units"], list):
        print(f"Error: {p} missing 'units' array", file=sys.stderr)
        return {}

    return data


def _print_bar(label: str, value: int, width: int = 40) -> None:
    """Print a labelled count with right-alignment."""
    print(f"  {label:<{width - 6}}{value:>6}")


def audit(repo_path: str) -> int:
    """Run the audit and print results. Returns exit code."""
    data = _load_units(repo_path)
    if not data:
        return 1 if not (Path(repo_path) / ".ai-debt" / "analysis-units.json").exists() else 2

    units = data["units"]
    total = len(units)

    # Header
    print(f"\nAnalysis Unit Audit: {repo_path}")
    print("=" * 50)
    print(f"Total units: {total}\n")

    # Unit count by type
    type_counts: dict[str, int] = {}
    for u in units:
        t = u.get("unit_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    print("Unit count by type:")
    for t in sorted(type_counts, key=lambda x: -type_counts[x]):
        _print_bar(t, type_counts[t])
    print()

    # Zero-evidence units
    zero_ev = [u for u in units if not u.get("evidence_ids")]
    if zero_ev:
        print("Zero-evidence units:")
        for u in zero_ev:
            print(f"  [!] {u.get('analysis_unit_id', '?')} ({u.get('unit_type', '?')})")
        print()

    # Largest units by evidence count
    by_evidence = sorted(units, key=lambda u: len(u.get("evidence_ids", [])), reverse=True)
    top_evidence = [u for u in by_evidence if len(u.get("evidence_ids", [])) > 0][:5]
    if top_evidence:
        print("Largest units by evidence count:")
        for u in top_evidence:
            uid = u.get("analysis_unit_id", "?")
            count = len(u.get("evidence_ids", []))
            marker = " [!]" if count >= THRESHOLD_LARGE_EVIDENCE else ""
            print(f"  {uid}: {count} evidence items{marker}")
        print()

    # Largest units by file count
    by_files = sorted(units, key=lambda u: len(u.get("files", [])), reverse=True)
    top_files = [u for u in by_files if len(u.get("files", [])) > 0][:5]
    if top_files:
        print("Largest units by file count:")
        for u in top_files:
            uid = u.get("analysis_unit_id", "?")
            count = len(u.get("files", []))
            print(f"  {uid}: {count} files")
        print()

    # Top trust-boundary tags
    tag_counts: dict[str, int] = {}
    for u in units:
        for tag in u.get("trust_boundary_tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    if tag_counts:
        print("Top trust-boundary tags:")
        for tag in sorted(tag_counts, key=lambda x: -tag_counts[x])[:10]:
            _print_bar(tag, tag_counts[tag])
        print()

    # Warnings
    warnings: list[str] = []

    if type_counts.get("security_sensitive_area", 0) >= THRESHOLD_MANY_SECURITY:
        warnings.append(
            f"Many security_sensitive_area units ({type_counts['security_sensitive_area']}). "
            "Consider reviewing grouping thresholds."
        )

    if type_counts.get("config_surface", 0) >= THRESHOLD_MANY_CONFIG:
        warnings.append(
            f"Many config_surface units ({type_counts['config_surface']}). "
            "Check for cache/tool directory noise."
        )

    if zero_ev:
        warnings.append(
            f"{len(zero_ev)} zero-evidence unit(s) found. "
            "These should have been filtered during mapping."
        )

    for u in by_evidence:
        if len(u.get("evidence_ids", [])) >= THRESHOLD_LARGE_EVIDENCE:
            warnings.append(
                f"{u.get('analysis_unit_id', '?')} has {len(u['evidence_ids'])} evidence items "
                "(possible over-aggregation)."
            )
            break  # one warning is enough

    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  [!] {w}")
    else:
        print("No warnings.")

    print()
    return 0


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <repo-path>", file=sys.stderr)
        sys.exit(2)

    sys.exit(audit(sys.argv[1]))


if __name__ == "__main__":
    main()
