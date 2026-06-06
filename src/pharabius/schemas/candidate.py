"""Candidate finding schema for external evidence promotion (v3.6.0).

Candidate findings are review artifacts, NOT accepted debt findings.
They are stored in a separate artifact (candidate-findings.json)
and never mixed into debt-register.json.

Design rules:
- Candidates are pre-review artifacts.
- Candidates are not detected findings.
- Candidates do not affect severity, priority, risk, work packages,
  tickets, exports, governance metrics, or quality gates.
- Only governed review can promote candidates into accepted findings.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class CandidateProvenance(BaseModel):
    """Provenance metadata for a candidate finding."""

    connector_name: str
    source_format: str
    evidence_count: int
    evidence_ids: list[str]
    source_types: list[str]
    proposed_at: str = Field(default_factory=utc_now_iso)


class CandidateFinding(BaseModel):
    """A finding proposed from external evidence, awaiting review.

    Not an accepted DebtFinding. Must be reviewed before promotion.
    """

    id: str
    category: str
    title: str
    description: str
    severity: str = "Unscored"
    confidence: str = "Low"
    status: str = "Candidate"
    locations: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    risk_score: int = 0
    priority: str = "Unscored"
    provenance: CandidateProvenance
    created_at: str = Field(default_factory=utc_now_iso)


class CandidateFindingsSummary(BaseModel):
    """Summary of candidate findings, separate from DebtRegisterSummary."""

    total_candidates: int = 0
    by_connector: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)
    by_severity: dict[str, int] = Field(default_factory=dict)


class CandidateFindingsArtifact(BaseModel):
    """Artifact stored at .ai-debt/candidate-findings.json.

    Completely separate from debt-register.json.
    """

    schema_version: str = "1.0"
    generated_at: str = Field(default_factory=utc_now_iso)
    summary: CandidateFindingsSummary = Field(default_factory=CandidateFindingsSummary)
    candidates: list[CandidateFinding] = Field(default_factory=list)
