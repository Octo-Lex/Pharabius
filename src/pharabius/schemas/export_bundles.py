"""Schema models for export bundle artifacts.

Export bundles are repository-local handoff artifacts that prepare
Pharabius ticket drafts for external tracker import. No external
tracker API writes occur.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TrackerKind(StrEnum):
    """Supported external tracker kinds."""

    JIRA = "jira"
    LINEAR = "linear"
    GITHUB_ISSUES = "github-issues"
    AZURE_DEVOPS = "azure-devops"


class ExportBundleFormat(StrEnum):
    """Supported export bundle file formats."""

    MARKDOWN = "markdown"
    CSV = "csv"
    YAML = "yaml"
    JSON = "json"


class ExportBundleArtifact(BaseModel):
    """A single artifact within an export bundle."""

    tracker: TrackerKind
    format: ExportBundleFormat
    relative_path: str
    description: str = ""
    ticket_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExportBundleSummary(BaseModel):
    """Summary counts for an export bundle manifest."""

    total_bundles: int = 0
    total_artifacts: int = 0
    total_tickets: int = 0
    trackers: list[TrackerKind] = Field(default_factory=list)


class ExportBundleManifest(BaseModel):
    """Manifest for the export bundle directory."""

    schema_version: str = "1.0"
    tool_version: str = ""
    generated_at: str = ""
    repository: str | None = None
    commit: str | None = None
    source_ticket_drafts: str = ".ai-debt/ticket-drafts/ticket-drafts.json"
    summary: ExportBundleSummary = Field(default_factory=ExportBundleSummary)
    artifacts: list[ExportBundleArtifact] = Field(default_factory=list)
