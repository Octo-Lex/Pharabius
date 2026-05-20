"""Review decision sidecar — core logic.

Non-canonical PET workflow state.  All operations are read/validate/summarize
except ``init_review_sidecar`` which creates an empty decisions.json.

Safety rules:
- Never write canonical artifacts.
- Never alter debt-register.json.
- Never suppress findings.
- Never modify severity, priority, risk score, evidence IDs, or finding IDs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pharabius.schemas.review import (
    ReviewDecisions,
    ReviewSummary,
    ReviewValidationResult,
    ValidationNotice,
)

REVIEW_DIR = "review"
DECISIONS_JSON = "decisions.json"


# ── Path helpers ──────────────────────────────────────────────────────


def _review_dir(root: Path) -> Path:
    return root / ".ai-debt" / REVIEW_DIR


def _decisions_path(root: Path) -> Path:
    return _review_dir(root) / DECISIONS_JSON


def _debt_register_path(root: Path) -> Path:
    return root / ".ai-debt" / "debt-register.json"


# ── Init ──────────────────────────────────────────────────────────────


def init_review_sidecar(root: Path) -> Path:
    """Create an empty review sidecar directory and decisions.json.

    Returns the path to the created file.

    Raises FileExistsError if decisions.json already exists.
    """
    review_dir = _review_dir(root)
    decisions_path = _decisions_path(root)

    if decisions_path.exists():
        msg = (
            f"Review sidecar already exists: {decisions_path}\n"
            "Delete or rename it before re-initializing."
        )
        raise FileExistsError(msg)

    review_dir.mkdir(parents=True, exist_ok=True)

    sidecar = ReviewDecisions(
        repository=str(root),
        branch="",
        commit="",
    )

    decisions_path.write_text(
        sidecar.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    return decisions_path


# ── Load ──────────────────────────────────────────────────────────────


def load_decisions(root: Path) -> ReviewDecisions | None:
    """Load review decisions from sidecar.

    Returns None if the sidecar does not exist.
    Raises ValueError if the JSON is malformed.
    """
    path = _decisions_path(root)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"Malformed review sidecar JSON: {exc}"
        raise ValueError(msg) from exc

    return ReviewDecisions.model_validate(data)


def _load_finding_ids(root: Path) -> set[str] | None:
    """Load finding IDs from debt-register.json.

    Returns None if debt-register does not exist.
    """
    path = _debt_register_path(root)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    return {f["id"] for f in data.get("findings", []) if "id" in f}


# ── Validate ─────────────────────────────────────────────────────────


def validate_decisions(root: Path) -> ReviewValidationResult:
    """Validate review decisions against debt-register.

    - Unknown finding IDs: warning (not error)
    - Duplicate finding IDs: first kept + warning
    - Invalid status: hard error (caught during load)
    - Missing required fields: hard error (caught during load)
    - Missing debt-register: error
    - Missing review sidecar: error
    - Malformed JSON: error
    """
    notices: list[ValidationNotice] = []

    # Load sidecar
    try:
        sidecar = load_decisions(root)
    except ValueError as exc:
        return ReviewValidationResult(
            valid=False,
            notices=[ValidationNotice(level="error", finding_id="", message=str(exc))],
        )

    if sidecar is None:
        return ReviewValidationResult(
            valid=False,
            notices=[
                ValidationNotice(
                    level="error",
                    finding_id="",
                    message="Review sidecar not found. Run 'ai-debt review --init' first.",
                )
            ],
        )

    # Load canonical findings
    finding_ids = _load_finding_ids(root)
    if finding_ids is None:
        return ReviewValidationResult(
            valid=False,
            notices=[
                ValidationNotice(
                    level="error",
                    finding_id="",
                    message="debt-register.json not found. Run analysis first.",
                )
            ],
        )

    # Track duplicates and unknowns
    seen_ids: dict[str, int] = {}
    unknown_ids: list[str] = []
    duplicate_ids: list[str] = []
    status_counts: dict[str, int] = {}

    for decision in sidecar.decisions:
        fid = decision.finding_id
        status_val = decision.status.value

        # Count statuses
        status_counts[status_val] = status_counts.get(status_val, 0) + 1

        # Duplicate check
        if fid in seen_ids:
            duplicate_ids.append(fid)
            notices.append(
                ValidationNotice(
                    level="warning",
                    finding_id=fid,
                    message=(
                        f"Duplicate decision for {fid} "
                        f"(occurrence {seen_ids[fid] + 1}). First kept."
                    ),
                )
            )
        seen_ids[fid] = seen_ids.get(fid, 0) + 1

        # Unknown finding check
        if fid not in finding_ids:
            unknown_ids.append(fid)
            notices.append(
                ValidationNotice(
                    level="warning",
                    finding_id=fid,
                    message=f"Unknown finding ID: {fid}. May have been removed since review.",
                )
            )

    # Stale decisions: findings in register that have decisions
    decided_ids = {d.finding_id for d in sidecar.decisions}

    # Undecided: findings without decisions
    undecided = sorted(finding_ids - decided_ids)

    # Stale: decisions for findings that no longer exist
    stale = sorted(decided_ids - finding_ids)

    has_errors = any(n.level == "error" for n in notices)

    return ReviewValidationResult(
        valid=not has_errors,
        total_decisions=len(sidecar.decisions),
        notices=notices,
        status_counts=status_counts,
        unknown_finding_ids=unknown_ids,
        duplicate_finding_ids=duplicate_ids,
        stale_finding_ids=stale,
        undecided_finding_ids=undecided,
    )


# ── Summarize ─────────────────────────────────────────────────────────


def summarize_decisions(root: Path) -> ReviewSummary:
    """Produce a human-readable summary of review decisions."""
    sidecar = load_decisions(root)
    finding_ids = _load_finding_ids(root) or set()

    if sidecar is None:
        return ReviewSummary(
            total_findings=len(finding_ids),
            decisions_recorded=0,
            undecided_count=len(finding_ids),
            undecided_findings=sorted(finding_ids),
            warnings=["No review sidecar found. Run 'ai-debt review --init' first."],
        )

    decided_ids = {d.finding_id for d in sidecar.decisions}
    undecided = sorted(finding_ids - decided_ids)
    stale = sorted(decided_ids - finding_ids)

    status_counts: dict[str, int] = {}
    decided_list: list[dict[str, Any]] = []
    seen: set[str] = set()
    warnings: list[str] = []

    for decision in sidecar.decisions:
        fid = decision.finding_id
        status_val = decision.status.value
        status_counts[status_val] = status_counts.get(status_val, 0) + 1

        # Only include first occurrence of each finding
        if fid not in seen:
            seen.add(fid)
            decided_list.append(
                {
                    "finding_id": fid,
                    "status": status_val,
                    "reviewer": decision.reviewer,
                    "reviewed_at": decision.reviewed_at.isoformat(),
                }
            )

    # Sort decided list by finding_id
    decided_list.sort(key=lambda x: x["finding_id"])

    if stale:
        warnings.append(f"Stale decisions (finding no longer exists): {', '.join(stale)}")

    return ReviewSummary(
        total_findings=len(finding_ids),
        decisions_recorded=len(seen),
        undecided_count=len(undecided),
        status_counts=status_counts,
        decided_findings=decided_list,
        undecided_findings=undecided,
        stale_decisions=stale,
        warnings=warnings,
    )


def format_summary_text(summary: ReviewSummary) -> str:
    """Format a ReviewSummary as human-readable text for console output."""
    lines: list[str] = []

    lines.append("Review Decision Summary")
    lines.append("")
    lines.append(f"Total findings:  {summary.total_findings}")
    lines.append(f"Decisions recorded: {summary.decisions_recorded}")
    lines.append(f"Undecided:       {summary.undecided_count}")

    if summary.status_counts:
        lines.append("")
        lines.append("By Status:")
        for status in sorted(summary.status_counts):
            lines.append(f"  {status}: {summary.status_counts[status]}")

    if summary.decided_findings:
        lines.append("")
        lines.append("Decisions:")
        for d in summary.decided_findings:
            reviewer = d.get("reviewer", "")
            reviewer_str = f" | {reviewer}" if reviewer else ""
            lines.append(f"  {d['finding_id']}: {d['status']}{reviewer_str}")

    if summary.undecided_findings:
        lines.append("")
        lines.append("Undecided:")
        for fid in summary.undecided_findings:
            lines.append(f"  {fid}")

    if summary.stale_decisions:
        lines.append("")
        lines.append("Stale (finding no longer exists):")
        for fid in summary.stale_decisions:
            lines.append(f"  {fid}")

    if summary.warnings:
        lines.append("")
        for w in summary.warnings:
            lines.append(f"Warning: {w}")

    return "\n".join(lines)
