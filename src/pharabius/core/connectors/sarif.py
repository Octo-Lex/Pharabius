"""SARIF v2.1.0 import connector.

Imports SARIF files produced by external scanners (Semgrep, CodeQL, etc.)
into normalized Pharabius evidence items.

Supported SARIF fields:
- runs[].tool.driver.name / version
- runs[].results[].ruleId
- runs[].results[].message.text
- runs[].results[].locations[].physicalLocation.artifactLocation.uri
- runs[].results[].locations[].physicalLocation.region.startLine

Unsupported fields are skipped with warnings, not errors.
Does not attempt full SARIF schema coverage.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pharabius.core.connectors.base import (
    CONNECTOR_EVIDENCE_SOURCE,
    ConnectorInterface,
    ConnectorResult,
)
from pharabius.core.connectors.confidence import apply_confidence
from pharabius.core.connectors.provenance import ConnectorProvenance
from pharabius.schemas.evidence import EvidenceItem, EvidenceLocation

_CONNECTOR_NAME = "sarif"
_CONNECTOR_VERSION = "1.0.0"
_SOURCE_FORMAT = "sarif"


class SarifConnector(ConnectorInterface):
    """Import SARIF v2.1.0 files as normalized evidence."""

    @property
    def name(self) -> str:
        return _CONNECTOR_NAME

    @property
    def version(self) -> str:
        return _CONNECTOR_VERSION

    def parse(self, source: Path) -> ConnectorResult:
        """Parse a SARIF file into normalized evidence.

        Args:
            source: Path to the SARIF JSON file.

        Returns:
            ConnectorResult with evidence items and import metadata.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Read and parse JSON
        try:
            raw = source.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"Cannot read file: {exc}")
            return _error_result(source, errors)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON: {exc}")
            return _error_result(source, errors)

        if not isinstance(data, dict):
            errors.append("SARIF root must be a JSON object")
            return _error_result(source, errors)

        # Extract runs
        runs = data.get("runs", [])
        if not isinstance(runs, list):
            errors.append("SARIF runs must be an array")
            return _error_result(source, errors)

        if not runs:
            return ConnectorResult(
                connector_name=_CONNECTOR_NAME,
                connector_version=_CONNECTOR_VERSION,
                source_format=_SOURCE_FORMAT,
                source_file=str(source),
                evidence=[],
                imported_count=0,
                skipped_count=0,
                warnings=["SARIF file contains no runs"],
                errors=[],
                ok=True,
            )

        # Process runs
        evidence: list[EvidenceItem] = []
        skipped = 0
        imported_at = datetime.now(UTC).replace(microsecond=0).isoformat()
        record_index = 0

        for run_idx, run in enumerate(runs):
            if not isinstance(run, dict):
                warnings.append(f"Run {run_idx} is not an object, skipping")
                skipped += 1
                continue

            # Extract tool info
            tool_name = ""
            tool_version = ""
            driver = _deep_get(run, "tool", "driver")
            if isinstance(driver, dict):
                tool_name = str(driver.get("name", ""))
                tool_version = str(driver.get("version", ""))

            # Extract results
            results = run.get("results", [])
            if not isinstance(results, list):
                warnings.append(f"Run {run_idx} results is not an array, skipping")
                continue

            for result in results:
                if not isinstance(result, dict):
                    skipped += 1
                    continue

                record_index += 1
                rule_id = str(result.get("ruleId", ""))
                message_text = _extract_message(result)

                # Extract location
                file_path, start_line = _extract_location(result)

                # Build provenance
                provenance = ConnectorProvenance(
                    connector_name=_CONNECTOR_NAME,
                    connector_version=_CONNECTOR_VERSION,
                    source_format=_SOURCE_FORMAT,
                    source_file=str(source),
                    source_tool_name=tool_name,
                    source_tool_version=tool_version,
                    source_rule_id=rule_id,
                    source_record_index=record_index,
                    imported_at=imported_at,
                )

                # Build evidence item
                summary = message_text or f"SARIF result: {rule_id or 'unknown rule'}"
                if not summary.strip():
                    summary = f"SARIF result from {tool_name or 'unknown tool'}"

                item = EvidenceItem(
                    evidence_id=f"EXT-SARIF-{record_index:06d}",
                    source=CONNECTOR_EVIDENCE_SOURCE,
                    type="external_scanner_result",
                    category="TD-EXT",
                    location=EvidenceLocation(
                        file=file_path,
                        line_start=start_line,
                    ),
                    summary=summary,
                    raw_observation=message_text,
                    metadata={
                        "connector_provenance": provenance.to_metadata_dict(),
                    },
                )

                # Apply confidence
                item = apply_confidence(
                    item,
                    has_location=bool(file_path),
                    has_rule_id=bool(rule_id),
                    has_message=bool(message_text),
                )

                evidence.append(item)

        return ConnectorResult(
            connector_name=_CONNECTOR_NAME,
            connector_version=_CONNECTOR_VERSION,
            source_format=_SOURCE_FORMAT,
            source_file=str(source),
            evidence=evidence,
            imported_count=len(evidence),
            skipped_count=skipped,
            warnings=warnings,
            errors=[],
            ok=True,
        )


def _error_result(source: Path, errors: list[str]) -> ConnectorResult:
    """Build a result for unparseable input."""
    return ConnectorResult(
        connector_name=_CONNECTOR_NAME,
        connector_version=_CONNECTOR_VERSION,
        source_format=_SOURCE_FORMAT,
        source_file=str(source),
        evidence=[],
        imported_count=0,
        skipped_count=0,
        warnings=[],
        errors=errors,
        ok=False,
    )


def _extract_message(result: dict) -> str:
    """Extract message text from a SARIF result."""
    message = result.get("message")
    if isinstance(message, dict):
        return str(message.get("text", ""))
    if isinstance(message, str):
        return message
    return ""


def _extract_location(result: dict) -> tuple[str, int | None]:
    """Extract file path and start line from a SARIF result."""
    locations = result.get("locations", [])
    if not isinstance(locations, list) or not locations:
        return "", None

    first = locations[0]
    if not isinstance(first, dict):
        return "", None

    phys = first.get("physicalLocation")
    if not isinstance(phys, dict):
        return "", None

    artifact = phys.get("artifactLocation")
    file_path = ""
    if isinstance(artifact, dict):
        file_path = str(artifact.get("uri", ""))

    region = phys.get("region")
    start_line = None
    if isinstance(region, dict):
        line = region.get("startLine")
        if isinstance(line, int):
            start_line = line

    return file_path, start_line


def _deep_get(data: dict, *keys: str) -> object:
    """Safely traverse nested dicts."""
    current: object = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    return current
