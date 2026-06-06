"""Lifecycle history artifact schema.

Append-only, optional artifact for tracking lifecycle state transitions.
Existing runs without this artifact remain valid.
If present, new entries are appended and previous entries are never rewritten.

Design rules:
- Optional: missing file is not an error
- Append-only: existing entries never modified
- No auto-promotion: entries only created by explicit transition operations
- Audit-visible: entries include actor, rationale, timestamp
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class LifecycleEntry(BaseModel):
    """A single lifecycle state transition record.

    Attributes:
        artifact_type: Type of artifact ("finding" or "work_package").
        artifact_id: ID of the artifact that transitioned.
        from_status: Previous status value.
        to_status: New status value.
        transitioned_at: ISO timestamp of the transition.
        actor: Who/what performed the transition ("operator", "system", etc.).
        rationale: Human-readable reason for the transition.
        metadata: Optional additional context.
    """

    artifact_type: str  # "finding" or "work_package"
    artifact_id: str
    from_status: str
    to_status: str
    transitioned_at: str = Field(default_factory=utc_now_iso)
    actor: str = "operator"
    rationale: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class LifecycleHistory(BaseModel):
    """Append-only lifecycle transition history.

    This is an optional artifact. Missing file = no history recorded.
    When present, entries are appended and previous entries are never modified.
    """

    schema_version: str = "1.0"
    entries: list[LifecycleEntry] = Field(default_factory=list)

    def append_entry(self, entry: LifecycleEntry) -> None:
        """Append a new entry to the history.

        Does not modify existing entries.
        """
        self.entries.append(entry)

    def get_entries_for(
        self,
        artifact_type: str,
        artifact_id: str,
    ) -> list[LifecycleEntry]:
        """Get all entries for a specific artifact."""
        return [
            e
            for e in self.entries
            if e.artifact_type == artifact_type and e.artifact_id == artifact_id
        ]

    def latest_entry_for(
        self,
        artifact_type: str,
        artifact_id: str,
    ) -> LifecycleEntry | None:
        """Get the most recent entry for a specific artifact."""
        entries = self.get_entries_for(artifact_type, artifact_id)
        return entries[-1] if entries else None
