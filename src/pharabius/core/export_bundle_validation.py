"""Export bundle manifest validation.

Validates .ai-debt/export-bundles/manifest.json for internal consistency.
No external tracker API calls are made.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field

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
