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
) -> list[TicketDraft]:
    """Generate Markdown ticket drafts from work packages.

    Args:
        workspace: Path to .ai-debt directory.
        output_dir: Override output directory. Defaults to workspace/ticket-drafts/.

    Returns:
        List of TicketDraft models for generated drafts.
    """
    wp_dir = workspace / "work-packages"
    if not wp_dir.exists() or not wp_dir.is_dir():
        logger.warning("No work-packages directory found")
        return []

    wp_files = sorted(wp_dir.glob("*.md"))
    if not wp_files:
        logger.warning("No work package files found")
        return []

    register = _load_debt_register(workspace)
    if output_dir is None:
        output_dir = workspace / "ticket-drafts"
    output_dir.mkdir(parents=True, exist_ok=True)

    drafts: list[TicketDraft] = []
    for wp_path in wp_files:
        parsed = parse_work_package_markdown(wp_path)
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
        )

        # Write Markdown file
        md_path = output_dir / ticket_filename(ticket_id)
        md_path.write_text(render_ticket_markdown(draft), encoding="utf-8")

        drafts.append(draft)

    return drafts


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
    lines.append("## Status")
    lines.append("")
    lines.append(
        "Repository-local ticket drafts generated by Pharabius. No external tickets were created."
    )
    lines.append("")

    s = index.summary
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Total drafts | {s.total_drafts} |")
    lines.append(f"| Included drafts | {s.included_drafts} |")
    lines.append(f"| Excluded by review | {s.excluded_by_review} |")
    lines.append(f"| Deferred | {s.deferred} |")
    lines.append(f"| False positive | {s.false_positive} |")
    lines.append(f"| Unreviewed | {s.unreviewed} |")
    lines.append("")

    if index.drafts:
        lines.append("## Drafts")
        lines.append("")
        lines.append("| Ticket Draft | Source | Priority | Risk Score | Linked Debt Items | Path |")
        lines.append("|---|---|---|---:|---|---|")
        for d in index.drafts:
            linked = ", ".join(d.linked_debt_items) if d.linked_debt_items else "—"
            pri = d.priority or "—"
            score = str(d.risk_score) if d.risk_score is not None else "—"
            lines.append(
                f"| {d.ticket_id} | {d.source_id} | {pri} "
                f"| {score} | {linked} | `{d.artifact_path}` |"
            )
        lines.append("")

    return "\n".join(lines)


def write_ticket_draft_summary(index: TicketDraftIndex, reports_dir: Path) -> Path:
    """Write the Markdown ticket draft summary to disk."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "ticket-draft-summary.md"
    path.write_text(render_ticket_draft_summary(index), encoding="utf-8")
    return path
