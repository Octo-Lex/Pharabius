"""AI enrichment orchestration.

Coordinates: artifact loading -> context assembly -> provider call -> validation -> sidecar writing.
Never mutates canonical artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pharabius.ai.adapter import AIAdapter, DisabledAdapter
from pharabius.ai.context import (
    build_enrichment_context,
    get_all_evidence_ids,
    get_all_finding_ids,
    get_all_graph_ids,
    get_all_unit_ids,
    load_artifacts,
)
from pharabius.ai.mock_provider import MockAIAdapter
from pharabius.ai.validator import validate_raw_output
from pharabius.schemas.ai_enrichment import (
    AIBudget,
    AIContextSummary,
    AIEnrichmentReport,
    AIUsageSummary,
    FindingEnrichment,
    RejectedAIOutput,
)


def _get_provider(provider_name: str) -> AIAdapter:
    """Get an AI adapter by name."""
    providers = {
        "disabled": DisabledAdapter,
        "mock": MockAIAdapter,
    }
    cls = providers.get(provider_name)
    if cls is None:
        raise ValueError(
            f"AI provider '{provider_name}' is not available. "
            "Use --provider mock for local testing."
        )
    return cls()


def _build_prompt(context: dict[str, Any]) -> str:
    """Build the enrichment prompt from context."""
    findings = context.get("findings", [])
    n = len(findings)
    return (
        f"Enrich {n} finding(s) with explanations, risk rationale, "
        f"and recommended action refinements. "
        f"Each enrichment must reference the finding's evidence IDs. "
        f"Output JSON with 'enrichments' array. "
        f"Each enrichment must include: finding_id, evidence_ids, "
        f"confidence (High/Medium/Low), and non-empty limitations list."
    )


def _aggregate_context_summary(
    per_finding: list[dict[str, Any]],
) -> AIContextSummary:
    """Aggregate per-finding context summaries into one."""
    total_evidence = sum(
        c.get("context_summary", {}).evidence_items_included
        for c in per_finding
        if hasattr(c.get("context_summary", {}), "evidence_items_included")
    )
    total_omitted = sum(
        c.get("context_summary", {}).evidence_items_omitted
        for c in per_finding
        if hasattr(c.get("context_summary", {}), "evidence_items_omitted")
    )
    total_units = sum(
        c.get("context_summary", {}).analysis_units_included
        for c in per_finding
        if hasattr(c.get("context_summary", {}), "analysis_units_included")
    )
    total_graph = sum(
        c.get("context_summary", {}).graph_records_included
        for c in per_finding
        if hasattr(c.get("context_summary", {}), "graph_records_included")
    )
    return AIContextSummary(
        evidence_items_included=total_evidence,
        evidence_items_omitted=total_omitted,
        analysis_units_included=total_units,
        graph_records_included=total_graph,
    )


def _write_md_report(report: AIEnrichmentReport, path: Path) -> None:
    """Write human-readable markdown enrichment report."""
    lines = [
        "# AI Enrichment Report",
        "",
        f"- **Provider:** {report.provider}",
        f"- **Model:** {report.model}",
        f"- **Generated:** {report.generated_at}",
        f"- **Findings enriched:** {len(report.enrichments)}",
        f"- **Rejections:** {len(report.rejections)}",
        "",
    ]

    if report.enrichments:
        lines.append("## Enrichments")
        lines.append("")
        for enc in report.enrichments:
            lines.append(f"### {enc.finding_id}")
            lines.append("")
            if enc.explanation:
                lines.append(f"**Explanation:** {enc.explanation}")
                lines.append("")
            if enc.risk_rationale:
                lines.append(f"**Risk Rationale:** {enc.risk_rationale}")
                lines.append("")
            if enc.recommended_action_refinement:
                lines.append(f"**Recommended Action:** {enc.recommended_action_refinement}")
                lines.append("")
            if enc.uncertainty_notes:
                lines.append(f"**Uncertainty:** {enc.uncertainty_notes}")
                lines.append("")
            lines.append(f"- **Confidence:** {enc.confidence}")
            lines.append(f"- **Evidence IDs:** {', '.join(enc.evidence_ids)}")
            lines.append(f"- **Limitations:** {'; '.join(enc.limitations)}")
            lines.append("")

    if report.rejections:
        lines.append("## Rejections")
        lines.append("")
        for rej in report.rejections:
            fid = rej.finding_id or "unknown"
            lines.append(f"- **{fid}:** {rej.reason}")
            if rej.invalid_fields:
                lines.append(f"  - Invalid fields: {', '.join(rej.invalid_fields)}")
            lines.append("")

    # Footer
    lines.extend(
        [
            "---",
            "",
            "*This report is AI-generated enrichment, not canonical finding data. "
            "Deterministic findings remain in `debt-register.json`.*",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def _git_value(root: Path, args: list[str]) -> str:
    """Get a git value, returning empty string on any failure."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def enrich_findings(
    repository_root: Path,
    *,
    provider_name: str = "disabled",
    max_findings: int = 10,
    finding_id: str | None = None,
    dry_run: bool = False,
    strict: bool = False,
    budget: AIBudget | None = None,
) -> AIEnrichmentReport:
    """Run AI enrichment pipeline.

    1. Load artifacts
    2. Assemble context
    3. Call provider
    4. Validate output
    5. Write sidecar files (unless dry_run)

    Returns AIEnrichmentReport.
    """
    if budget is None:
        budget = AIBudget()

    ai_debt_dir = repository_root / ".ai-debt"

    # 1. Load artifacts
    artifacts = load_artifacts(ai_debt_dir)
    register = artifacts.get("register", {})

    # 2. Check prerequisites
    if not register.get("findings"):
        return AIEnrichmentReport(
            provider=provider_name,
            model="none",
            repository=str(repository_root),
            usage=AIUsageSummary(provider=provider_name, model="none"),
            enrichments=[],
            rejections=[],
        )

    # 3. Assemble context
    ctx = build_enrichment_context(
        artifacts, max_findings=max_findings, finding_id=finding_id, budget=budget
    )

    findings_to_enrich = ctx["findings"]
    if not findings_to_enrich:
        return AIEnrichmentReport(
            provider=provider_name,
            model="none",
            repository=str(repository_root),
            usage=AIUsageSummary(provider=provider_name, model="none"),
            enrichments=[],
            rejections=[],
        )

    # 4. Get provider and call
    provider = _get_provider(provider_name)
    prompt = _build_prompt(ctx)
    response = provider.generate_json(prompt, ctx)

    # Check for disabled provider
    if response.errors and provider_name == "disabled":
        return AIEnrichmentReport(
            provider=provider_name,
            model="none",
            repository=str(repository_root),
            usage=AIUsageSummary(provider=provider_name, model="none"),
            enrichments=[],
            rejections=[
                RejectedAIOutput(
                    finding_id=None,
                    reason=response.errors[0],
                )
            ],
        )

    # 5. Validate output
    valid_finding_ids = get_all_finding_ids(register)
    valid_evidence_ids = get_all_evidence_ids(artifacts)
    valid_unit_ids = get_all_unit_ids(artifacts) or None
    valid_graph_ids = get_all_graph_ids(artifacts) or None

    raw_json = response.raw_text
    results = validate_raw_output(
        raw_json,
        valid_finding_ids,
        valid_evidence_ids,
        valid_unit_ids,
        valid_graph_ids,
    )

    # 6. Separate valid enrichments from rejections
    enrichments: list[FindingEnrichment] = []
    rejections: list[RejectedAIOutput] = []

    all_valid = True
    for result in results:
        if result.is_valid and result.enrichment:
            enrichments.append(result.enrichment)
        else:
            all_valid = False
            rejections.append(
                RejectedAIOutput(
                    finding_id=result.enrichment.finding_id if result.enrichment else None,
                    reason="; ".join(result.rejection_reasons),
                    invalid_fields=result.invalid_fields,
                    missing_evidence_ids=result.missing_evidence_ids,
                    raw_output_hash=result.raw_output_hash,
                )
            )

    # Strict mode: reject all if any failed
    if strict and not all_valid:
        for enc in enrichments:
            rejections.append(
                RejectedAIOutput(
                    finding_id=enc.finding_id,
                    reason="Strict mode: entire batch rejected due to validation failures",
                )
            )
        enrichments = []

    # 7. Aggregate context summary
    context_summary = _aggregate_context_summary(ctx.get("per_finding_contexts", []))

    # 8. Build report
    report = AIEnrichmentReport(
        provider=provider_name,
        model=response.usage.model or provider.model,
        repository=str(repository_root),
        commit=_git_value(repository_root, ["rev-parse", "--short", "HEAD"]),
        context_summary=context_summary,
        usage=AIUsageSummary(
            provider=provider_name,
            model=response.usage.model or provider.model,
            prompt_chars=response.usage.prompt_chars,
            response_chars=response.usage.response_chars,
            items_processed=len(findings_to_enrich),
            items_accepted=len(enrichments),
            items_rejected=len(rejections),
        ),
        enrichments=enrichments,
        rejections=rejections,
    )

    # 9. Write sidecar files (unless dry_run)
    if not dry_run and provider_name != "disabled":
        ai_dir = ai_debt_dir / "ai"
        ai_dir.mkdir(parents=True, exist_ok=True)

        # Full report JSON
        (ai_dir / "enrichment-report.json").write_text(
            report.model_dump_json(indent=2), encoding="utf-8"
        )

        # Markdown report
        _write_md_report(report, ai_dir / "enrichment-report.md")

        # Finding enrichments only
        (ai_dir / "finding-enrichments.json").write_text(
            json.dumps([e.model_dump() for e in enrichments], indent=2, default=str),
            encoding="utf-8",
        )

        # Rejected outputs
        (ai_dir / "rejected-ai-output.json").write_text(
            json.dumps([r.model_dump() for r in rejections], indent=2, default=str),
            encoding="utf-8",
        )

    return report
