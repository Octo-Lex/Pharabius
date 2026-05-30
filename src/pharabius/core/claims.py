"""Minimal claims helpers — markdown rendering and file writers.

All outputs are repository-local sidecar artifacts. No external APIs.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import cast

from pharabius.schemas.claims import (
    GapItem,
    OperationalClaim,
    OperationalClaimsRegister,
    OperationalClaimsRegisterSummary,
    QuestionItem,
)

logger = logging.getLogger(__name__)

CLAIMS_DIR = ".ai-debt/claims"
TRACEABILITY_DIR = ".ai-debt/traceability"

CATEGORY_CLAIM_TYPE: dict[str, str] = {
    "TD-ARCH": "architecture",
    "TD-DEP": "dependency",
    "TD-TEST": "test",
    "TD-SEC": "security",
    "TD-COMP": "compliance",
    "TD-OPS": "operational",
    "TD-BUILD": "operational",
    "TD-OBS": "operational",
    "TD-DATA": "data",
    "TD-DOC": "documentation",
    "TD-CODE": "behavior",
    "TD-PERF": "behavior",
    "TD-CONFIG": "behavior",
    "TD-PROCESS": "behavior",
}

_STATUS_ORDER = {"confirmed": 0, "inferred": 1, "gap": 2}


def _map_claim_type(category: str) -> str:
    """Map a finding category to a claim type."""
    return CATEGORY_CLAIM_TYPE.get(category, "behavior")


def _determine_status(
    evidence_ids: list[str],
    business_impact_basis: str | None = None,
) -> tuple[str, str, bool, str | None]:
    """Determine claim status, confidence, and validation fields.

    Returns:
        (status, confidence, requires_human_validation, validation_question)
    """
    if evidence_ids:
        # Has evidence — check if business impact is inferred
        if business_impact_basis and "inferred" in business_impact_basis.lower():
            return ("inferred", "Medium", True, "Business impact basis is inferred.")
        return ("confirmed", "High", False, None)
    # No evidence — gap
    return (
        "gap",
        "Low",
        True,
        "No direct evidence available. Manual validation required.",
    )


def generate_claims_from_findings(
    findings: list[dict[str, object]],
    warnings: list[str] | None = None,
    *,
    finding_to_wp_map: dict[str, list[str]] | None = None,
) -> list[OperationalClaim]:
    """Generate operational claims from debt-register findings.

    Args:
        findings: List of finding dicts from debt-register.json.
        warnings: Optional list to append warnings.
        finding_to_wp_map: Mapping from finding ID to list of work package IDs.
            If None, linked_work_packages will be empty.

    Returns:
        Sorted list of OperationalClaim.
    """
    if warnings is None:
        warnings = []

    claims: list[OperationalClaim] = []

    for idx, finding in enumerate(findings, 1):
        fid = str(finding.get("id", ""))
        category = str(finding.get("category", "TD-CODE"))
        title = str(finding.get("title", ""))
        description = str(finding.get("description", ""))
        evidence_ids: list[str] = [
            str(x) for x in cast("list[object]", finding.get("evidence_ids") or [])
        ]
        bib_val: object = finding.get("business_impact_basis")
        bib = str(bib_val) if bib_val is not None else None

        # v3.1.0: Read work packages from explicit mapping, not related_findings
        wp_map = finding_to_wp_map or {}
        work_packages: list[str] = wp_map.get(fid, [])

        claim_id = f"CLM-{idx:06d}"

        claim_type = _map_claim_type(category)
        status, confidence, requires_hv, question = _determine_status(evidence_ids, bib)

        statement = title
        if description:
            statement = f"{title}: {description[:200]}"

        source = "finding"

        try:
            claim = OperationalClaim(
                claim_id=claim_id,
                claim_type=claim_type,  # type: ignore[arg-type]
                statement=statement,
                status=status,  # type: ignore[arg-type]
                confidence=confidence,  # type: ignore[arg-type]
                evidence_ids=evidence_ids,
                linked_findings=[fid],
                linked_work_packages=work_packages,
                requires_human_validation=requires_hv,
                validation_question=question,
                source=source,  # type: ignore[arg-type]
            )
            claims.append(claim)
        except Exception as exc:
            warnings.append(f"Skipping claim for {fid}: {exc}")

    # Deterministic sort: status, then type, then finding ID, then claim ID
    claims.sort(
        key=lambda c: (
            _STATUS_ORDER.get(c.status, 99),
            c.claim_type,
            c.linked_findings[0] if c.linked_findings else "",
            c.claim_id,
        )
    )

    return claims


def build_claims_register(
    findings: list[dict[str, object]],
    project_name: str | None = None,
    repository: str | None = None,
    branch: str | None = None,
    commit: str | None = None,
    generated_at: str = "",
    warnings: list[str] | None = None,
    *,
    finding_to_wp_map: dict[str, list[str]] | None = None,
) -> OperationalClaimsRegister:
    """Build a complete claims register from findings."""
    claims = generate_claims_from_findings(
        findings, warnings, finding_to_wp_map=finding_to_wp_map,
    )

    summary = OperationalClaimsRegisterSummary(
        total_claims=len(claims),
        confirmed=sum(1 for c in claims if c.status == "confirmed"),
        inferred=sum(1 for c in claims if c.status == "inferred"),
        gap=sum(1 for c in claims if c.status == "gap"),
        high_confidence=sum(1 for c in claims if c.confidence == "High"),
        medium_confidence=sum(1 for c in claims if c.confidence == "Medium"),
        low_confidence=sum(1 for c in claims if c.confidence == "Low"),
        requiring_validation=sum(1 for c in claims if c.requires_human_validation),
    )

    return OperationalClaimsRegister(
        schema_version="1.0",
        generated_at=generated_at,
        project_name=project_name,
        repository=repository,
        branch=branch,
        commit=commit,
        claims=claims,
        summary=summary,
        warnings=warnings or [],
    )


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


def extract_gaps_from_claims(
    claims: list[OperationalClaim],
    findings: list[dict[str, object]] | None = None,
) -> list[GapItem]:
    """Extract gap items from operational claims."""
    findings = findings or []
    # Build priority lookup
    priority_map: dict[str, str] = {}
    for f in findings:
        fid = str(f.get("id", ""))
        priority_map[fid] = str(f.get("priority", "Medium"))

    gaps: list[GapItem] = []
    gap_counter = 0
    for claim in claims:
        if claim.status != "gap":
            continue
        gap_counter += 1
        fid = claim.linked_findings[0] if claim.linked_findings else ""
        priority = priority_map.get(fid, "Medium")
        severity = "blocking" if priority in ("Critical", "High") else "non_blocking"
        gaps.append(
            GapItem(
                gap_id=f"GAP-{gap_counter:04d}",
                claim_id=claim.claim_id,
                linked_findings=claim.linked_findings,
                linked_work_packages=claim.linked_work_packages,
                severity=severity,  # type: ignore[arg-type]
                question=claim.validation_question or "Manual validation required.",
                reason=claim.statement,
                evidence_ids=claim.evidence_ids,
            )
        )
    return gaps


def extract_questions_from_claims(
    claims: list[OperationalClaim],
) -> list[QuestionItem]:
    """Extract question items from claims requiring human validation."""
    questions: list[QuestionItem] = []
    q_counter = 0

    # Map claim types to question categories
    cat_map: dict[str, str] = {
        "architecture": "architecture",
        "security": "security_compliance",
        "compliance": "security_compliance",
        "test": "testing_verification",
        "behavior": "product_engineering",
    }

    for claim in claims:
        if not claim.requires_human_validation:
            continue
        q_counter += 1
        questions.append(
            QuestionItem(
                question_id=f"Q-{q_counter:04d}",
                claim_id=claim.claim_id,
                linked_findings=claim.linked_findings,
                question=claim.validation_question or "Validation required.",
                category=cat_map.get(claim.claim_type, "general"),  # type: ignore[arg-type]
            )
        )
    return questions


def render_questions_markdown(questions: list[QuestionItem]) -> str:
    """Render questions as Markdown grouped by category."""
    lines: list[str] = []
    lines.append("# Question Registry")
    lines.append("")

    if not questions:
        lines.append("No questions identified.")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"**Total questions**: {len(questions)}")
    lines.append("")

    # Group by category
    categories: dict[str, list[QuestionItem]] = {}
    for q in questions:
        categories.setdefault(q.category, []).append(q)

    for cat_name in sorted(categories):
        lines.append(f"## {cat_name.replace('_', ' ').title()}")
        lines.append("")
        for q in categories[cat_name]:
            lines.append(f"### {q.question_id}")
            lines.append("")
            lines.append(f"**Question**: {q.question}")
            if q.claim_id:
                lines.append(f"**Linked claim**: {q.claim_id}")
            if q.linked_findings:
                lines.append(f"**Linked findings**: {', '.join(q.linked_findings)}")
            lines.append("")

    return "\n".join(lines)


def write_questions_markdown(claims_dir: Path, questions: list[QuestionItem]) -> Path:
    """Write questions.md."""
    claims_dir.mkdir(parents=True, exist_ok=True)
    path = claims_dir / "questions.md"
    path.write_text(render_questions_markdown(questions), encoding="utf-8")
    return path


def compute_confidence_metrics(
    claims: list[OperationalClaim],
    gaps: list[GapItem] | None = None,
) -> dict[str, int | float]:
    """Compute confidence metrics from claims and gaps."""
    gaps = gaps or []
    total = len(claims)
    confirmed = sum(1 for c in claims if c.status == "confirmed")
    inferred = sum(1 for c in claims if c.status == "inferred")
    gap_count = sum(1 for c in claims if c.status == "gap")
    high = sum(1 for c in claims if c.confidence == "High")
    medium = sum(1 for c in claims if c.confidence == "Medium")
    low = sum(1 for c in claims if c.confidence == "Low")
    requires_hv = sum(1 for c in claims if c.requires_human_validation)
    blocking = sum(1 for g in gaps if g.severity == "blocking")
    non_blocking = sum(1 for g in gaps if g.severity == "non_blocking")
    evidence_linked = sum(1 for c in claims if c.evidence_ids)
    evidence_missing = total - evidence_linked
    total_evidence = sum(len(c.evidence_ids) for c in claims)
    avg_evidence = round(total_evidence / total, 2) if total > 0 else 0.0

    return {
        "total_claims": total,
        "confirmed_claims": confirmed,
        "inferred_claims": inferred,
        "gap_claims": gap_count,
        "high_confidence": high,
        "medium_confidence": medium,
        "low_confidence": low,
        "claims_requiring_human_validation": requires_hv,
        "blocking_gaps": blocking,
        "non_blocking_gaps": non_blocking,
        "evidence_linked_claims": evidence_linked,
        "evidence_missing_claims": evidence_missing,
        "average_evidence_per_claim": avg_evidence,
    }


def _compute_warnings(
    claims: list[OperationalClaim],
) -> list[str]:
    """Warn about high-priority findings without confirmed claims."""
    warnings: list[str] = []
    for c in claims:
        if c.status != "confirmed" and c.confidence == "High":
            fid = c.linked_findings[0] if c.linked_findings else "unknown"
            warnings.append(f"High-priority finding {fid} lacks confirmed claim ({c.claim_id})")
    return warnings


def render_confidence_report(
    claims: list[OperationalClaim],
    gaps: list[GapItem] | None = None,
) -> str:
    """Render confidence-report.md content."""
    metrics = compute_confidence_metrics(claims, gaps)
    warnings = _compute_warnings(claims)

    lines: list[str] = []
    lines.append("# Confidence Report")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|---|---:|")
    for key in (
        "total_claims",
        "confirmed_claims",
        "inferred_claims",
        "gap_claims",
        "claims_requiring_human_validation",
    ):
        label = key.replace("_", " ").title()
        lines.append(f"| {label} | {metrics[key]} |")
    lines.append("")

    # Claims by Confidence
    lines.append("## Claims by Confidence")
    lines.append("")
    lines.append("| Confidence | Count |")
    lines.append("|---|---:|")
    lines.append(f"| High | {metrics['high_confidence']} |")
    lines.append(f"| Medium | {metrics['medium_confidence']} |")
    lines.append(f"| Low | {metrics['low_confidence']} |")
    lines.append("")

    # Gap Summary
    lines.append("## Gap Summary")
    lines.append("")
    lines.append(f"- **Blocking gaps**: {metrics['blocking_gaps']}")
    lines.append(f"- **Non-blocking gaps**: {metrics['non_blocking_gaps']}")
    lines.append("")

    # Traceability Density
    lines.append("## Traceability Density")
    lines.append("")
    lines.append(f"- **Evidence-linked claims**: {metrics['evidence_linked_claims']}")
    lines.append(f"- **Evidence-missing claims**: {metrics['evidence_missing_claims']}")
    lines.append(f"- **Average evidence per claim**: {metrics['average_evidence_per_claim']}")
    lines.append("")

    # Warnings
    if warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    # Interpretation note
    lines.append("## Interpretation Notes")
    lines.append("")
    lines.append(
        "Confidence distribution is not a factual-precision measurement. "
        "It indicates traceability and uncertainty posture based on "
        "available repository evidence."
    )
    lines.append("")

    return "\n".join(lines)


def write_confidence_report(
    claims_dir: Path,
    claims: list[OperationalClaim],
    gaps: list[GapItem] | None = None,
) -> Path:
    """Write confidence-report.md."""
    claims_dir.mkdir(parents=True, exist_ok=True)
    path = claims_dir / "confidence-report.md"
    path.write_text(render_confidence_report(claims, gaps), encoding="utf-8")
    return path
