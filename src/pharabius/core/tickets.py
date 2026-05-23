"""Ticket draft generation helpers.

Pure deterministic functions for ticket ID mapping and filename generation.
Generation functions for Markdown ticket drafts from work packages.
No network, no external tracker integration, no canonical mutation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC
from pathlib import Path
from typing import Any

from pharabius.schemas.tickets import (
    TicketDraft,
    TicketDraftIndex,
    TicketDraftSourceArtifacts,
    TicketDraftSummary,
    TicketDraftValidationIssue,
)

logger = logging.getLogger(__name__)


# ── Deterministic ID helpers ──────────────────────────────────────────


def ticket_id_for_work_package(work_package_id: str) -> str:
    """Map a work package ID to a deterministic ticket draft ID.

    WP-001 → TICKET-WP-001
    """
    return f"TICKET-{work_package_id}"


def ticket_id_for_finding(finding_id: str) -> str:
    """Map a finding ID to a deterministic ticket draft ID (reserved).

    TD-ARCH-001 → TICKET-TD-ARCH-001
    """
    return f"TICKET-{finding_id}"


def ticket_filename(ticket_id: str) -> str:
    """Map a ticket ID to its Markdown filename.

    TICKET-WP-001 → TICKET-WP-001.md
    """
    return f"{ticket_id}.md"


# ── Work package parsing ───────────────────────────────────────────────


@dataclass(frozen=True)
class ParsedWorkPackage:
    """Extracted data from a work package Markdown file."""

    id: str
    title: str
    path: Path
    linked_debt_items: list[str] = field(default_factory=list)
    objective: str | None = None
    current_risk: str | None = None
    recommended_engineering_approach: list[str] = field(default_factory=list)
    expected_affected_areas: list[str] = field(default_factory=list)
    verification_recommendations: list[str] = field(default_factory=list)
    risks_and_cautions: list[str] = field(default_factory=list)
    definition_of_done: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    estimated_effort: str | None = None


def _extract_section(content: str, heading: str) -> str:
    """Extract text between a ## heading and the next ## heading."""
    pattern = rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _extract_list_items(section_text: str) -> list[str]:
    """Extract bullet-point list items from section text."""
    items: list[str] = []
    for line in section_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip().strip("`"))
        elif re.match(r"^\d+\.\s", stripped):
            items.append(re.sub(r"^\d+\.\s+", "", stripped))
    return items


