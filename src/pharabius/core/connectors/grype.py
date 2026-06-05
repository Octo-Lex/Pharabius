"""Grype JSON connector — imports Grype vulnerability scan results.

Parses Grype's JSON output format:
  matches[] → EvidenceItem[]

Design rules:
- source = "external_connector"
- type = "external_scanner_result", category = "TD-EXT"
- Package name is a package coordinate, NOT a file location
- EvidenceLocation.file populated only from real file paths
- Severity stored as metadata, not mapped to Pharabius confidence
- Connector version separate from source tool version
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
from pharabius.core.connectors.depsec_helpers import (
    assign_depsec_confidence,
    build_depsec_coordinates,
)
from pharabius.core.connectors.provenance import ConnectorProvenance
from pharabius.schemas.evidence import EvidenceItem, EvidenceLocation


class GrypeConnector(ConnectorInterface):
    """Import Grype JSON vulnerability scan output as normalized evidence."""

    @property
    def name(self) -> str:
        return "grype"

    @property
    def version(self) -> str:
        return "1.0.0"

    def parse(self, source: Path) -> ConnectorResult:
        """Parse a Grype JSON results file.

        Args:
            source: Path to Grype JSON output file.

        Returns:
            ConnectorResult with normalized evidence items.
        """
        warnings: list[str] = []
        errors: list[str] = []

        try:
            raw = source.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return ConnectorResult(
                connector_name=self.name,
                connector_version=self.version,
                source_format="grype",
                source_file=str(source),
                errors=[f"Cannot read input: {exc}"],
                ok=False,
            )
        except OSError as exc:
            return ConnectorResult(
                connector_name=self.name,
                connector_version=self.version,
                source_format="grype",
                source_file=str(source),
                errors=[f"Cannot read file: {exc}"],
                ok=False,
            )

        if not isinstance(data, dict):
            return ConnectorResult(
                connector_name=self.name,
                connector_version=self.version,
                source_format="grype",
                source_file=str(source),
                errors=["Expected JSON object at top level"],
                ok=False,
            )

        # Extract source tool version from descriptor
        descriptor = data.get("descriptor", {})
        source_tool_name = descriptor.get("name", "Grype")
        source_tool_version = descriptor.get("version", "")

        matches = data.get("matches", [])
        if not matches:
            warnings.append("No matches found in Grype output")

        # Source metadata for provenance
        source_info = data.get("source", {})
        source_target = source_info.get("target", "")

        now = datetime.now(UTC).replace(microsecond=0).isoformat()
        evidence: list[EvidenceItem] = []
        imported = 0
        skipped = 0
        record_index = 0

        for match in matches:
            record_index += 1

            vuln = match.get("vulnerability", {})
            artifact = match.get("artifact", {})

            vuln_id = vuln.get("id", "")
            severity = vuln.get("severity", "")
            description = vuln.get("description", "")

            pkg_name = artifact.get("name", "")
            pkg_version = artifact.get("version", "")
            pkg_type = artifact.get("type", "")
            purl = artifact.get("purl", "")

            # Locator: package coordinate, not file location
            has_locator = bool(pkg_name or purl or source_target)
            has_vuln_id = bool(vuln_id)
            has_message = bool(description)

            if not has_locator and not has_vuln_id:
                skipped += 1
                warnings.append(f"Skipping record {record_index}: no usable data")
                continue

            # Confidence (depsec model)
            confidence, reason = assign_depsec_confidence(
                has_locator=has_locator,
                has_vulnerability_id=has_vuln_id,
                has_message=has_message,
            )

            # Build summary
            summary = (
                f"{vuln_id} in {pkg_name}"
                if vuln_id and pkg_name
                else (description[:200] if description else "Grype vulnerability match")
            )

            # Provenance
            provenance = ConnectorProvenance(
                connector_name=self.name,
                connector_version=self.version,
                source_format="grype",
                source_file=str(source),
                source_tool_name=source_tool_name,
                source_tool_version=source_tool_version,
                source_rule_id=vuln_id,
                source_record_index=record_index,
                imported_at=now,
            )

            # Package coordinates
            pkg_coords = build_depsec_coordinates(
                pkg_name=pkg_name,
                installed_version=pkg_version,
                purl=purl,
                severity=severity,
            )

            metadata: dict = {
                "connector_provenance": provenance.to_metadata_dict(),
                "package_coordinates": pkg_coords,
                "artifact_type": pkg_type,
                "source_target": source_target,
                "confidence_reason": reason,
            }

            # Match details
            match_details = match.get("matchDetails", [])
            if match_details:
                first_detail = match_details[0]
                metadata["match_type"] = first_detail.get("type", "")
                metadata["matcher"] = first_detail.get("matcher", "")

            # EvidenceLocation: conservative — no real file path from Grype
            location = EvidenceLocation()

            item = EvidenceItem(
                evidence_id=f"EXT-GRYPE-{record_index:06d}",
                source=CONNECTOR_EVIDENCE_SOURCE,
                type="external_scanner_result",
                category="TD-EXT",
                location=location,
                subject=pkg_name,
                object=vuln_id,
                summary=summary,
                raw_observation=description,
                confidence=confidence,
                metadata=metadata,
            )
            evidence.append(item)
            imported += 1

        return ConnectorResult(
            connector_name=self.name,
            connector_version=self.version,
            source_format="grype",
            source_file=str(source),
            evidence=evidence,
            imported_count=imported,
            skipped_count=skipped,
            warnings=warnings,
            errors=errors,
            ok=True,
        )
