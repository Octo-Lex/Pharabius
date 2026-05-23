"""Minimal claims helpers — markdown rendering and file writers.

All outputs are repository-local sidecar artifacts. No external APIs.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pharabius.schemas.claims import OperationalClaimsRegister

logger = logging.getLogger(__name__)

CLAIMS_DIR = ".ai-debt/claims"
TRACEABILITY_DIR = ".ai-debt/traceability"


def render_claims_markdown(register: OperationalClaimsRegister) -> str:
    """Render operational claims register as Markdown."""
    lines: list[str] = []

    lines.append("# Operational Claims Register")
    lines.append("")

    # Header
    if register.project_name:
        lines.append(f"**Project**: {register.project_name}")
    if register.repository:
        lines.append(f"**Repository**: {register.repository}")
    if register.branch:
        lines.append(f"**Branch**: {register.branch}")
    if register.commit:
        lines.append(f"**Commit**: {register.commit}")
    lines.append("")

    # Summary
    s = register.summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total claims**: {s.total_claims}")
    lines.append(f"- Confirmed: {s.confirmed} | Inferred: {s.inferred} | Gaps: {s.gap}")
    lines.append(
        f"- High confidence: {s.high_confidence} | "
        f"Medium: {s.medium_confidence} | Low: {s.low_confidence}"
    )
    lines.append(f"- Requiring human validation: {s.requiring_validation}")
    lines.append("")

    # Claims table
    if register.claims:
        lines.append("## Claims")
        lines.append("")
        lines.append("| ID | Type | Status | Confidence | Statement |")
        lines.append("|---|---|---|---|---|")
        for c in sorted(register.claims, key=lambda x: x.claim_id):
            stmt = c.statement[:80] + ("..." if len(c.statement) > 80 else "")
            lines.append(
                f"| {c.claim_id} | {c.claim_type} | {c.status} | {c.confidence} | {stmt} |"
            )
        lines.append("")

    # Warnings
    if register.warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in register.warnings:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)


def render_gaps_markdown(register: OperationalClaimsRegister) -> str:
    """Render gap claims as a separate Markdown artifact."""
    lines: list[str] = []

    lines.append("# Gap and Question Registry")
    lines.append("")

    gaps = [c for c in register.claims if c.status == "gap"]
    if not gaps:
        lines.append("No gaps identified.")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"**Total gaps**: {len(gaps)}")
    lines.append("")

    for g in sorted(gaps, key=lambda x: x.claim_id):
        lines.append(f"## {g.claim_id}")
        lines.append("")
        lines.append(f"**Type**: {g.claim_type}")
        lines.append(f"**Confidence**: {g.confidence}")
        lines.append(f"**Statement**: {g.statement}")
        if g.validation_question:
            lines.append(f"**Validation Question**: {g.validation_question}")
        if g.linked_findings:
            lines.append(f"**Linked Findings**: {', '.join(g.linked_findings)}")
        lines.append("")

    return "\n".join(lines)


def write_claims_json(claims_dir: Path, register: OperationalClaimsRegister) -> Path:
    """Write operational-claims.json."""
    claims_dir.mkdir(parents=True, exist_ok=True)
    path = claims_dir / "operational-claims.json"
    path.write_text(register.model_dump_json(indent=2), encoding="utf-8")
    return path


def write_claims_markdown(claims_dir: Path, register: OperationalClaimsRegister) -> Path:
    """Write operational-claims.md."""
    claims_dir.mkdir(parents=True, exist_ok=True)
    path = claims_dir / "operational-claims.md"
    path.write_text(render_claims_markdown(register), encoding="utf-8")
    return path


def write_gaps_markdown(claims_dir: Path, register: OperationalClaimsRegister) -> Path:
    """Write gaps.md."""
    claims_dir.mkdir(parents=True, exist_ok=True)
    path = claims_dir / "gaps.md"
    path.write_text(render_gaps_markdown(register), encoding="utf-8")
    return path
