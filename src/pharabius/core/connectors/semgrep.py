"""Semgrep JSON output import connector.

Imports Semgrep JSON output files as normalized Pharabius evidence items.

Supported fields:
- results[].check_id
- results[].path
- results[].start.line / end.line
- results[].extra.severity
- results[].extra.message

Missing optional fields are handled safely.
Does not run semgrep. Does not require semgrep to be installed.
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

_CONNECTOR_NAME = "semgrep"
_CONNECTOR_VERSION = "1.0.0"
_SOURCE_FORMAT = "semgrep"


class SemgrepConnector(ConnectorInterface):
    """Import Semgrep JSON output files as normalized evidence."""

    @property
    def name(self) -> str:
        return _CONNECTOR_NAME

    @property
    def version(self) -> str:
        return _CONNECTOR_VERSION

    def parse(self, source: Path) -> ConnectorResult:
        """Parse a Semgrep JSON output file into normalized evidence.

        Args:
            source: Path to the Semgrep JSON file.

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
            errors.append("Semgrep output root must be a JSON object")
            return _error_result(source, errors)

        # Extract results
        results = data.get("results", [])
        if not isinstance(results, list):
            errors.append("Semgrep results must be an array")
            return _error_result(source, errors)

        if not results:
            return ConnectorResult(
                connector_name=_CONNECTOR_NAME,
                connector_version=_CONNECTOR_VERSION,
                source_format=_SOURCE_FORMAT,
                source_file=str(source),
                evidence=[],
                imported_count=0,
                skipped_count=0,
                warnings=["Semgrep file contains no results"],
                errors=[],
                ok=True,
            )

        # Extract tool info from top-level metadata if present
        tool_version = str(data.get("version", ""))

        # Process results
        evidence: list[EvidenceItem] = []
        skipped = 0
        imported_at = datetime.now(UTC).replace(microsecond=0).isoformat()
        record_index = 0

        for result in results:
            if not isinstance(result, dict):
                skipped += 1
                continue

            record_index += 1

            check_id = str(result.get("check_id", ""))
            file_path = str(result.get("path", ""))

            # Extract line numbers
            start_obj = result.get("start")
            start_line = None
            if isinstance(start_obj, dict):
                line = start_obj.get("line")
                if isinstance(line, int):
                    start_line = line

            # Extract severity and message from extra
            extra = result.get("extra")
            severity = ""
            message = ""
            if isinstance(extra, dict):
                severity = str(extra.get("severity", ""))
                message = str(extra.get("message", ""))

            # Build provenance
            provenance = ConnectorProvenance(
                connector_name=_CONNECTOR_NAME,
                connector_version=_CONNECTOR_VERSION,
                source_format=_SOURCE_FORMAT,
                source_file=str(source),
                source_tool_name="semgrep",
                source_tool_version=tool_version,
                source_rule_id=check_id,
                source_record_index=record_index,
                imported_at=imported_at,
            )

            # Build evidence item
            summary = message or f"Semgrep finding: {check_id or 'unknown check'}"
            if not summary.strip():
                summary = f"Semgrep finding (record {record_index})"

            raw_obs = message
            if severity:
                raw_obs = f"[{severity}] {message}" if message else severity

            item = EvidenceItem(
                evidence_id=f"EXT-SEM-{record_index:06d}",
                source=CONNECTOR_EVIDENCE_SOURCE,
                type="external_scanner_result",
                category="TD-EXT",
                location=EvidenceLocation(
                    file=file_path,
                    line_start=start_line,
                ),
                summary=summary,
                raw_observation=raw_obs,
                metadata={
                    "connector_provenance": provenance.to_metadata_dict(),
                    "source_severity": severity,
                },
            )

            # Apply confidence
            item = apply_confidence(
                item,
                has_location=bool(file_path) and start_line is not None,
                has_rule_id=bool(check_id),
                has_message=bool(message),
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