def parse_work_package_markdown(path: Path) -> ParsedWorkPackage:
    """Parse a Pharabius work package Markdown file."""
    content = path.read_text(encoding="utf-8")

    # Extract ID from filename: WP-001-slug.md → WP-001
    stem = path.stem
    wp_id_match = re.match(r"^(WP-\d+)", stem)
    wp_id = wp_id_match.group(1) if wp_id_match else stem

    # Title from first heading
    title_match = re.search(r"^# Work Package: (.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else stem

    # Extract sections
    linked_raw = _extract_section(content, "Linked Debt Items")
    linked = _extract_list_items(linked_raw)

    objective_raw = _extract_section(content, "Objective")
    objective = objective_raw if objective_raw else None

    current_risk_raw = _extract_section(content, "Current Risk")
    current_risk = current_risk_raw if current_risk_raw else None

    approach_raw = _extract_section(content, "Recommended Engineering Approach")
    approach = _extract_list_items(approach_raw)

    areas_raw = _extract_section(content, "Expected Affected Areas")
    areas = _extract_list_items(areas_raw)

    verification_raw = _extract_section(content, "Verification Recommendations")
    verification = _extract_list_items(verification_raw)

    risks_raw = _extract_section(content, "Risks and Cautions")
    risks = _extract_list_items(risks_raw)

    dod_raw = _extract_section(content, "Definition of Done")
    dod = _extract_list_items(dod_raw)

    evidence_raw = _extract_section(content, "Evidence")
    evidence = _extract_list_items(evidence_raw)

    effort_raw = _extract_section(content, "Estimated Effort")
    effort = effort_raw.strip() if effort_raw else None

    return ParsedWorkPackage(
        id=wp_id,
        title=title,
        path=path,
        linked_debt_items=linked,
        objective=objective,
        current_risk=current_risk,
        recommended_engineering_approach=approach,
        expected_affected_areas=areas,
        verification_recommendations=verification,
        risks_and_cautions=risks,
        definition_of_done=dod,
        evidence=evidence,
        estimated_effort=effort,
    )


# ── Finding enrichment ─────────────────────────────────────────────────


def _load_debt_register(workspace: Path) -> dict[str, Any] | None:
    """Load debt-register.json. Returns None if missing."""
    path = workspace / "debt-register.json"
    if not path.exists():
        return None
    data: dict[str, Any] | None = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def _find_finding(register: dict[str, Any], finding_id: str) -> dict[str, Any] | None:
    """Find a finding by ID in the register."""
    for f in register.get("findings", []):
        if isinstance(f, dict) and f.get("id") == finding_id:
            return f
    return None


def _highest_priority_and_score(
    register: dict[str, Any], finding_ids: list[str]
) -> tuple[str | None, int | None]:
    """Get highest priority and risk score from linked findings."""
    priority_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    best_priority: str | None = None
    best_score: int | None = None
    for fid in finding_ids:
        finding = _find_finding(register, fid)
        if finding:
            score = finding.get("risk_score")
            priority = finding.get("priority")
            if score is not None and (best_score is None or score > best_score):
                best_score = score
            if priority and (
                best_priority is None
                or priority_order.get(priority, 0) > priority_order.get(best_priority, 0)
            ):
                best_priority = priority
    return best_priority, best_score


def _collect_evidence_ids(register: dict[str, Any], finding_ids: list[str]) -> list[str]:
    """Collect evidence IDs from linked findings."""
    all_ids: list[str] = []
    for fid in finding_ids:
        finding = _find_finding(register, fid)
        if finding:
            all_ids.extend(finding.get("evidence_ids", []))
    return sorted(set(all_ids))


def _collect_categories(register: dict[str, Any], finding_ids: list[str]) -> list[str]:
    """Collect unique categories from linked findings."""
    cats: list[str] = []
    for fid in finding_ids:
        finding = _find_finding(register, fid)
        if finding:
            cat = finding.get("category", "")
            if cat and cat not in cats:
                cats.append(cat)
    return cats


# ── Markdown rendering ─────────────────────────────────────────────────


def render_ticket_markdown(draft: TicketDraft) -> str:
    """Render a ticket draft as Markdown."""
    lines: list[str] = []
    lines.append(f"# Ticket: {draft.title}")
    lines.append("")
    lines.append("## Draft Status")
    lines.append("")
    lines.append(
        "Repository-local draft generated by Pharabius. Not created in an external issue tracker."
    )
    lines.append("")

    # Source
    lines.append("## Source")
    lines.append("")
    lines.append(f"- Ticket draft ID: {draft.ticket_id}")
    lines.append(f"- Source work package: {draft.source_id}")
    if draft.linked_debt_items:
        lines.append(f"- Linked debt items: {', '.join(draft.linked_debt_items)}")
    if draft.priority:
        lines.append(f"- Priority: {draft.priority}")
    if draft.risk_score is not None:
        lines.append(f"- Highest risk score: {draft.risk_score}")
    lines.append("")

    # PET Review Status
    lines.append("## PET Review Status")
    lines.append("")
    if draft.review_summary:
        lines.append(f"- Overall decision: {draft.review_decision}")
        for decision, count in sorted(draft.review_summary.items()):
            lines.append(f"  - {decision}: {count}")
        if draft.excluded_linked_debt_items:
            lines.append(
                f"- Excluded linked findings: {', '.join(draft.excluded_linked_debt_items)}"
            )
    else:
        lines.append("No PET review sidecar found. Marked as not reviewed.")
    lines.append("")

    # Body sections from body_markdown (structured content)
    if draft.body_markdown:
        lines.append(draft.body_markdown)
        lines.append("")

    # Labels
    if draft.labels:
        lines.append("## Labels")
        lines.append("")
        lines.append(" ".join(f"`{lbl}`" for lbl in draft.labels))
        lines.append("")

    # Notes
    lines.append("## Notes")
    lines.append("")
    lines.append(
        "This draft is a planning artifact. The Product Engineering Team "
        "owns final ticket creation, assignment, implementation, and verification."
    )
    lines.append("")

    return "\n".join(lines)


# ── Main generation ─────────────────────────────────────────────────────


def generate_ticket_markdown_drafts(
    workspace: Path,
    output_dir: Path | None = None,
    include_deferred: bool = False,
) -> tuple[list[TicketDraft], list[TicketDraftValidationIssue]]:
    """Generate Markdown ticket drafts from work packages.

    Args:
        workspace: Path to .ai-debt directory.
        output_dir: Override output directory. Defaults to workspace/ticket-drafts/.
        include_deferred: Include deferred-only work packages.

    Returns:
        Tuple of (drafts, validation_issues).
    """
    wp_dir = workspace / "work-packages"
    if not wp_dir.exists() or not wp_dir.is_dir():
        logger.warning("No work-packages directory found")
        return [], [
            TicketDraftValidationIssue(
                source_path=str(wp_dir),
                code="missing_work_packages_directory",
                severity="warning",
                message="Work packages directory not found",
            )
        ]

    wp_files = sorted(wp_dir.glob("*.md"))
    if not wp_files:
        logger.warning("No work package files found")
        return [], [
            TicketDraftValidationIssue(
                source_path=str(wp_dir),
                code="empty_work_packages_directory",
                severity="warning",
                message="Work packages directory is empty",
            )
        ]

    register = _load_debt_register(workspace)
    review_decisions = load_review_decisions(workspace)
    if output_dir is None:
        output_dir = workspace / "ticket-drafts"
    output_dir.mkdir(parents=True, exist_ok=True)

    drafts: list[TicketDraft] = []
    validation_issues: list[TicketDraftValidationIssue] = []
    for wp_path in wp_files:
        try:
            parsed = parse_work_package_markdown(wp_path)
        except Exception as exc:
            logger.warning("Failed to parse work package %s: %s", wp_path.name, exc)
            validation_issues.append(
                TicketDraftValidationIssue(
                    source_path=str(wp_path),
                    code="unreadable_work_package",
                    severity="warning",
                    message=f"Failed to parse: {exc}",
                )
            )
            continue

        if not parsed.id or not parsed.id.startswith("WP-"):
            validation_issues.append(
                TicketDraftValidationIssue(
                    source_path=str(wp_path),
                    work_package_id=parsed.id or None,
                    code="missing_work_package_id",
                    severity="warning",
                    message=f"Invalid work package ID: {parsed.id}",
                )
            )
            continue

        ticket_id = ticket_id_for_work_package(parsed.id)
        artifact_path = str(output_dir / ticket_filename(ticket_id))

        # Enrich from debt register
        priority = None
        risk_score = None
        evidence_ids: list[str] = []
        categories: list[str] = []
        if register:
            priority, risk_score = _highest_priority_and_score(register, parsed.linked_debt_items)
            evidence_ids = _collect_evidence_ids(register, parsed.linked_debt_items)
            categories = _collect_categories(register, parsed.linked_debt_items)

        # Build body
        body_sections: list[str] = []

        if parsed.objective:
            body_sections.append("## Summary")
            body_sections.append("")
            body_sections.append(parsed.objective)
            body_sections.append("")

        if parsed.current_risk:
            body_sections.append("## Why This Matters")
            body_sections.append("")
            body_sections.append(parsed.current_risk)
            body_sections.append("")

        if parsed.expected_affected_areas:
            body_sections.append("## Scope")
            body_sections.append("")
            for area in parsed.expected_affected_areas:
                body_sections.append(f"- {area}")
            body_sections.append("")

        if parsed.recommended_engineering_approach:
            body_sections.append("## Recommended Engineering Approach")
            body_sections.append("")
            for i, step in enumerate(parsed.recommended_engineering_approach, 1):
                body_sections.append(f"{i}. {step}")
            body_sections.append("")

        if parsed.verification_recommendations:
            body_sections.append("## Verification Recommendations")
            body_sections.append("")
            for item in parsed.verification_recommendations:
                body_sections.append(f"- {item}")
            body_sections.append("")

        if parsed.definition_of_done:
            body_sections.append("## Acceptance Criteria")
            body_sections.append("")
            for item in parsed.definition_of_done:
                body_sections.append(f"- {item}")
            body_sections.append("")

        if parsed.risks_and_cautions:
            body_sections.append("## Risks and Cautions")
            body_sections.append("")
            for item in parsed.risks_and_cautions:
                body_sections.append(f"- {item}")
            body_sections.append("")

        if evidence_ids:
            body_sections.append("## Evidence")
            body_sections.append("")
            for eid in evidence_ids:
                body_sections.append(f"- `{eid}`")
            body_sections.append("")

        body_markdown = "\n".join(body_sections)

        # Content hash
        content = f"{ticket_id}:{parsed.id}:{parsed.title}"
        content_hash = f"sha256:{hashlib.sha256(content.encode()).hexdigest()[:16]}"

        # Labels
        labels = ["technical-debt", "pharabius", *categories]

        # Review classification
        rv_decision, rv_include, rv_summary, rv_excluded = classify_work_package_for_ticketing(
            parsed.linked_debt_items, review_decisions, include_deferred
        )

        if not rv_include:
            # Write excluded draft
            draft = TicketDraft(
                ticket_id=ticket_id,
                title=parsed.title,
                source_type="work_package",
                source_id=parsed.id,
                artifact_path=artifact_path,
                linked_debt_items=parsed.linked_debt_items,
                categories=categories,
                priority=priority,
                risk_score=risk_score,
                labels=sorted(set(labels)),
                content_hash=content_hash,
                body_markdown=body_markdown,
                review_decision=rv_decision,
                status="excluded",
                review_summary=rv_summary,
                excluded_linked_debt_items=rv_excluded,
            )
            drafts.append(draft)
            continue

        draft = TicketDraft(
            ticket_id=ticket_id,
            title=parsed.title,
            source_type="work_package",
            source_id=parsed.id,
            artifact_path=artifact_path,
            linked_debt_items=parsed.linked_debt_items,
            categories=categories,
            priority=priority,
            risk_score=risk_score,
            labels=sorted(set(labels)),
            content_hash=content_hash,
            body_markdown=body_markdown,
            review_decision=rv_decision,
            review_summary=rv_summary,
            excluded_linked_debt_items=rv_excluded,
        )

        # Write Markdown file
        md_path = output_dir / ticket_filename(ticket_id)
        md_path.write_text(render_ticket_markdown(draft), encoding="utf-8")

        drafts.append(draft)

    return drafts, validation_issues


# ── JSON index and summary generation ───────────────────────────────────


def content_hash(markdown: str) -> str:
    """Compute SHA-256 content hash for a Markdown body."""
    return "sha256:" + hashlib.sha256(markdown.encode("utf-8")).hexdigest()[:16]


def _get_repo_metadata(workspace: Path) -> tuple[str | None, str | None, str | None]:
    """Get repository name, commit SHA, and branch."""
    repo_root = workspace.parent
    name: str | None = repo_root.name if repo_root.exists() else None
    commit: str | None = None
    branch: str | None = None
    try:
        import subprocess

        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            timeout=5,
        )
        if r.returncode == 0:
            commit = r.stdout.strip()
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            timeout=5,
        )
        if r.returncode == 0:
            branch = r.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return name, commit, branch


