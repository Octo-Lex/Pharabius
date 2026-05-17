from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class DebtFinding(BaseModel):
    id: str
    category: str
    issue_type: str = "technical_debt"
    title: str
    description: str
    severity: str = "Medium"
    confidence: str = "Medium"
    status: str = "Detected"
    locations: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    technical_impact: str
    business_impact: str
    business_impact_basis: str = (
        "Inferred from repository evidence. Validate with Product Engineering Team."
    )
    risk_score: int
    priority: str
    risk_breakdown: dict[str, Any] = Field(default_factory=dict)
    remediation_effort: str = "Medium"
    recommended_action: str
    verification_recommendations: list[str] = Field(default_factory=list)
    risks_and_cautions: list[str] = Field(default_factory=list)
    suggested_owner_area: str = ""
    related_findings: list[str] = Field(default_factory=list)
    analysis_unit_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class DebtRegisterSummary(BaseModel):
    total_findings: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    top_categories: list[str] = Field(default_factory=list)


class DebtRegister(BaseModel):
    schema_version: str = "1.0"
    project_name: str = ""
    repository: str = ""
    commit: str = ""
    branch: str = ""
    generated_at: str = Field(default_factory=utc_now_iso)
    summary: DebtRegisterSummary = Field(default_factory=DebtRegisterSummary)
    findings: list[DebtFinding] = Field(default_factory=list)
