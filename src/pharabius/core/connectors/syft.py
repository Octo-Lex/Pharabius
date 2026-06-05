"""Syft JSON connector — imports Syft SBOM package inventory.

Parses Syft's syft-json output format:
  artifacts[] → EvidenceItem[]

Design rules:
- source = "external_connector"
- type = "external_scanner_result", category = "TD-EXT"
- SBOM confidence uses separate model (no vulnerability rule IDs required)
- EvidenceLocation.file populated from real file paths (locations[].path)
- Connector version separate from source tool version
- No SBOM generation — import only
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
    assign_sbom_confidence,
    build_sbom_coordinates,
)
from pharabius.core.connectors.provenance import ConnectorProvenance
from pharabius.schemas.evidence import EvidenceItem, EvidenceLocation


class SyftConnector(ConnectorInterface):
    """Import Syft JSON SBOM output as normalized evidence."""

    @property
    def name(self) -> str:
        return "syft"

    @property
    def version(self) -> str:
        return "1.0.0"

    def parse(self, source: Path) -> ConnectorResult:
        """Parse a Syft JSON SBOM file.

        Args:
            source: Path to Syft JSON output file.

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
                source_format="syft",
                source_file=str(source),
                errors=[f"Cannot read input: {exc}"],
                ok=False,
            )
        except OSError as exc:
            return ConnectorResult(
                connector_name=self.name,
                connector_version=self.version,
                source_format="syft",
                source_file=str(source),
                errors=[f"Cannot read file: {exc}"],
                ok=False,
            )

        if not isinstance(data, dict):
            return ConnectorResult(
                connector_name=self.name,
                connector_version=self.version,
                source_format="syft",
                source_file=str(source),
                errors=["Expected JSON object at top level"],
                ok=False,
            )

        # Extract source tool version from descriptor
        descriptor = data.get("descriptor", {})
        source_tool_name = descriptor.get("name", "Syft")
        source_tool_version = descriptor.get("version", "")

        artifacts = data.get("artifacts", [])
        if not artifacts:
            warnings.append("No artifacts found in Syft output")

        now = datetime.now(UTC).replace(microsecond=0).isoformat()
        evidence: list[EvidenceItem] = []
        imported = 0
        skipped = 0
        record_index = 0

        for artifact in artifacts:
            record_index += 1

            pkg_name = artifact.get("name", "")
            pkg_version = artifact.get("version", "") or ""
            pkg_type = artifact.get("type", "")
            language = artifact.get("language", "") or ""
            purl = artifact.get("purl", "") or ""
            found_by = artifact.get("foundBy", "")
            licenses = artifact.get("licenses", []) or []

            # Real file path from locations
            locations = artifact.get("locations", [])
            file_path = ""
            if locations and isinstance(locations, list):
                first_loc = locations[0] if locations else {}
                file_path = first_loc.get("path", "") if isinstance(first_loc, dict) else ""

            # SBOM-aware confidence (no vulnerability rule IDs)
            has_name = bool(pkg_name)
            has_version_or_purl = bool(pkg_version or purl)
            has_location = bool(file_path)

            if not has_name and not has_version_or_purl:
                skipped += 1
                warnings.append(f"Skipping record {record_index}: no package identity")
                continue

            confidence, reason = assign_sbom_confidence(
                has_name=has_name,
                has_version_or_purl=has_version_or_purl,
                has_location=has_location,
            )

            # Build summary
            summary = f"{pkg_name} {pkg_version}".strip()
            if pkg_type:
                summary += f" ({pkg_type})"

            # Provenance
            provenance = ConnectorProvenance(
                connector_name=self.name,
                connector_version=self.version,
                source_format="syft",
                source_file=str(source),
                source_tool_name=source_tool_name,
                source_tool_version=source_tool_version,
                source_rule_id="",  # SBOM has no rules
                source_record_index=record_index,
                imported_at=now,
            )

            # Package coordinates
            pkg_coords = build_sbom_coordinates(
                pkg_name=pkg_name,
                version=pkg_version,
                pkg_type=pkg_type,
                language=language,
                purl=purl,
                licenses=licenses,
                found_by=found_by,
            )

            metadata: dict = {
                "connector_provenance": provenance.to_metadata_dict(),
                "package_coordinates": pkg_coords,
                "confidence_reason": reason,
            }

            # EvidenceLocation: populated from real file path if available
            location = EvidenceLocation(file=file_path) if file_path else EvidenceLocation()

            item = EvidenceItem(
                evidence_id=f"EXT-SYFT-{record_index:06d}",
                source=CONNECTOR_EVIDENCE_SOURCE,
                type="external_scanner_result",
                category="TD-EXT",
                location=location,
                subject=pkg_name,
                object=pkg_type,
                summary=summary,
                raw_observation="",
                confidence=confidence,
                metadata=metadata,
            )
            evidence.append(item)
            imported += 1

        return ConnectorResult(
            connector_name=self.name,
            connector_version=self.version,
            source_format="syft",
            source_file=str(source),
            evidence=evidence,
            imported_count=imported,
            skipped_count=skipped,
            warnings=warnings,
            errors=errors,
            ok=True,
        )