def generate_ticket_draft_index(
    workspace: Path,
    drafts: list[TicketDraft],
    validation_issues: list[TicketDraftValidationIssue] | None = None,
) -> TicketDraftIndex:
    """Generate a TicketDraftIndex from generated drafts."""
    from datetime import datetime

    # Update content hashes from written files
    for draft in drafts:
        md_path = Path(draft.artifact_path)
        if md_path.exists():
            md_body = md_path.read_text(encoding="utf-8")
            draft.content_hash = content_hash(md_body)

    # Summary counts
    total = len(drafts)
    included = sum(1 for d in drafts if d.status == "draft")
    excluded = sum(1 for d in drafts if d.status == "excluded")
    deferred = sum(1 for d in drafts if d.review_decision == "deferred")
    false_pos = sum(1 for d in drafts if d.review_decision == "false_positive")
    unreviewed = sum(1 for d in drafts if d.review_decision == "not_reviewed")

    repo_name, commit, branch = _get_repo_metadata(workspace)

    # Tool version
    try:
        from importlib.metadata import version as get_version

        tool_ver = get_version("pharabius")
    except Exception:
        tool_ver = "1.6.0-dev"

    return TicketDraftIndex(
        tool_version=tool_ver,
        generated_at=datetime.now(UTC).isoformat(),
        repository=repo_name,
        commit=commit,
        branch=branch,
        source_artifacts=TicketDraftSourceArtifacts(
            debt_register=str(workspace / "debt-register.json"),
            work_packages_dir=str(workspace / "work-packages"),
        ),
        summary=TicketDraftSummary(
            total_drafts=total,
            included_drafts=included,
            excluded_by_review=excluded,
            deferred=deferred,
            false_positive=false_pos,
            unreviewed=unreviewed,
        ),
        drafts=sorted(drafts, key=lambda d: d.ticket_id),
        validation_issues=validation_issues or [],
    )


