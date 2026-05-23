"""Minimal portfolio helpers — summary writer and markdown renderer.

All outputs are file-based and deterministic. No external APIs are called.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pharabius.schemas.portfolio import (
    PortfolioCategoryRollup,
    PortfolioReadinessRollup,
    PortfolioRepositoryEntry,
    PortfolioRiskRollup,
    PortfolioSummary,
)

logger = logging.getLogger(__name__)

PORTFOLIO_DIR = ".ai-debt/portfolio"

PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]

PRIORITY_WEIGHT: dict[str, int] = {"Critical": 8, "High": 5, "Medium": 3, "Low": 1}


def compute_risk_rollup(entries: list[PortfolioRepositoryEntry]) -> PortfolioRiskRollup:
    """Compute aggregate risk rollup from repository entries."""
    agg: dict[str, int] = {}
    for e in entries:
        for pri, cnt in e.priority_counts.items():
            agg[pri] = agg.get(pri, 0) + cnt
    total = sum(e.total_findings for e in entries)
    highest = _highest_priority(agg)
    return PortfolioRiskRollup(
        total_repositories=len(entries),
        total_findings=total,
        priority_counts=agg,
        highest_priority=highest,
    )


def compute_category_rollup(entries: list[PortfolioRepositoryEntry]) -> PortfolioCategoryRollup:
    """Compute aggregate category rollup from repository entries."""
    agg: dict[str, int] = {}
    for e in entries:
        for cat in e.top_categories:
            # Use top_categories as a signal; full counts not in entry
            agg[cat] = agg.get(cat, 0) + 1
    # Sort by count desc, category asc
    top = sorted(agg, key=lambda c: (-agg[c], c))
    return PortfolioCategoryRollup(category_counts=agg, top_categories=top)


def _repo_risk_sort_key(entry: PortfolioRepositoryEntry) -> tuple[tuple[int, ...], str]:
    """Sort key for repository risk ordering."""
    pc = entry.priority_counts
    priorities = tuple(-pc.get(p, 0) for p in PRIORITY_ORDER)
    return (priorities, entry.repository_id)


def top_risk_repositories(entries: list[PortfolioRepositoryEntry], limit: int = 10) -> list[str]:
    """Return repository IDs ordered by risk concentration."""
    sorted_entries = sorted(entries, key=_repo_risk_sort_key)
    return [e.repository_id for e in sorted_entries[:limit]]


def compute_readiness_rollup(
    entries: list[PortfolioRepositoryEntry],
    warnings: list[str] | None = None,
) -> PortfolioReadinessRollup:
    """Compute readiness rollup from repository entries."""
    if warnings is None:
        warnings = []

    status_counts: dict[str, int] = {}
    needing_review: list[str] = []
    with_tickets = 0
    with_bundles = 0

    for e in entries:
        status_counts[e.validation_status] = status_counts.get(e.validation_status, 0) + 1
        if e.validation_status in ("needs_review", "unknown"):
            needing_review.append(e.repository_id)
        if e.has_ticket_drafts:
            with_tickets += 1
        if e.has_export_bundles:
            with_bundles += 1
        if e.limitations:
            for lim in e.limitations:
                warnings.append(f"{e.repository_id}: {lim}")

    return PortfolioReadinessRollup(
        total_repositories=len(entries),
        with_ticket_drafts=with_tickets,
        with_export_bundles=with_bundles,
        status_counts=status_counts,
        repositories_needing_review=sorted(needing_review),
        warnings=warnings,
    )


def render_validation_rollup_markdown(
    entries: list[PortfolioRepositoryEntry],
    rollup: PortfolioReadinessRollup | None = None,
) -> str:
    """Render validation-rollup.md content."""
    if rollup is None:
        rollup = compute_readiness_rollup(entries)

    lines: list[str] = []
    lines.append("# Portfolio Validation Rollup")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total repositories**: {rollup.total_repositories}")
    lines.append(f"- **With ticket drafts**: {rollup.with_ticket_drafts}")
    lines.append(f"- **With export bundles**: {rollup.with_export_bundles}")
    lines.append("")

    # Readiness by Repository
    if entries:
        lines.append("## Readiness by Repository")
        lines.append("")
        lines.append("| Repository | Readiness | Ticket Drafts | Export Bundles | Notes |")
        lines.append("|---|---|---|---|---|")
        for e in sorted(entries, key=lambda x: x.repository_id):
            notes = ", ".join(e.limitations) if e.limitations else "\u2014"
            td = "yes" if e.has_ticket_drafts else "no"
            eb = "yes" if e.has_export_bundles else "no"
            lines.append(f"| {e.project_name} | {e.validation_status} | {td} | {eb} | {notes} |")
        lines.append("")

    # Repositories Needing Review
    if rollup.repositories_needing_review:
        lines.append("## Repositories Needing Review")
        lines.append("")
        for rid in rollup.repositories_needing_review:
            lines.append(f"- {rid}")
        lines.append("")

    # Warnings
    if rollup.warnings:
        lines.append("## Warnings and Limitations")
        lines.append("")
        for w in rollup.warnings:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)


def write_validation_rollup(
    portfolio_dir: Path,
    entries: list[PortfolioRepositoryEntry],
    rollup: PortfolioReadinessRollup | None = None,
) -> Path:
    """Write validation-rollup.md to disk."""
    portfolio_dir.mkdir(parents=True, exist_ok=True)
    path = portfolio_dir / "validation-rollup.md"
    path.write_text(render_validation_rollup_markdown(entries, rollup), encoding="utf-8")
    return path


def _highest_priority(priority_counts: dict[str, int]) -> str | None:
    """Return the highest priority with a non-zero count."""
    for p in PRIORITY_ORDER:
        if priority_counts.get(p, 0) > 0:
            return p
    return None


def extract_repository_entry(
    repo_path: Path,
    warnings: list[str] | None = None,
) -> PortfolioRepositoryEntry | None:
    """Extract a portfolio entry from a repository's .ai-debt/ directory."""
    if warnings is None:
        warnings = []

    ai_debt = repo_path / ".ai-debt"
    if not ai_debt.is_dir():
        warnings.append(f"Missing .ai-debt/ in {repo_path}")
        return None

    debt_register_path = ai_debt / "debt-register.json"
    if not debt_register_path.exists():
        warnings.append(f"Missing debt-register.json in {repo_path}")
        return PortfolioRepositoryEntry(
            repository_id=repo_path.name,
            project_name=repo_path.name,
            repository_path=str(repo_path),
            validation_status="needs_review",
            limitations=["Missing debt-register.json"],
        )

    try:
        data = json.loads(debt_register_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        warnings.append(f"Malformed debt-register.json in {repo_path}: {exc}")
        return PortfolioRepositoryEntry(
            repository_id=repo_path.name,
            project_name=repo_path.name,
            repository_path=str(repo_path),
            validation_status="needs_review",
            limitations=["Malformed debt-register.json"],
        )

    summary = data.get("summary", {})
    findings = data.get("findings", [])

    priority_counts: dict[str, int] = {}
    for key in ("critical", "high", "medium", "low"):
        val = summary.get(key, 0)
        if val:
            priority_counts[key.capitalize()] = val

    category_counts: dict[str, int] = {}
    for f in findings:
        cat = f.get("category", "unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    top_categories = sorted(category_counts, key=lambda c: category_counts[c], reverse=True)[:5]

    has_ticket_drafts = (ai_debt / "ticket-drafts" / "ticket-drafts.json").exists()
    has_export_bundles = (ai_debt / "export-bundles" / "manifest.json").exists()

    return PortfolioRepositoryEntry(
        repository_id=data.get("repository", repo_path.name) or repo_path.name,
        project_name=data.get("project_name", repo_path.name) or repo_path.name,
        repository_path=str(repo_path),
        branch=data.get("branch"),
        commit=data.get("commit"),
        generated_at=data.get("generated_at"),
        total_findings=summary.get("total_findings", len(findings)),
        priority_counts=priority_counts,
        top_categories=top_categories,
        highest_priority=_highest_priority(priority_counts),
        has_ticket_drafts=has_ticket_drafts,
        has_export_bundles=has_export_bundles,
        validation_status="complete",
    )


def collect_portfolio_repository_entries(
    repo_paths: list[Path],
    warnings: list[str] | None = None,
) -> list[PortfolioRepositoryEntry]:
    """Collect portfolio entries from multiple repositories."""
    if warnings is None:
        warnings = []

    entries: list[PortfolioRepositoryEntry] = []
    seen_ids: set[str] = set()

    for rp in repo_paths:
        entry = extract_repository_entry(rp, warnings)
        if entry is None:
            continue
        if entry.repository_id in seen_ids:
            warnings.append(f"Duplicate repository_id: {entry.repository_id}")
            continue
        seen_ids.add(entry.repository_id)
        entries.append(entry)

    entries.sort(key=lambda e: e.repository_id)
    return entries


PORTFOLIO_SUMMARY_JSON = "portfolio-summary.json"
PORTFOLIO_SUMMARY_MD = "portfolio-summary.md"
REPOSITORY_INDEX_JSON = "repository-index.json"


def write_portfolio_json(portfolio_dir: Path, summary: PortfolioSummary) -> Path:
    """Write portfolio-summary.json to disk.

    Args:
        portfolio_dir: Target directory for portfolio artifacts.
        summary: Portfolio summary data.

    Returns:
        Path to the written JSON file.
    """
    portfolio_dir.mkdir(parents=True, exist_ok=True)
    path = portfolio_dir / PORTFOLIO_SUMMARY_JSON
    path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    return path


def write_repository_index(portfolio_dir: Path, summary: PortfolioSummary) -> Path:
    """Write repository-index.json to disk.

    Args:
        portfolio_dir: Target directory for portfolio artifacts.
        summary: Portfolio summary data.

    Returns:
        Path to the written JSON file.
    """
    portfolio_dir.mkdir(parents=True, exist_ok=True)
    index = [
        {
            "repository_id": r.repository_id,
            "project_name": r.project_name,
            "repository_path": r.repository_path,
            "branch": r.branch,
            "commit": r.commit,
            "total_findings": r.total_findings,
            "highest_priority": r.highest_priority,
            "validation_status": r.validation_status,
        }
        for r in summary.repositories
    ]
    path = portfolio_dir / REPOSITORY_INDEX_JSON
    path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    return path


def render_portfolio_markdown(summary: PortfolioSummary) -> str:
    """Render portfolio summary as deterministic Markdown.

    Args:
        summary: Portfolio summary data.

    Returns:
        Markdown string.
    """
    lines: list[str] = []

    lines.append("# Portfolio Summary")
    lines.append("")
    lines.append(
        f"Generated at: {summary.generated_at or 'unknown'}  "
        f"Tool version: {summary.tool_version or 'unknown'}  "
        f"Schema version: {summary.schema_version}"
    )
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Repositories**: {summary.risk_rollup.total_repositories}")
    lines.append(f"- **Total findings**: {summary.risk_rollup.total_findings}")
    if summary.risk_rollup.highest_priority:
        lines.append(f"- **Highest priority**: {summary.risk_rollup.highest_priority}")
    lines.append("")

    # Repositories
    if summary.repositories:
        lines.append("## Repositories")
        lines.append("")
        lines.append("| Repository | Findings | Highest Priority | Status |")
        lines.append("|---|---:|---|---|")
        for r in summary.repositories:
            lines.append(
                f"| {r.project_name} | {r.total_findings} "
                f"| {r.highest_priority or '—'} "
                f"| {r.validation_status} |"
            )
        lines.append("")

    # Aggregate Risk
    rr = summary.risk_rollup
    if rr.priority_counts:
        lines.append("## Aggregate Risk")
        lines.append("")
        lines.append("| Priority | Count |")
        lines.append("|---|---:|")
        for pri in sorted(rr.priority_counts):
            lines.append(f"| {pri} | {rr.priority_counts[pri]} |")
        lines.append("")

    # Category Rollup
    cr = summary.category_rollup
    if cr.category_counts:
        lines.append("## Category Rollup")
        lines.append("")
        lines.append("| Category | Count |")
        lines.append("|---|---:|")
        for cat in sorted(cr.category_counts):
            lines.append(f"| {cat} | {cr.category_counts[cat]} |")
        lines.append("")

    # Readiness Rollup
    rdr = summary.readiness_rollup
    if rdr.status_counts:
        lines.append("## Readiness Rollup")
        lines.append("")
        lines.append("| Status | Count |")
        lines.append("|---|---:|")
        for status in sorted(rdr.status_counts):
            lines.append(f"| {status} | {rdr.status_counts[status]} |")
        if rdr.repositories_needing_review:
            lines.append("")
            lines.append("Repositories needing review:")
            for repo_id in rdr.repositories_needing_review:
                lines.append(f"- {repo_id}")
        lines.append("")

    # Validation Warnings
    if summary.validation_warnings:
        lines.append("## Validation Warnings")
        lines.append("")
        for w in summary.validation_warnings:
            lines.append(f"- {w}")
        lines.append("")

    # Limitations
    if summary.limitations:
        lines.append("## Limitations")
        lines.append("")
        for lim in summary.limitations:
            lines.append(f"- {lim}")
        lines.append("")

    return "\n".join(lines)


def write_portfolio_markdown(portfolio_dir: Path, summary: PortfolioSummary) -> Path:
    """Write portfolio-summary.md to disk.

    Args:
        portfolio_dir: Target directory for portfolio artifacts.
        summary: Portfolio summary data.

    Returns:
        Path to the written Markdown file.
    """
    portfolio_dir.mkdir(parents=True, exist_ok=True)
    path = portfolio_dir / PORTFOLIO_SUMMARY_MD
    path.write_text(render_portfolio_markdown(summary), encoding="utf-8")
    return path
