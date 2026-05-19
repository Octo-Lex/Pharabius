"""AI enrichment schemas for Pharabius.

Defines strict Pydantic models for AI adapter output.
Every enrichment must reference existing evidence IDs and finding IDs.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


# ── Shared types ────────────────────────────────────────────────────────


class EvidenceReference(BaseModel):
    """Reference to a specific evidence item used in enrichment context."""

    evidence_id: str
    relevance: str = ""
    snippet_used: str = ""


class AIOmittedItems(BaseModel):
    """Record of items omitted from context due to budget constraints."""

    evidence_items: int = 0
    analysis_units: int = 0
    graph_edges: int = 0
    graph_cycles: int = 0
    graph_violations: int = 0


class AIBudgetSummary(BaseModel):
    """Summary of budget usage during context assembly."""

    max_context_chars: int = 0
    used_context_chars: int = 0
    max_evidence_items: int = 0
    used_evidence_items: int = 0
    max_graph_records: int = 0
    used_graph_records: int = 0
    max_analysis_units: int = 0
    used_analysis_units: int = 0


class AIContextSummary(BaseModel):
    """Summary of what was included/excluded from enrichment context."""

    evidence_items_included: int = 0
    evidence_items_omitted: int = 0
    analysis_units_included: int = 0
    analysis_units_omitted: int = 0
    graph_records_included: int = 0
    graph_records_omitted: int = 0
    total_context_chars: int = 0
    budget_limit_chars: int = 0
    omitted_items: AIOmittedItems = Field(default_factory=AIOmittedItems)
    budget_summary: AIBudgetSummary = Field(default_factory=AIBudgetSummary)


class AIUsageSummary(BaseModel):
    """Token/usage statistics from the AI provider call."""

    provider: str = ""
    model: str = ""
    prompt_chars: int = 0
    response_chars: int = 0
    items_processed: int = 0
    items_accepted: int = 0
    items_rejected: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    latency_ms: int = 0
    request_id: str = ""
    provider_error_code: str = ""


class AIBudget(BaseModel):
    """Budget controls for AI context assembly."""

    max_context_chars: int = 30_000
    max_evidence_items: int = 20
    max_graph_edges: int = 10
    max_analysis_units: int = 5
    max_output_chars: int = 10_000
    max_repair_attempts: int = 0
    provider_timeout_seconds: int = 30
    max_provider_retries: int = 0


# ── Enrichment models ──────────────────────────────────────────────────

_VALID_CONFIDENCE = {"High", "Medium", "Low"}


class FindingEnrichment(BaseModel):
    """AI enrichment for a single finding.

    Required fields: finding_id, evidence_ids, confidence, limitations.
    All evidence_ids must exist in evidence.json.
    finding_id must exist in debt-register.json.
    """

    # Required fields
    finding_id: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: str = "Medium"
    limitations: list[str] = Field(
        default_factory=lambda: ["AI-generated enrichment — validate before acting"]
    )

    # Enrichment fields (all optional)
    title_suggestion: str = ""
    explanation: str = ""
    risk_rationale: str = ""
    recommended_action_refinement: str = ""
    verification_refinement: str = ""
    uncertainty_notes: str = ""
    grouping_suggestion: str = ""
    business_impact_narrative: str = ""

    # Cross-references (validated if present)
    analysis_unit_ids: list[str] = Field(default_factory=list)
    graph_ids: list[str] = Field(default_factory=list)

    # Metadata
    evidence_references: list[EvidenceReference] = Field(default_factory=list)
    rejected_claims: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class RejectedAIOutput(BaseModel):
    """Record of an AI output that failed validation."""

    finding_id: str | None = None
    reason: str
    invalid_fields: list[str] = Field(default_factory=list)
    missing_evidence_ids: list[str] = Field(default_factory=list)
    raw_output_hash: str = ""
    timestamp: str = Field(default_factory=_utc_now_iso)


class AIValidationResult(BaseModel):
    """Result of validating a single AI output."""

    enrichment: FindingEnrichment | None = None
    is_valid: bool
    rejection_reasons: list[str] = Field(default_factory=list)
    missing_evidence_ids: list[str] = Field(default_factory=list)
    invalid_fields: list[str] = Field(default_factory=list)
    raw_output_hash: str = ""
    timestamp: str = Field(default_factory=_utc_now_iso)


class AIEnrichmentReport(BaseModel):
    """Top-level enrichment report written to .ai-debt/ai/."""

    schema_version: str = "1.0"
    provider: str = ""
    model: str = ""
    generated_at: str = Field(default_factory=_utc_now_iso)
    repository: str = ""
    commit: str = ""
    context_summary: AIContextSummary = Field(default_factory=AIContextSummary)
    usage: AIUsageSummary = Field(default_factory=AIUsageSummary)
    enrichments: list[FindingEnrichment] = Field(default_factory=list)
    rejections: list[RejectedAIOutput] = Field(default_factory=list)
    is_ai_enriched: bool = True
