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
            f"Provider '{provider_name}' is not available in v0.8.0. "
            "Available providers: disabled, mock. "
            "Future releases may add external provider support."
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


def _count_evidence_ids(enrichments: list[FindingEnrichment]) -> int:
    """Count unique evidence IDs across enrichments."""
    ids: set[str] = set()
    for enc in enrichments:
        ids.update(enc.evidence_ids)
    return len(ids)


def _write_md_report(report: AIEnrichmentReport, path: Path) -> None:
    """Write human-readable markdown enrichment report."""
    # Deterministic ordering: sort enrichments by finding_id
    sorted_enrichments = sorted(report.enrichments, key=lambda e: e.finding_id)
    # Deterministic ordering: sort rejections by finding_id (unknown last)
    sorted_rejections = sorted(
        report.rejections,
        key=lambda r: r.finding_id or "zzz_unknown",
    )

    evidence_count = _count_evidence_ids(sorted_enrichments)
    omitted = report.context_summary.evidence_items_omitted

    lines: list[str] = [
        "# AI Enrichment Report",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Provider | {report.provider} |",
        f"| Model | {report.model} |",
        f"| Generated | {report.generated_at} |",
        f"| Findings selected for enrichment | {report.usage.items_processed} |",
        f"| Enrichments accepted | {len(sorted_enrichments)} |",
        f"| Enrichments rejected | {len(sorted_rejections)} |",
        f"| Evidence IDs referenced | {evidence_count} |",
        f"| Evidence items omitted (budget) | {omitted} |",
        "",
    ]

    if sorted_enrichments:
        lines.append("## Enrichments")
        lines.append("")
        for enc in sorted_enrichments:
            sorted_evidence = sorted(enc.evidence_ids)
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
            lines.append(f"- **Evidence IDs:** {', '.join(sorted_evidence)}")
            lines.append(f"- **Limitations:** {'; '.join(enc.limitations)}")
            lines.append("")

    if sorted_rejections:
        lines.append("## Rejections")
        lines.append("")
        for rej in sorted_rejections:
            fid = rej.finding_id or "unknown"
            lines.append(f"### {fid}")
            lines.append("")
            lines.append(f"- **Reason:** {rej.reason}")
            if rej.invalid_fields:
                sorted_fields = sorted(rej.invalid_fields)
                lines.append(f"- **Invalid fields:** {', '.join(sorted_fields)}")
            if rej.missing_evidence_ids:
                sorted_missing = sorted(rej.missing_evidence_ids)
                lines.append(f"- **Missing evidence IDs:** {', '.join(sorted_missing)}")
            if rej.raw_output_hash:
                lines.append(f"- **Hash:** {rej.raw_output_hash}")
            lines.append("")

    # Review checklist
    lines.extend(
        [
            "## Review Checklist",
            "",
            "- [ ] Enrichment evidence IDs verified against `evidence.json`",
            "- [ ] No canonical artifacts modified (by design)",
            "- [ ] Limitations reviewed for each enrichment",
            "- [ ] Rejected outputs inspected (if any)",
            "- [ ] Privacy caution acknowledged",
            "- [ ] Sidecar files reviewed before sharing",
            "",
        ]
    )

    # Footer
    lines.extend(
        [
            "---",
            "",
            f"*Generated: {report.generated_at}*",
            "",
            "## Privacy Caution",
            "",
            "Sidecar files may contain summarized repository context. "
            "Review before sharing with external parties.",
            "",
            "External AI providers are not included in v0.7.2. "
            "Future providers may send evidence to third-party services.",
            "",
            "*This report is AI-generated enrichment, not canonical finding data. "
            "Deterministic findings remain in `debt-register.json`. "
            "No canonical artifacts were modified.*",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def preview_context(
    repository_root: Path,
    *,
    max_findings: int = 10,
    finding_id: str | None = None,
    budget: AIBudget | None = None,
) -> dict[str, Any]:
    """Assemble bounded context for preview without calling any provider.

    Returns dict with:
    - findings: list of findings selected for enrichment
    - per_finding_contexts: list of per-finding context dicts
    - summary: aggregated context summary
    - no_provider_called: True
    - no_files_written: True
    """
    if budget is None:
        budget = AIBudget()

    ai_debt_dir = repository_root / ".ai-debt"
    artifacts = load_artifacts(ai_debt_dir)
    register = artifacts.get("register", {})

    if not register.get("findings"):
        return {
            "findings": [],
            "per_finding_contexts": [],
            "summary": AIContextSummary(),
            "no_provider_called": True,
            "no_files_written": True,
        }

    ctx = build_enrichment_context(
        artifacts, max_findings=max_findings, finding_id=finding_id, budget=budget
    )
    context_summary = _aggregate_context_summary(ctx.get("per_finding_contexts", []))

    return {
        "findings": ctx["findings"],
        "per_finding_contexts": ctx.get("per_finding_contexts", []),
        "summary": context_summary,
        "no_provider_called": True,
        "no_files_written": True,
    }


def format_context_preview(preview: dict[str, Any]) -> str:
    """Format context preview dict into human-readable text."""
    findings = preview["findings"]
    summary: AIContextSummary = preview["summary"]
    per_finding = preview.get("per_finding_contexts", [])

    lines = [
        "Context Preview",
        "",
        "No provider was called.",
        "No files were written.",
        "",
        f"Findings selected: {len(findings)}",
    ]

    for fc in per_finding:
        finding = fc.get("finding", {})
        cs = fc.get("context_summary", AIContextSummary())
        fid = finding.get("id", "unknown")
        title = finding.get("title", "")
        lines.append(f"  {fid}: {title}")
        lines.append(f"    Evidence included: {cs.evidence_items_included}")
        lines.append(f"    Evidence omitted: {cs.evidence_items_omitted}")
        lines.append(f"    Analysis units: {cs.analysis_units_included}")
        lines.append(f"    Graph records: {cs.graph_records_included}")

    lines.extend(
        [
            "",
            f"Total evidence included: {summary.evidence_items_included}",
            f"Total evidence omitted: {summary.evidence_items_omitted}",
            f"Total analysis units: {summary.analysis_units_included}",
            f"Total graph records: {summary.graph_records_included}",
            f"Context chars used: {summary.total_context_chars}",
            f"Budget limit: {summary.budget_limit_chars}",
        ]
    )

    return "\n".join(lines)


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
    response = provider.generate_json(prompt, ctx, timeout_seconds=budget.provider_timeout_seconds)

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

    # Check for provider-level errors (timeout, rate-limit, auth, etc.)
    if response.errors and not response.raw_text:
        return AIEnrichmentReport(
            provider=provider_name,
            model=response.usage.model or provider.model,
            repository=str(repository_root),
            usage=response.usage,
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
