"""Run diff engine for temporal comparison (W53-S03).

Compares two debt-register snapshots or run metadata files.
Deterministic, read-only, no network access.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from pharabius.schemas.run_diff import DiffSummary, FindingChange, RunDiff


def _load_findings(path: Path) -> tuple[str, list[dict[str, object]]]:
    """Load findings from a debt-register.json or run metadata file.

    Returns (run_id, findings_list).
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    data: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))

    # Check if this is a run metadata file or a debt register
    if "debt_register_path" in data:
        # Run metadata — extract run_id and load referenced debt register
        run_id = cast(str, data.get("run_id", path.stem))
        dr_path = cast(str, data.get("debt_register_path", ""))
        dr = path.parent.parent / dr_path if dr_path else path
        if dr.exists():
            dr_data: dict[str, object] = json.loads(dr.read_text(encoding="utf-8"))
            findings = cast(list[dict[str, object]], dr_data.get("findings", []))
        else:
            findings = []
        return run_id, findings
    else:
        # Direct debt register
        run_id = cast(str, data.get("run_id", path.stem))
        findings = cast(list[dict[str, object]], data.get("findings", []))
        return run_id, findings


def compute_run_diff(before_path: Path, after_path: Path) -> RunDiff:
    """Compute diff between two analysis runs.

    Args:
        before_path: Path to earlier run or debt register
        after_path: Path to later run or debt register

    Returns:
        RunDiff with new, resolved, and changed findings
    """
    before_id, before_findings = _load_findings(before_path)
    after_id, after_findings = _load_findings(after_path)

    # Index findings by ID
    before_map: dict[str, dict[str, object]] = {}
    for f in before_findings:
        fid = cast(str, f.get("id", ""))
        if fid:
            before_map[fid] = f

    after_map: dict[str, dict[str, object]] = {}
    for f in after_findings:
        fid = cast(str, f.get("id", ""))
        if fid:
            after_map[fid] = f

    before_ids = set(before_map.keys())
    after_ids = set(after_map.keys())

    new_findings = sorted(after_ids - before_ids)
    resolved_findings = sorted(before_ids - after_ids)
    common_ids = before_ids & after_ids

    severity_changes: list[FindingChange] = []
    confidence_changes: list[FindingChange] = []

    for fid in sorted(common_ids):
        bf = before_map[fid]
        af = after_map[fid]

        before_sev = cast(str, bf.get("severity", ""))
        after_sev = cast(str, af.get("severity", ""))
        if before_sev != after_sev:
            severity_changes.append(
                FindingChange(id=fid, from_value=before_sev, to_value=after_sev)
            )

        before_conf = cast(str, bf.get("confidence", ""))
        after_conf = cast(str, af.get("confidence", ""))
        if before_conf != after_conf:
            confidence_changes.append(
                FindingChange(id=fid, from_value=before_conf, to_value=after_conf)
            )

    net_change = len(after_ids) - len(before_ids)

    return RunDiff(
        before_run_id=before_id,
        after_run_id=after_id,
        new_findings=new_findings,
        resolved_findings=resolved_findings,
        severity_changes=severity_changes,
        confidence_changes=confidence_changes,
        summary=DiffSummary(
            before_total=len(before_ids),
            after_total=len(after_ids),
            new_count=len(new_findings),
            resolved_count=len(resolved_findings),
            severity_change_count=len(severity_changes),
            confidence_change_count=len(confidence_changes),
            net_change=net_change,
        ),
    )


def find_latest_runs(ai_debt_dir: Path) -> tuple[Path, Path] | None:
    """Find the two most recent run files in .ai-debt/runs/.

    Returns (before, after) paths or None if fewer than 2 runs exist.
    """
    runs_dir = ai_debt_dir / "runs"
    if not runs_dir.exists():
        return None

    run_files = sorted(runs_dir.glob("RUN-*.json"), key=lambda p: p.stat().st_mtime)
    if len(run_files) < 2:
        return None

    return run_files[-2], run_files[-1]
