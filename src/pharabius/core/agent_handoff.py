"""Agent-handoff contract generation.

Generates a safety/review contract for downstream AI agents and human
operators. This artifact does NOT authorize code modification.
"""

from __future__ import annotations

from pathlib import Path

from pharabius.schemas.claims import GapItem, OperationalClaim, QuestionItem


def render_agent_handoff_contract(
    claims: list[OperationalClaim],
    gaps: list[GapItem] | None = None,
    questions: list[QuestionItem] | None = None,
) -> str:
    """Render agent-handoff-contract.md content."""
    gaps = gaps or []
    questions = questions or []

    confirmed = [c for c in claims if c.status == "confirmed"]
    inferred = [c for c in claims if c.status == "inferred"]
    gap_claims = [c for c in claims if c.status == "gap"]
    blocking = [g for g in gaps if g.severity == "blocking"]

    lines: list[str] = []

    lines.append("# Agent Handoff Contract")
    lines.append("")

    # Purpose
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This contract summarizes what downstream agents may rely on, "
        "what must be preserved, what is inferred, what is blocked by gaps, "
        "and what requires human validation."
    )
    lines.append("")

    # Safety Boundary
    lines.append("## Safety Boundary")
    lines.append("")
    lines.append(
        "This artifact is a **safety and review contract**, not an execution "
        "permission slip. It does not authorize code modification."
    )
    lines.append("")

    # Confirmed Claims
    lines.append("## Reliable Context: Confirmed Claims")
    lines.append("")
    if confirmed:
        for c in sorted(confirmed, key=lambda x: x.claim_id):
            lines.append(f"- **{c.claim_id}** ({c.claim_type}): {c.statement[:120]}")
    else:
        lines.append("No confirmed claims.")
    lines.append("")

    # Inferred Claims
    lines.append("## Caution Context: Inferred Claims")
    lines.append("")
    if inferred:
        for c in sorted(inferred, key=lambda x: x.claim_id):
            lines.append(f"- **{c.claim_id}** ({c.claim_type}): {c.statement[:120]}")
            lines.append(f"  - Treat as hypothesis requiring validation.")
    else:
        lines.append("No inferred claims.")
    lines.append("")

    # Blocking Gaps
    lines.append("## Blocking Gaps")
    lines.append("")
    if blocking:
        for g in sorted(blocking, key=lambda x: x.gap_id):
            lines.append(f"- **{g.gap_id}**: {g.question}")
            if g.linked_work_packages:
                lines.append(f"  - Work package(s): {', '.join(g.linked_work_packages)}")
    else:
        lines.append("No blocking gaps.")
    lines.append("")

    # Human Validation Required
    lines.append("## Human Validation Required")
    lines.append("")
    hv_claims = [c for c in claims if c.requires_human_validation]
    if hv_claims:
        for c in sorted(hv_claims, key=lambda x: x.claim_id):
            q = c.validation_question or "Validation required."
            lines.append(f"- **{c.claim_id}**: {q}")
    else:
        lines.append("No claims require human validation.")
    lines.append("")

    # Preservation Requirements
    lines.append("## Preservation Requirements")
    lines.append("")
    lines.append("- All confirmed claims must remain evidence-backed in future iterations.")
    lines.append("- Inferred claims must not be promoted to confirmed without direct evidence.")
    lines.append("- Blocking gaps must be resolved before work package execution.")
    lines.append("")

    # Allowed Uses
    lines.append("## Allowed Uses")
    lines.append("")
    lines.append("- Use confirmed claims as context for planning.")
    lines.append("- Use inferred claims as hypotheses requiring validation.")
    lines.append("- Use gaps/questions to ask Product Engineering for clarification.")
    lines.append("- Use traceability matrices to inspect evidence relationships.")
    lines.append("- Use work packages as planning inputs, not implementation authority.")
    lines.append("")

    # Forbidden Actions
    lines.append("## Forbidden Actions")
    lines.append("")
    forbidden = [
        "Do not modify production code based solely on this artifact.",
        "Do not change authentication, authorization, data retention, payment, migration, or public API behavior without human approval.",
        "Do not treat inferred claims as confirmed facts.",
        "Do not proceed on work packages with blocking gaps.",
        "Do not call external systems or create issues unless separately authorized by the Product Engineering Team.",
    ]
    for f in forbidden:
        lines.append(f"- {f}")
    lines.append("")

    # Linked Artifacts
    lines.append("## Linked Artifacts")
    lines.append("")
    lines.append("- `.ai-debt/claims/operational-claims.json`")
    lines.append("- `.ai-debt/claims/operational-claims.md`")
    lines.append("- `.ai-debt/claims/confidence-report.md`")
    lines.append("- `.ai-debt/claims/gaps.md`")
    lines.append("- `.ai-debt/claims/questions.md`")
    lines.append("- `.ai-debt/traceability/evidence-finding-matrix.md`")
    lines.append("- `.ai-debt/traceability/finding-claim-matrix.md`")
    lines.append("- `.ai-debt/traceability/claim-workpackage-matrix.md`")
    lines.append("")

    return "\n".join(lines)


def write_agent_handoff_contract(
    ai_debt_dir: Path,
    claims: list[OperationalClaim],
    gaps: list[GapItem] | None = None,
    questions: list[QuestionItem] | None = None,
) -> Path:
    """Write agent-handoff-contract.md to .ai-debt/."""
    ai_debt_dir.mkdir(parents=True, exist_ok=True)
    path = ai_debt_dir / "agent-handoff-contract.md"
    path.write_text(render_agent_handoff_contract(claims, gaps, questions), encoding="utf-8")
    return path
