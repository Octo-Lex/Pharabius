"""Analysis Unit IR — semantic groupings of repository evidence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class AnalysisUnit(BaseModel):
    """A semantically meaningful engineering area in the repository."""

    schema_version: str = "1.0"
    analysis_unit_id: str
    unit_type: str
    name: str
    root_path: str
    files: list[str] = Field(default_factory=list)
    primary_files: list[str] = Field(default_factory=list)
    related_tests: list[str] = Field(default_factory=list)
    related_docs: list[str] = Field(default_factory=list)
    related_configs: list[str] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    manifests: list[str] = Field(default_factory=list)
    deployment_files: list[str] = Field(default_factory=list)
    infrastructure_files: list[str] = Field(default_factory=list)
    trust_boundary_tags: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: str = "Medium"
    limitations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalysisUnitStore(BaseModel):
    """Collection of all analysis units for a repository."""

    schema_version: str = "1.0"
    repository: str = ""
    generated_at: str = Field(default_factory=utc_now_iso)
    units: list[AnalysisUnit] = Field(default_factory=list)
