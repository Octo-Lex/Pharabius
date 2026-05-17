"""Verification schemas for ai-debt verify."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class VerificationResult(BaseModel):
    """Verification result for a single debt finding."""

    finding_id: str
    verification_status: str = "uncertain"
    confidence: str = "Medium"
    evidence_ids_checked: list[str] = Field(default_factory=list)
    evidence_ids_present: list[str] = Field(default_factory=list)
    evidence_ids_missing: list[str] = Field(default_factory=list)
    analysis_unit_ids_checked: list[str] = Field(default_factory=list)
    analysis_unit_ids_present: list[str] = Field(default_factory=list)
    analysis_unit_ids_missing: list[str] = Field(default_factory=list)
    analysis_units_available: bool = True
    locations_checked: list[str] = Field(default_factory=list)
    locations_present: list[str] = Field(default_factory=list)
    locations_missing: list[str] = Field(default_factory=list)
    still_detected_by_current_analyzer: bool = False
    current_matching_finding_ids: list[str] = Field(default_factory=list)
    work_package_paths: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    notes: list[str] = Field(default_factory=list)


class WorkPackageVerificationResult(BaseModel):
    """Verification result for a single work package."""

    work_package_path: str
    linked_debt_ids: list[str] = Field(default_factory=list)
    status: str = "needs_review"
    notes: list[str] = Field(default_factory=list)


class VerificationReport(BaseModel):
    """Full verification report for a repository."""

    schema_version: str = "1.0"
    repository: str = ""
    generated_at: str = Field(default_factory=utc_now_iso)
    source_debt_register_path: str = ""
    current_evidence_path: str = ""
    current_analysis_units_path: str = ""
    current_analyzer_mode: str = "deterministic-no-ai"
    current_evidence_count: int = 0
    current_analysis_unit_count: int = 0
    total_findings_checked: int = 0
    still_detected_count: int = 0
    evidence_missing_count: int = 0
    partially_supported_count: int = 0
    likely_remediated_count: int = 0
    stale_count: int = 0
    uncertain_count: int = 0
    work_packages_valid: int = 0
    work_packages_stale: int = 0
    work_packages_orphaned: int = 0
    work_packages_needs_review: int = 0
    results: list[VerificationResult] = Field(default_factory=list)
    work_package_results: list[WorkPackageVerificationResult] = Field(default_factory=list)
