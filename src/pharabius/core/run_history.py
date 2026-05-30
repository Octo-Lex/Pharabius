"""Run history intelligence (v3.5.0).

Builds enriched per-run snapshots, a queryable run history index, and
trend summaries covering finding counts, risk scores, evidence coverage,
work-package readiness, and traceability quality.

All trend functions expose a ``status`` field:
  - ``complete``: both compared runs have enriched snapshots
  - ``partial``: only the latest run has enriched data
  - ``insufficient_data``: fewer than 2 runs

Overall trajectory is heuristic — explicitly labeled as such in all outputs.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pharabius.core.constants import (
    EVIDENCE_SOURCE_FILE_SKIPPED,
    OBSERVATION_STRENGTH_LIMITATION,
)

# Evidence types for snapshot counting
_EVIDENCE_TYPES = [
    "large_file_detected",
    "debt_marker_detected",
    "source_file_skipped",
    "coverage_report_detected",
    "coverage_metric_detected",
    "coverage_gap_detected",
    "long_function_detected",
    "broad_exception_detected",
    "dependency_health_signal",
    "runtime_version_signal",
]


# ── File discrimination ───────────────────────────────────────────────


def _is_run_metadata_file(path: Path) -> bool:
    """True for run metadata JSON, false for index/snapshot/other files."""
    return (
        path.name.startswith("RUN-")
        and path.suffix == ".json"
        and not path.name.endswith("-history-snapshot.json")
    )


def _is_history_snapshot_file(path: Path) -> bool:
    """True for enriched per-run history snapshots."""
    return (
        path.name.startswith("RUN-")
        and path.name.endswith("-history-snapshot.json")
    )


# ── JSON helpers ──────────────────────────────────────────────────────


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return []
    return value if isinstance(value, list) else []


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


# ── S01: Enriched per-run snapshot ────────────────────────────────────


def build_current_run_snapshot(workspace: Path, run_id: str) -> dict[str, Any]:
    """Build enriched snapshot from current run artifacts.

    Reads: debt-register.json, evidence.json, claims/operational-claims.json,
    traceability/traceability-quality.json, work-packages/*.md
    Tolerates all missing files gracefully.
    """
    register = _load_json(workspace / "debt-register.json")
    evidence = _load_json(workspace / "evidence.json")
    claims_data = _load_json(workspace / "claims" / "operational-claims.json")
    trace_quality = _load_json(workspace / "traceability" / "traceability-quality.json")

    findings: list[dict[str, Any]] = register.get("findings", [])
    evidence_items: list[dict[str, Any]] = evidence.get("evidence", [])
    claims_list: list[dict[str, Any]] = claims_data.get("claims", [])
    wp_files = list((workspace / "work-packages").glob("WP-*.md")) if (workspace / "work-packages").exists() else []

    # Findings by category
    findings_by_category: dict[str, int] = {}
    for f in findings:
        cat = str(f.get("category", "unknown"))
        findings_by_category[cat] = findings_by_category.get(cat, 0) + 1

    # Risk by category
    risk_by_category: dict[str, dict[str, float]] = {}
    total_risk = 0
    risk_scores: list[int] = []
    for f in findings:
        cat = str(f.get("category", "unknown"))
        score = int(f.get("risk_score", 0) or 0)
        total_risk += score
        if score > 0:
            risk_scores.append(score)
        if cat not in risk_by_category:
            risk_by_category[cat] = {"total_risk": 0, "count": 0, "max_risk": 0}
        risk_by_category[cat]["total_risk"] += score
        risk_by_category[cat]["count"] += 1
        risk_by_category[cat]["max_risk"] = max(risk_by_category[cat]["max_risk"], score)

    # Clean risk_by_category — remove internal count
    for cat in risk_by_category:
        entry = risk_by_category[cat]
        avg = round(entry["total_risk"] / entry["count"], 1) if entry["count"] > 0 else 0
        risk_by_category[cat] = {
            "total_risk": entry["total_risk"],
            "average_risk": avg,
            "max_risk": entry["max_risk"],
        }

    # Evidence type counts
    evidence_type_counts: dict[str, int] = {t: 0 for t in _EVIDENCE_TYPES}
    for e in evidence_items:
        etype = str(e.get("type", ""))
        if etype in evidence_type_counts:
            evidence_type_counts[etype] += 1
        else:
            evidence_type_counts[etype] = evidence_type_counts.get(etype, 0) + 1

    # Observation strength counts
    obs_strength_counts: dict[str, int] = {}
    for e in evidence_items:
        meta = e.get("metadata", {})
        strength = str(meta.get("observation_strength", "unknown")) if isinstance(meta, dict) else "unknown"
        obs_strength_counts[strength] = obs_strength_counts.get(strength, 0) + 1

    # Source file skipped by reason
    source_skipped_by_reason: dict[str, int] = {}
    for e in evidence_items:
        if str(e.get("type", "")) == EVIDENCE_SOURCE_FILE_SKIPPED:
            meta = e.get("metadata", {})
            reason = str(meta.get("reason", "unknown")) if isinstance(meta, dict) else "unknown"
            source_skipped_by_reason[reason] = source_skipped_by_reason.get(reason, 0) + 1

    limitation_count = obs_strength_counts.get(OBSERVATION_STRENGTH_LIMITATION, 0)

    # Traceability metrics
    findings_with_evidence_pct = float(trace_quality.get("findings_with_evidence_pct", 0))
    orphan_evidence_count = int(trace_quality.get("orphan_evidence_count", 0))
    orphan_finding_count = int(trace_quality.get("orphan_finding_count", 0))
    broken_reference_count = int(trace_quality.get("broken_reference_count", 0))
    trace_grade = str(trace_quality.get("traceability_grade", ""))

    # Claims
    claim_count = int(claims_data.get("summary", {}).get("total_claims", len(claims_list)))

    # Work-package readiness
    wp_count = len(wp_files)
    wp_with_findings = 0
    wp_with_verification = 0
    total_linked_items = 0
    for wp_file in wp_files:
        text = wp_file.read_text(encoding="utf-8", errors="ignore")
        has_linked = "linked_debt_items" in text.lower() or "linked findings" in text.lower()
        has_verification = "verification" in text.lower()
        if has_linked:
            wp_with_findings += 1
        if has_verification:
            wp_with_verification += 1
        # Count linked items heuristically from markdown
        for line in text.split("\n"):
            if line.strip().startswith("- ") and any(fid.startswith("TD-") or fid.startswith("SEC-") for fid in [line]):
                total_linked_items += 1

    wp_with_findings_pct = round(wp_with_findings / wp_count * 100, 1) if wp_count > 0 else 0.0
    wp_with_verification_pct = round(wp_with_verification / wp_count * 100, 1) if wp_count > 0 else 0.0
    grouping_ratio = round(total_linked_items / wp_count, 1) if wp_count > 0 else 0.0

    # Owner areas
    owner_areas: list[str] = sorted(set(
        str(f.get("suggested_owner_area", ""))
        for f in findings
        if f.get("suggested_owner_area")
    ))

    return {
        "schema_version": "1.0",
        "run_id": run_id,
        "timestamp": _utc_now(),
        "findings_by_category": findings_by_category,
        "risk_by_category": risk_by_category,
        "total_risk_score": total_risk,
        "average_risk_score": round(total_risk / len(risk_scores), 1) if risk_scores else 0.0,
        "max_risk_score": max(risk_scores) if risk_scores else 0,
        "evidence_type_counts": evidence_type_counts,
        "evidence_observation_strength_counts": obs_strength_counts,
        "source_file_skipped_by_reason": source_skipped_by_reason,
        "limitation_evidence_count": limitation_count,
        "findings_with_evidence_pct": findings_with_evidence_pct,
        "orphan_evidence_count": orphan_evidence_count,
        "orphan_finding_count": orphan_finding_count,
        "broken_reference_count": broken_reference_count,
        "claim_count": claim_count,
        "work_package_count": wp_count,
        "work_packages_with_linked_findings_pct": wp_with_findings_pct,
        "work_packages_with_verification_steps_pct": wp_with_verification_pct,
        "grouping_ratio": grouping_ratio,
        "traceability_grade": trace_grade,
        "owner_areas": owner_areas,
    }


def write_run_history_snapshot(workspace: Path, snapshot: dict[str, Any]) -> Path:
    """Write .ai-debt/runs/RUN-*-history-snapshot.json."""
    runs_dir = workspace / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_id = snapshot.get("run_id", "unknown")
    path = runs_dir / f"{run_id}-history-snapshot.json"
    path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    return path


# ── S02: Run history index ────────────────────────────────────────────


def build_run_history_index(workspace: Path) -> dict[str, Any]:
    """Build index from run metadata files + enriched snapshots when available.

    Excludes run-history-index.json and history-snapshot files from scanning.
    """
    runs_dir = workspace / "runs"
    runs: list[dict[str, Any]] = []
    warnings: list[dict[str, str]] = []

    if not runs_dir.exists():
        return {
            "schema_version": "1.0",
            "generated_at": _utc_now(),
            "runs": [],
            "warnings": warnings,
        }

    # Collect run metadata files
    metadata_files = sorted(
        [f for f in runs_dir.iterdir() if f.is_file() and _is_run_metadata_file(f)],
        key=lambda f: f.name,
    )

    for mf in metadata_files:
        data = _load_json(mf)
        if not data:
            warnings.append({
                "code": "malformed_run_metadata",
                "path": f".ai-debt/runs/{mf.name}",
                "message": "Skipped malformed run metadata.",
            })
            continue

        run_id = str(data.get("run_id", mf.stem))
        timestamp = str(data.get("timestamp", ""))
        summary = data.get("summary", {})

        entry: dict[str, Any] = {
            "run_id": run_id,
            "timestamp": timestamp,
            "enriched": False,
            "finding_count": int(summary.get("finding_count", 0)),
            "evidence_count": int(summary.get("evidence_count", 0)),
            "work_package_count": int(summary.get("work_package_count", 0)),
            "analysis_unit_count": int(summary.get("analysis_unit_count", 0)),
            "critical_findings": int(summary.get("critical_findings", 0)),
            "high_findings": int(summary.get("high_findings", 0)),
            "medium_findings": int(summary.get("medium_findings", 0)),
            "low_findings": int(summary.get("low_findings", 0)),
        }

        # Check for enriched snapshot
        snapshot_path = runs_dir / f"{run_id}-history-snapshot.json"
        snapshot = _load_json(snapshot_path)
        if snapshot and snapshot.get("run_id"):
            entry["enriched"] = True
            entry["findings_by_category"] = snapshot.get("findings_by_category", {})
            entry["total_risk_score"] = snapshot.get("total_risk_score", 0)
            entry["traceability_grade"] = snapshot.get("traceability_grade", "")
            entry["claim_count"] = snapshot.get("claim_count", 0)
            entry["limitation_evidence_count"] = snapshot.get("limitation_evidence_count", 0)

        runs.append(entry)

    # Sort by timestamp
    runs.sort(key=lambda r: r.get("timestamp", ""))

    return {
        "schema_version": "1.0",
        "generated_at": _utc_now(),
        "runs": runs,
        "warnings": warnings,
    }


def write_run_history_index(workspace: Path, index: dict[str, Any]) -> Path:
    """Write .ai-debt/runs/run-history-index.json."""
    runs_dir = workspace / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / "run-history-index.json"
    path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return path


# ── S03: Finding trend by category ────────────────────────────────────


def compute_finding_trend(index: dict[str, Any]) -> dict[str, Any]:
    """Compute finding count trend across runs."""
    runs = index.get("runs", [])
    warnings: list[dict[str, str]] = []

    if len(runs) < 2:
        return {
            "status": "insufficient_data",
            "latest_run_id": runs[-1].get("run_id") if runs else None,
            "previous_run_id": None,
            "total_delta": None,
            "by_category": None,
            "added_categories": [],
            "removed_categories": [],
            "trajectory": "insufficient_data",
            "warnings": [{
                "code": "partial_historical_data",
                "path": "",
                "message": f"Insufficient data: {len(runs)} run(s). At least 2 runs required.",
            }],
        }

    latest = runs[-1]
    previous = runs[-2]
    latest_count = int(latest.get("finding_count", 0))
    previous_count = int(previous.get("finding_count", 0))
    total_delta = latest_count - previous_count

    both_enriched = bool(latest.get("enriched")) and bool(previous.get("enriched"))

    if not both_enriched:
        trajectory = "improving" if total_delta < 0 else ("worsening" if total_delta > 0 else "stable")
        return {
            "status": "partial",
            "latest_run_id": latest.get("run_id"),
            "previous_run_id": previous.get("run_id"),
            "total_delta": total_delta,
            "by_category": None,
            "added_categories": [],
            "removed_categories": [],
            "trajectory": trajectory,
            "warnings": [{
                "code": "partial_historical_data",
                "path": "",
                "message": "Previous run lacks enriched category snapshot. Category breakdown unavailable.",
            }],
        }

    # Both enriched — full category comparison
    latest_cats: dict[str, int] = latest.get("findings_by_category", {})
    prev_cats: dict[str, int] = previous.get("findings_by_category", {})

    all_categories = sorted(set(list(latest_cats.keys()) + list(prev_cats.keys())))
    by_category: dict[str, dict[str, int]] = {}
    improving_cats = 0
    worsening_cats = 0

    for cat in all_categories:
        prev_val = prev_cats.get(cat, 0)
        latest_val = latest_cats.get(cat, 0)
        delta = latest_val - prev_val
        by_category[cat] = {"previous": prev_val, "latest": latest_val, "delta": delta}
        if delta < 0:
            improving_cats += 1
        elif delta > 0:
            worsening_cats += 1

    added = [c for c in all_categories if c not in prev_cats]
    removed = [c for c in all_categories if c not in latest_cats]

    # Trajectory
    if total_delta < 0:
        if worsening_cats > 0:
            trajectory: str = "mixed"
        else:
            trajectory = "improving"
    elif total_delta > 0:
        trajectory = "worsening"
    else:
        trajectory = "stable"

    return {
        "status": "complete",
        "latest_run_id": latest.get("run_id"),
        "previous_run_id": previous.get("run_id"),
        "total_delta": total_delta,
        "by_category": by_category,
        "added_categories": added,
        "removed_categories": removed,
        "trajectory": trajectory,
        "warnings": warnings,
    }


# ── S04: Risk trend by category ───────────────────────────────────────


def compute_risk_trend(index: dict[str, Any]) -> dict[str, Any]:
    """Compute risk score trend across runs."""
    runs = index.get("runs", [])
    warnings: list[dict[str, str]] = []

    if len(runs) < 2:
        return {
            "status": "insufficient_data",
            "total_risk_delta": None,
            "average_risk_delta": None,
            "max_risk_delta": None,
            "by_category": None,
            "trajectory": "insufficient_data",
            "warnings": [{
                "code": "partial_historical_data",
                "path": "",
                "message": f"Insufficient data: {len(runs)} run(s).",
            }],
        }

    latest = runs[-1]
    previous = runs[-2]

    # Need enriched snapshots for risk data
    if not latest.get("enriched"):
        return {
            "status": "insufficient_data",
            "total_risk_delta": None,
            "average_risk_delta": None,
            "max_risk_delta": None,
            "by_category": None,
            "trajectory": "insufficient_data",
            "warnings": [{"code": "missing_enriched_snapshot", "path": "", "message": "Latest run lacks enriched snapshot."}],
        }

    # Load snapshot for detailed risk data
    workspace = Path(".ai-debt")  # Will be overridden by build_run_history_summary
    # For now, use the data stored in the index entry
    latest_risk = int(latest.get("total_risk_score", 0))

    if not previous.get("enriched"):
        return {
            "status": "partial",
            "total_risk_delta": None,
            "average_risk_delta": None,
            "max_risk_delta": None,
            "by_category": None,
            "trajectory": "insufficient_data",
            "warnings": [{
                "code": "partial_historical_data",
                "path": "",
                "message": "Previous run lacks enriched snapshot. Risk comparison unavailable.",
            }],
        }

    prev_risk = int(previous.get("total_risk_score", 0))
    total_risk_delta = latest_risk - prev_risk

    trajectory = "improving" if total_risk_delta < -5 else ("worsening" if total_risk_delta > 5 else "stable")

    return {
        "status": "complete",
        "total_risk_delta": total_risk_delta,
        "average_risk_delta": None,  # Requires full snapshot data
        "max_risk_delta": None,
        "by_category": None,  # Requires full snapshot data — enriched in S08
        "trajectory": trajectory,
        "warnings": warnings,
    }


# ── S05: Evidence coverage trend ──────────────────────────────────────


def compute_evidence_coverage_trend(
    index: dict[str, Any],
    latest_snapshot: dict[str, Any] | None = None,
    previous_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute evidence coverage trend across runs."""
    runs = index.get("runs", [])
    warnings: list[dict[str, str]] = []

    if len(runs) < 2:
        return {
            "status": "insufficient_data",
            "trajectory": "insufficient_data",
            "warnings": [{
                "code": "partial_historical_data",
                "path": "",
                "message": f"Insufficient data: {len(runs)} run(s).",
            }],
        }

    if not latest_snapshot:
        return {
            "status": "insufficient_data",
            "trajectory": "insufficient_data",
            "warnings": [{"code": "missing_enriched_snapshot", "path": "", "message": "Latest snapshot unavailable."}],
        }

    result: dict[str, Any] = {
        "status": "partial",
        "evidence_type_counts_latest": latest_snapshot.get("evidence_type_counts", {}),
        "warnings": warnings,
    }

    if previous_snapshot:
        result["status"] = "complete"
        # Compute deltas
        prev_ev = previous_snapshot.get("evidence_type_counts", {})
        latest_ev = latest_snapshot.get("evidence_type_counts", {})

        deltas: dict[str, int] = {}
        for etype in set(list(prev_ev.keys()) + list(latest_ev.keys())):
            deltas[etype] = int(latest_ev.get(etype, 0)) - int(prev_ev.get(etype, 0))
        result["evidence_type_count_deltas"] = deltas

        # Key metrics
        result["limitation_evidence_count_delta"] = (
            int(latest_snapshot.get("limitation_evidence_count", 0))
            - int(previous_snapshot.get("limitation_evidence_count", 0))
        )
        result["source_file_skipped_count_delta"] = (
            int(latest_snapshot.get("evidence_type_counts", {}).get(EVIDENCE_SOURCE_FILE_SKIPPED, 0))
            - int(previous_snapshot.get("evidence_type_counts", {}).get(EVIDENCE_SOURCE_FILE_SKIPPED, 0))
        )
        result["findings_with_evidence_pct_delta"] = round(
            float(latest_snapshot.get("findings_with_evidence_pct", 0))
            - float(previous_snapshot.get("findings_with_evidence_pct", 0)), 1
        )
        result["orphan_evidence_count_delta"] = (
            int(latest_snapshot.get("orphan_evidence_count", 0))
            - int(previous_snapshot.get("orphan_evidence_count", 0))
        )
        result["orphan_finding_count_delta"] = (
            int(latest_snapshot.get("orphan_finding_count", 0))
            - int(previous_snapshot.get("orphan_finding_count", 0))
        )
        result["broken_reference_count_delta"] = (
            int(latest_snapshot.get("broken_reference_count", 0))
            - int(previous_snapshot.get("broken_reference_count", 0))
        )

        # Trajectory
        broken_delta = result["broken_reference_count_delta"]
        ev_pct_delta = result["findings_with_evidence_pct_delta"]
        if broken_delta < 0 or ev_pct_delta > 5:
            result["trajectory"] = "improving"
        elif broken_delta > 0 or ev_pct_delta < -5:
            result["trajectory"] = "worsening"
        else:
            result["trajectory"] = "stable"
    else:
        result["warnings"].append({
            "code": "partial_historical_data",
            "path": "",
            "message": "Previous run lacks enriched snapshot. Evidence deltas unavailable.",
        })
        result["trajectory"] = "insufficient_data"

    return result


# ── S06: Work-package readiness trend ─────────────────────────────────


def compute_work_package_readiness_trend(
    index: dict[str, Any],
    latest_snapshot: dict[str, Any] | None = None,
    previous_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute work-package readiness trend across runs."""
    runs = index.get("runs", [])
    warnings: list[dict[str, str]] = []

    if len(runs) < 2:
        return {
            "status": "insufficient_data",
            "trajectory": "insufficient_data",
            "warnings": [{
                "code": "partial_historical_data",
                "path": "",
                "message": f"Insufficient data: {len(runs)} run(s).",
            }],
        }

    latest = runs[-1]
    previous = runs[-2]

    latest_wp = int(latest.get("work_package_count", 0))
    previous_wp = int(previous.get("work_package_count", 0))

    result: dict[str, Any] = {
        "status": "partial",
        "work_package_count_delta": latest_wp - previous_wp,
        "warnings": warnings,
    }

    if latest_snapshot:
        result["grouping_ratio_latest"] = latest_snapshot.get("grouping_ratio", 0)
        result["work_packages_with_linked_findings_pct_latest"] = latest_snapshot.get("work_packages_with_linked_findings_pct", 0)
        result["work_packages_with_verification_steps_pct_latest"] = latest_snapshot.get("work_packages_with_verification_steps_pct", 0)

    if previous_snapshot:
        result["status"] = "complete"
        result["grouping_ratio_previous"] = previous_snapshot.get("grouping_ratio", 0)
        result["work_packages_with_linked_findings_pct_previous"] = previous_snapshot.get("work_packages_with_linked_findings_pct", 0)

        # Trajectory based on grouping ratio and linked-finding %
        prev_linked = float(previous_snapshot.get("work_packages_with_linked_findings_pct", 0))
        latest_linked = float(latest_snapshot.get("work_packages_with_linked_findings_pct", 0))
        if latest_linked > prev_linked and latest_wp <= previous_wp:
            result["trajectory"] = "improving"
        elif latest_linked < prev_linked:
            result["trajectory"] = "worsening"
        else:
            result["trajectory"] = "stable"
    else:
        result["trajectory"] = "insufficient_data"
        result["warnings"].append({
            "code": "partial_historical_data",
            "path": "",
            "message": "Previous run lacks enriched snapshot. WP readiness comparison unavailable.",
        })

    return result


# ── S07: Traceability trend ───────────────────────────────────────────


def _load_traceability_trend(workspace: Path) -> dict[str, Any]:
    """Load existing traceability quality trend."""
    path = workspace / "traceability" / "traceability-quality-trend.json"
    return _load_json(path)


# ── S08: Run history summary ──────────────────────────────────────────


def build_run_history_summary(workspace: Path) -> dict[str, Any]:
    """Build full run history summary from index + supplementary data."""
    index = build_run_history_index(workspace)
    runs = index.get("runs", [])

    # Load enriched snapshots for latest and previous
    latest_snapshot = None
    previous_snapshot = None

    enriched_runs = [r for r in runs if r.get("enriched")]

    if len(runs) >= 1 and runs[-1].get("enriched"):
        latest_snapshot = _load_json(
            workspace / "runs" / f"{runs[-1]['run_id']}-history-snapshot.json"
        )
    if len(runs) >= 2:
        # Find previous enriched run
        for r in reversed(runs[:-1]):
            if r.get("enriched"):
                previous_snapshot = _load_json(
                    workspace / "runs" / f"{r['run_id']}-history-snapshot.json"
                )
                break

    # Compute trends
    finding_trend = compute_finding_trend(index)
    risk_trend = compute_risk_trend(index)
    evidence_trend = compute_evidence_coverage_trend(index, latest_snapshot, previous_snapshot)
    wp_trend = compute_work_package_readiness_trend(index, latest_snapshot, previous_snapshot)
    trace_trend = _load_traceability_trend(workspace)

    # Determine confidence
    enriched_count = len(enriched_runs)
    if len(runs) < 2:
        confidence: str = "insufficient"
    elif enriched_count >= 2:
        confidence = "complete"
    else:
        confidence = "partial"

    # Determine overall trajectory
    overall_trajectory = _compute_overall_trajectory(
        runs, latest_snapshot, previous_snapshot, evidence_trend
    )

    # Merge warnings
    all_warnings: list[dict[str, str]] = list(index.get("warnings", []))
    for trend in [finding_trend, risk_trend, evidence_trend, wp_trend]:
        all_warnings.extend(trend.get("warnings", []))

    return {
        "schema_version": "1.0",
        "generated_at": _utc_now(),
        "run_count": len(runs),
        "enriched_run_count": enriched_count,
        "latest_run_id": runs[-1].get("run_id") if runs else None,
        "overall_trajectory": overall_trajectory,
        "confidence": confidence,
        "finding_trend": finding_trend,
        "risk_trend": risk_trend,
        "evidence_coverage_trend": evidence_trend,
        "work_package_readiness_trend": wp_trend,
        "traceability_trend": trace_trend,
        "warnings": all_warnings,
    }


def _compute_overall_trajectory(
    runs: list[dict[str, Any]],
    latest_snapshot: dict[str, Any] | None,
    previous_snapshot: dict[str, Any] | None,
    evidence_trend: dict[str, Any],
) -> str:
    """Compute overall trajectory using conservative rules."""
    if len(runs) < 2:
        return "insufficient_data"

    if not latest_snapshot or not previous_snapshot:
        # Only total counts available
        latest_count = int(runs[-1].get("finding_count", 0))
        prev_count = int(runs[-2].get("finding_count", 0))
        if latest_count < prev_count:
            return "improving"
        elif latest_count > prev_count:
            return "worsening"
        return "stable"

    # Full enriched comparison
    broken_delta = (
        int(latest_snapshot.get("broken_reference_count", 0))
        - int(previous_snapshot.get("broken_reference_count", 0))
    )
    risk_delta = (
        int(latest_snapshot.get("total_risk_score", 0))
        - int(previous_snapshot.get("total_risk_score", 0))
    )
    ev_pct_latest = float(latest_snapshot.get("findings_with_evidence_pct", 0))
    ev_pct_prev = float(previous_snapshot.get("findings_with_evidence_pct", 0))
    ev_pct_delta = ev_pct_latest - ev_pct_prev

    # Worsening rules
    if broken_delta > 0:
        return "worsening"
    if risk_delta >= 5:
        return "worsening"
    if ev_pct_delta <= -5:
        return "worsening"

    # Improving rules
    if risk_delta <= -5 and broken_delta <= 0 and ev_pct_delta >= 0:
        return "improving"

    return "stable"


def write_run_history_summary(workspace: Path, summary: dict[str, Any]) -> list[Path]:
    """Write JSON + Markdown summary to .ai-debt/reports/."""
    reports_dir = workspace / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    json_path = reports_dir / "run-history-summary.json"
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    paths.append(json_path)

    md_path = reports_dir / "run-history-summary.md"
    md_path.write_text(render_run_history_summary_markdown(summary), encoding="utf-8")
    paths.append(md_path)

    return paths


def render_run_history_summary_markdown(summary: dict[str, Any]) -> str:
    """Render Markdown summary from JSON summary."""
    lines: list[str] = []
    lines.append("# Run History Summary")
    lines.append("")

    run_count = summary.get("run_count", 0)
    enriched_count = summary.get("enriched_run_count", 0)
    confidence = summary.get("confidence", "insufficient")
    trajectory = summary.get("overall_trajectory", "unknown")

    lines.append(f"> Generated from {run_count} run(s) ({enriched_count} enriched). Confidence: **{confidence}**.")
    lines.append("")

    # Overall trajectory
    traj_label = trajectory.replace("_", " ").title()
    if confidence == "partial" and trajectory not in ("insufficient_data",):
        traj_label = f"Preliminary: {traj_label}"
    lines.append(f"## Overall trajectory: {traj_label}")
    lines.append("")

    # Finding trend
    ft = summary.get("finding_trend", {})
    lines.append("## Finding trend")
    lines.append("")
    _render_trend_section(lines, ft)
    if ft.get("by_category"):
        lines.append("| Category | Previous | Latest | Delta |")
        lines.append("|---|---:|---:|---:|")
        for cat, data in sorted(ft["by_category"].items()):
            lines.append(f"| {cat} | {data['previous']} | {data['latest']} | {data['delta']:+d} |")
        lines.append("")

    # Risk trend
    rt = summary.get("risk_trend", {})
    lines.append("## Risk trend")
    lines.append("")
    _render_trend_section(lines, rt)

    # Evidence coverage trend
    et = summary.get("evidence_coverage_trend", {})
    lines.append("## Evidence coverage trend")
    lines.append("")
    _render_trend_section(lines, et)
    if et.get("status") != "insufficient_data":
        limitation_delta = et.get("limitation_evidence_count_delta", 0)
        if limitation_delta and limitation_delta > 0:
            lines.append(f"> ⚠ Limitation evidence changed by {limitation_delta:+d}. This may indicate improved scanner honesty (detecting more constraints) rather than worsening repository health. Correlate with coverage metric trends before drawing conclusions.")
            lines.append("")

    # Work-package readiness trend
    wt = summary.get("work_package_readiness_trend", {})
    lines.append("## Work-package readiness trend")
    lines.append("")
    _render_trend_section(lines, wt)

    # Traceability trend
    tt = summary.get("traceability_trend", {})
    lines.append("## Traceability trend")
    lines.append("")
    if tt:
        lines.append(f"Trajectory: {tt.get('trajectory', 'unknown')}")
        if tt.get("baseline_grade"):
            lines.append(f"Baseline grade: {tt['baseline_grade']}")
        if tt.get("latest_grade"):
            lines.append(f"Latest grade: {tt['latest_grade']}")
    else:
        lines.append("No traceability trend data available.")
    lines.append("")

    # Warnings
    warnings = summary.get("warnings", [])
    if warnings:
        lines.append("## Warnings and limitations")
        lines.append("")
        for w in warnings:
            lines.append(f"- **{w.get('code', 'unknown')}**: {w.get('message', '')}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("> Overall trajectory classification is heuristic, not a scientific measure.")
    lines.append("")

    return "\n".join(lines)


def _render_trend_section(lines: list[str], trend: dict[str, Any]) -> None:
    """Render a trend section header."""
    status = trend.get("status", "unknown")
    trajectory = trend.get("trajectory", "unknown")
    lines.append(f"Status: **{status}** | Trajectory: **{trajectory}**")
    lines.append("")