def write_ticket_draft_index(index: TicketDraftIndex, output_dir: Path) -> Path:
    """Write the JSON ticket draft index to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "ticket-drafts.json"
    path.write_text(index.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def render_ticket_draft_summary(index: TicketDraftIndex) -> str:
    """Render a human-readable ticket draft summary."""
    lines: list[str] = []
    lines.append("# Ticket Draft Summary")
    lines.append("")
    lines.append(
        "Repository-local ticket drafts generated by Pharabius. No external tickets were created."
    )
    lines.append("")

    s = index.summary
    included = [d for d in index.drafts if d.status == "draft"]
    skipped = [d for d in index.drafts if d.status == "excluded"]
    review_applied = sum(
        len(d.review_summary) - (1 if "not_reviewed" in d.review_summary else 0)
        for d in index.drafts
    )

    # Generation Summary
    lines.append("## Generation Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|---|---:|")
    lines.append(f"| Work packages scanned | {s.total_drafts} |")
    lines.append(f"| Ticket drafts generated | {len(included)} |")
    lines.append(f"| Work packages skipped | {len(skipped)} |")
    lines.append(f"| Review decisions applied | {review_applied} |")
    lines.append("")

    # Output Artifacts
    lines.append("## Output Artifacts")
    lines.append("")
    lines.append("| Artifact | Path |")
    lines.append("|---|---|")
    lines.append("| Ticket draft index | `.ai-debt/ticket-drafts/ticket-drafts.json` |")
    lines.append("| Markdown drafts | `.ai-debt/ticket-drafts/*.md` |")
    lines.append("")

    # Review Decision Summary
    if review_applied > 0:
        review_counts: dict[str, int] = {}
        for d in index.drafts:
            for decision, count in d.review_summary.items():
                review_counts[decision] = review_counts.get(decision, 0) + count
        lines.append("## Review Decision Summary")
        lines.append("")
        lines.append("| Decision | Count | Behavior |")
        lines.append("|---|---:|---|")
        for decision in sorted(review_counts):
            count = review_counts[decision]
            if decision in ("accepted", "needs-investigation"):
                behavior = "Drafted"
            elif decision == "deferred":
                behavior = "Skipped (use --include-deferred)"
            elif decision in ("rejected", "duplicate", "already-fixed", "risk-accepted"):
                behavior = "Skipped"
            else:
                behavior = "Drafted"
            lines.append(f"| {decision} | {count} | {behavior} |")
        lines.append("")

    # Drafts table
    if included:
        lines.append("## Drafts")
        lines.append("")
        lines.append("| Ticket | Work Package | Priority | Review State | Status | Path |")
        lines.append("|---|---|---|---|---|---|")
        for d in included:
            pri = d.priority or "—"
            review = d.review_decision or "not_reviewed"
            lines.append(
                f"| {d.ticket_id} | {d.source_id} | {pri} "
                f"| {review} | {d.status} | `{d.artifact_path}` |"
            )
        lines.append("")

    # Skipped Items
    if skipped:
        lines.append("## Skipped Items")
        lines.append("")
        lines.append("| Work Package | Reason |")
        lines.append("|---|---|")
        for d in sorted(skipped, key=lambda x: x.source_id):
            reason = d.review_decision or "unknown"
            lines.append(f"| {d.source_id} | {reason} |")
        lines.append("")

    # Validation Issues
    if index.validation_issues:
        lines.append("## Validation Issues")
        lines.append("")
        lines.append("| Source | Code | Severity | Message |")
        lines.append("|---|---|---|---|")
        for vi in index.validation_issues:
            src = vi.work_package_id or vi.source_path
            lines.append(f"| {src} | {vi.code} | {vi.severity} | {vi.message} |")
        lines.append("")

    # Warnings and Limitations
    lines.append("## Warnings and Limitations")
    lines.append("")
    lines.append("- Ticket drafts are local planning artifacts, not external tickets.")
    if s.unreviewed > 0:
        lines.append(f"- {s.unreviewed} draft(s) have not been reviewed via `ai-debt review`.")
    lines.append(
        "- Content should be validated by Product Engineering Teams "
        "before creating tracker tickets."
    )
    lines.append("")

    return "\n".join(lines)


def write_ticket_draft_summary(index: TicketDraftIndex, reports_dir: Path) -> Path:
    """Write the Markdown ticket draft summary to disk."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "ticket-draft-summary.md"
    path.write_text(render_ticket_draft_summary(index), encoding="utf-8")
    return path


