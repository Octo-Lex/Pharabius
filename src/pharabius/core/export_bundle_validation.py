"""Export bundle manifest validation.

Validates .ai-debt/export-bundles/manifest.json for internal consistency.
No external tracker API calls are made.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from pharabius.schemas.export_bundles import TrackerBundleCompleteness

logger = logging.getLogger(__name__)

SUPPORTED_TRACKERS = {"jira", "linear", "github-issues", "azure-devops"}


class ExportBundleValidationIssue(BaseModel):
    """A single validation issue found in an export bundle manifest."""

    severity: str  # "error" or "warning"
    code: str
    message: str
    tracker: str | None = None
    artifact_path: str | None = None


class ExportBundleValidationResult(BaseModel):
    """Result of validating an export bundle manifest."""

    valid: bool
    errors: list[ExportBundleValidationIssue] = Field(default_factory=list)
    warnings: list[ExportBundleValidationIssue] = Field(default_factory=list)


def validate_export_bundle_manifest(
    export_bundles_dir: Path,
) -> ExportBundleValidationResult:
    """Validate the export bundle manifest and referenced artifacts.

    Args:
        export_bundles_dir: Path to .ai-debt/export-bundles/.

    Returns:
        ExportBundleValidationResult with errors and warnings.
    """
    errors: list[ExportBundleValidationIssue] = []
    warnings: list[ExportBundleValidationIssue] = []

    manifest_path = export_bundles_dir / "manifest.json"

    # Rule: Missing manifest
    if not manifest_path.exists():
        errors.append(
            ExportBundleValidationIssue(
                severity="error",
                code="missing_manifest",
                message="manifest.json not found in export bundles directory",
            )
        )
        return ExportBundleValidationResult(valid=False, errors=errors)

    # Rule: Invalid manifest schema
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        errors.append(
            ExportBundleValidationIssue(
                severity="error",
                code="invalid_manifest_json",
                message=f"manifest.json is not valid JSON: {exc}",
            )
        )
        return ExportBundleValidationResult(valid=False, errors=errors)

    # Validate structure
    if not isinstance(data, dict):
        errors.append(
            ExportBundleValidationIssue(
                severity="error",
                code="invalid_manifest_structure",
                message="manifest.json must be a JSON object",
            )
        )
        return ExportBundleValidationResult(valid=False, errors=errors)

    schema_version = data.get("schema_version", "")
    if schema_version != "1.0":
        errors.append(
            ExportBundleValidationIssue(
                severity="error",
                code="unsupported_schema_version",
                message=f"Unsupported schema_version: {schema_version!r}",
            )
        )

    artifacts = data.get("artifacts", [])
    if not isinstance(artifacts, list):
        errors.append(
            ExportBundleValidationIssue(
                severity="error",
                code="invalid_artifacts_field",
                message="manifest 'artifacts' must be a list",
            )
        )
        return ExportBundleValidationResult(valid=False, errors=errors)

    # Rule: Unsupported tracker
    seen_paths: dict[str, int] = {}
    for i, art in enumerate(artifacts):
        if not isinstance(art, dict):
            errors.append(
                ExportBundleValidationIssue(
                    severity="error",
                    code="invalid_artifact_entry",
                    message=f"Artifact entry {i} is not a JSON object",
                )
            )
            continue

        tracker = art.get("tracker", "")
        if tracker and tracker not in SUPPORTED_TRACKERS:
            errors.append(
                ExportBundleValidationIssue(
                    severity="error",
                    code="unsupported_tracker",
                    message=f"Unsupported tracker: {tracker!r}",
                    tracker=tracker,
                )
            )

        # Rule: Duplicate artifact path
        rel_path = art.get("relative_path", "")
        if rel_path:
            if rel_path in seen_paths:
                errors.append(
                    ExportBundleValidationIssue(
                        severity="error",
                        code="duplicate_artifact_path",
                        message=f"Duplicate artifact path: {rel_path}",
                        artifact_path=rel_path,
                    )
                )
            else:
                seen_paths[rel_path] = i

            # Rule: Referenced artifact file missing
            abs_path = export_bundles_dir / rel_path
            if not abs_path.exists():
                errors.append(
                    ExportBundleValidationIssue(
                        severity="error",
                        code="missing_artifact_file",
                        message=f"Referenced artifact file not found: {rel_path}",
                        artifact_path=rel_path,
                    )
                )

    # Rule: README missing from tracker bundles
    for tracker_dir_name in SUPPORTED_TRACKERS:
        tracker_dir = export_bundles_dir / tracker_dir_name
        if tracker_dir.is_dir():
            readme = tracker_dir / "README.md"
            if not readme.exists():
                warnings.append(
                    ExportBundleValidationIssue(
                        severity="warning",
                        code="missing_tracker_readme",
                        message=f"README.md missing from {tracker_dir_name}/ bundle",
                        tracker=tracker_dir_name,
                    )
                )

    # Rule: Artifact count mismatch (summary vs actual)
    summary = data.get("summary", {})
    if isinstance(summary, dict):
        expected_count = summary.get("total_artifacts", 0)
        actual_count = len(artifacts)
        if expected_count != actual_count:
            warnings.append(
                ExportBundleValidationIssue(
                    severity="warning",
                    code="artifact_count_mismatch",
                    message=(
                        f"Summary reports {expected_count} artifacts "
                        f"but manifest has {actual_count}"
                    ),
                )
            )

    valid = len(errors) == 0
    return ExportBundleValidationResult(
        valid=valid,
        errors=errors,
        warnings=warnings,
    )


# --- Tracker bundle completeness ---

TRACKER_EXPECTED_ARTIFACTS: dict[str, dict[str, Any]] = {
    "jira": {
        "files": ["README.md", "jira-ticket-drafts.md", "jira-ticket-drafts.csv"],
        "csv_required_columns": ["Summary", "Description", "Issue Type", "Priority"],
    },
    "linear": {
        "files": ["README.md", "linear-ticket-drafts.md", "linear-ticket-drafts.csv"],
        "csv_required_columns": ["Title", "Description", "Priority"],
    },
    "github-issues": {
        "files": ["README.md", "github-issues-ticket-drafts.md"],
        "yaml_required_fields": ["title", "body", "labels"],
        "issues_dir": "issues",
    },
    "azure-devops": {
        "files": [
            "README.md",
            "azure-devops-ticket-drafts.md",
            "azure-devops-ticket-drafts.csv",
        ],
        "csv_required_columns": ["Title", "Description", "Work Item Type", "Priority"],
    },
}


def check_tracker_bundle_completeness(
    export_bundles_dir: Path,
    tracker: str,
) -> TrackerBundleCompleteness:
    """Check completeness of a specific tracker bundle.

    Args:
        export_bundles_dir: Path to .ai-debt/export-bundles/.
        tracker: Tracker name (e.g. "jira").

    Returns:
        TrackerBundleCompleteness assessment.
    """

    config = TRACKER_EXPECTED_ARTIFACTS.get(tracker, {})
    expected_files = config.get("files", [])
    tracker_dir = export_bundles_dir / tracker

    present: list[str] = []
    missing: list[str] = []
    warns: list[str] = []

    for fname in expected_files:
        fpath = tracker_dir / fname
        if fpath.exists():
            present.append(fname)
        else:
            missing.append(fname)

    # Check CSV required columns
    csv_columns = config.get("csv_required_columns", [])
    if csv_columns:
        # Find CSV file
        csv_file = None
        for f in present:
            if f.endswith(".csv"):
                csv_file = tracker_dir / f
                break
        if csv_file is not None:
            import csv as csv_mod
            import io

            content = csv_file.read_text(encoding="utf-8")
            reader = csv_mod.reader(io.StringIO(content))
            rows = [r for r in reader if r]
            if rows:
                header = rows[0]
                for col in csv_columns:
                    if col not in header:
                        warns.append(f"CSV missing required column: {col}")
            else:
                warns.append("CSV file is empty (no rows)")

    # Check GitHub Issues YAML directory
    issues_dir_name = config.get("issues_dir")
    if issues_dir_name:
        issues_dir = tracker_dir / issues_dir_name
        if issues_dir.is_dir():
            yaml_files = list(issues_dir.glob("*.yaml"))
            if not yaml_files:
                warns.append("GitHub Issues YAML directory is empty")
            else:
                yaml_fields = config.get("yaml_required_fields", [])
                for yf in yaml_files[:5]:  # Check first 5
                    content = yf.read_text(encoding="utf-8")
                    for field in yaml_fields:
                        if f"{field}:" not in content:
                            warns.append(f"YAML {yf.name} missing field: {field}")
                            break
        else:
            missing.append(f"{issues_dir_name}/")

    # Determine status
    if missing:
        # Missing README or primary export → needs_review
        critical_missing = [f for f in missing if not f.startswith("issues")]
        if critical_missing:
            status = "needs_review"
        else:
            status = "partial"
    elif warns:
        status = "partial"
    else:
        status = "complete"

    return TrackerBundleCompleteness(
        tracker=tracker,
        status=status,
        expected_artifacts=expected_files,
        present_artifacts=present,
        missing_artifacts=missing,
        warnings=warns,
    )


def check_all_tracker_bundles(
    export_bundles_dir: Path,
) -> list[TrackerBundleCompleteness]:
    """Check completeness of all tracker bundles.

    Returns:
        List of TrackerBundleCompleteness, one per tracker.
    """
    results: list[TrackerBundleCompleteness] = []
    for tracker in SUPPORTED_TRACKERS:
        tracker_dir = export_bundles_dir / tracker
        if tracker_dir.is_dir():
            results.append(check_tracker_bundle_completeness(export_bundles_dir, tracker))
    return results
