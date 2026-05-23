"""Core logic for export bundle generation.

Export bundles are repository-local handoff artifacts that prepare
Pharabius ticket drafts for external tracker import. No external
tracker API writes occur.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pharabius.schemas.export_bundles import (
    ExportBundleArtifact,
    ExportBundleManifest,
    ExportBundleSummary,
    TrackerKind,
)

logger = logging.getLogger(__name__)

EXPORT_BUNDLES_DIR = "export-bundles"


def tracker_slug(tracker: TrackerKind) -> str:
    """Return the directory slug for a tracker kind."""
    return tracker.value


def export_bundles_root(workspace: Path) -> Path:
    """Return the export bundles root directory path."""
    return workspace / EXPORT_BUNDLES_DIR


def tracker_output_dir(workspace: Path, tracker: TrackerKind) -> Path:
    """Return the output directory for a specific tracker."""
    return export_bundles_root(workspace) / tracker_slug(tracker)


def write_export_bundle_manifest(
    output_dir: Path,
    manifest: ExportBundleManifest,
) -> Path:
    """Write the export bundle manifest as pretty JSON.

    Creates the output directory if it does not exist.
    Returns the path to the written manifest file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        manifest.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def build_manifest_from_artifacts(
    artifacts: list[ExportBundleArtifact],
    tool_version: str = "",
    generated_at: str = "",
    repository: str | None = None,
    commit: str | None = None,
) -> ExportBundleManifest:
    """Build a manifest from a list of ExportBundleArtifact models."""
    trackers_seen: set[TrackerKind] = set()
    total_tickets = 0
    for art in artifacts:
        trackers_seen.add(art.tracker)
        total_tickets += art.ticket_count

    return ExportBundleManifest(
        tool_version=tool_version,
        generated_at=generated_at,
        repository=repository,
        commit=commit,
        summary=ExportBundleSummary(
            total_bundles=len(trackers_seen),
            total_artifacts=len(artifacts),
            total_tickets=total_tickets,
            trackers=sorted(trackers_seen, key=lambda t: t.value),
        ),
        artifacts=artifacts,
    )