# ── PET Review filtering ────────────────────────────────────────────────

# Decision classifications for ticket generation
_EXCLUDE_DECISIONS = {"rejected", "duplicate", "already-fixed", "risk-accepted"}
_FALSE_POSITIVE_DECISIONS = {"rejected", "duplicate"}
_DEFERRED_DECISIONS = {"deferred"}
_INCLUDE_DECISIONS = {"accepted", "needs-investigation"}


def load_review_decisions(workspace: Path) -> dict[str, str]:
    """Load finding_id -> review_decision from the review sidecar.

    Returns empty dict if no review sidecar exists.
    Does not mutate any files.
    """
    review_path = workspace / "review" / "decisions.json"
    if not review_path.exists():
        return {}
    try:
        data = json.loads(review_path.read_text(encoding="utf-8"))
        decisions: dict[str, str] = {}
        for d in data.get("decisions", []):
            if isinstance(d, dict) and "finding_id" in d and "status" in d:
                decisions[d["finding_id"]] = d["status"]
        return decisions
    except (json.JSONDecodeError, OSError):
        logger.warning("Invalid review sidecar, treating as no reviews")
        return {}


def classify_work_package_for_ticketing(
    linked_debt_items: list[str],
    review_decisions: dict[str, str],
    include_deferred: bool = False,
) -> tuple[str, bool, dict[str, int], list[str]]:
    """Classify a work package for ticket draft inclusion.

    Returns:
        (review_decision_label, should_include, review_summary, excluded_items)
    """
    if not linked_debt_items:
        return "not_reviewed", True, {}, []

    summary: dict[str, int] = {}
    excluded: list[str] = []
    has_include = False
    has_deferred = False
    all_excluded = True

    for fid in linked_debt_items:
        decision = review_decisions.get(fid, "not_reviewed")
        summary[decision] = summary.get(decision, 0) + 1

        if decision in _EXCLUDE_DECISIONS:
            excluded.append(fid)
        elif decision in _DEFERRED_DECISIONS:
            has_deferred = True
            all_excluded = False
        elif decision in _INCLUDE_DECISIONS:
            has_include = True
            all_excluded = False
        else:
            # not_reviewed or unknown
            all_excluded = False

    # Determine overall label
    if not review_decisions:
        label = "not_reviewed"
    elif len(set(summary.keys())) == 1:
        label = next(iter(summary.keys()))
    else:
        label = "mixed"

    # Determine inclusion
    if (all_excluded and excluded) or (has_deferred and not has_include and not include_deferred):
        should_include = False
    else:
        should_include = True

    return label, should_include, summary, excluded
