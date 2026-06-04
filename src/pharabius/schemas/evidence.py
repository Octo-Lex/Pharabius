from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class EvidenceLocation(BaseModel):
    file: str = ""
    line_start: int | None = None
    line_end: int | None = None


class EvidenceItem(BaseModel):
    evidence_id: str
    source: str = "repository_scan"
    type: str
    category: str
    location: EvidenceLocation = Field(default_factory=EvidenceLocation)
    subject: str = ""
    object: str = ""
    summary: str
    raw_observation: str = ""
    confidence: str = "Medium"
    collected_at: str = Field(
        default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat()
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceStore(BaseModel):
    schema_version: str = "1.0"
    repository: str = ""
    generated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat()
    )
    evidence: list[EvidenceItem] = Field(default_factory=list)


class EvidenceBuilder:
    """Mutable builder for collecting evidence items during scanning."""

    def __init__(self) -> None:
        self._counter = 0
        self.items: list[EvidenceItem] = []

    def add(
        self,
        *,
        type_: str,
        category: str,
        summary: str,
        location_file: str = "",
        line_start: int | None = None,
        line_end: int | None = None,
        subject: str = "",
        object_: str = "",
        raw_observation: str = "",
        confidence: str = "Medium",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._counter += 1

        item = EvidenceItem(
            evidence_id=f"EVD-{self._counter:06d}",
            type=type_,
            category=category,
            location=EvidenceLocation(
                file=location_file,
                line_start=line_start,
                line_end=line_end,
            ),
            subject=subject,
            object=object_,
            summary=summary,
            raw_observation=raw_observation,
            confidence=confidence,
            metadata=metadata or {},
        )

        self.items.append(item)
