"""Trivy JSON connector — imports Trivy vulnerability scan results.

Parses Trivy's JSON output format (SchemaVersion 2):
  Results[].Vulnerabilities[] → EvidenceItem[]

Design rules:
- source = "external_connector"
- type = "external_scanner_result", category = "TD-EXT"
- Package name is a package coordinate, NOT a file location
- EvidenceLocation.file is populated only from real file paths if available
- Trivy Target is preserved in metadata, not overclaimed as repository file
- Severity is stored as metadata, not mapped to Pharabius confidence
- Connector version (Pharabius implementation) is separate from source tool version
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


class TrivyConnector(ConnectorInterface):
    """Import Trivy JSON vulnerability scan output as normalized evidence."""

    @property
    def name(self) -> str:
        return "trivy"

    @property
    def version(self) -> str:
        return "1.0.0"

    def parse(self, source: Path) -> ConnectorResult:
        """Parse a Trivy JSON results file.

        Args:
            source: Path to Trivy JSON output file.

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
                source_format="trivy",
                source_file=str(source),
                errors=[f"Cannot read input: {exc}"],
                ok=False,
            )
        except OSError as exc:
            return ConnectorResult(
                connector_name=self.name,
                connector_version=self.version,
                source_format="trivy",
                source_file=str(source),
                errors=[f"Cannot read file: {exc}"],
                ok=False,
            )

        if not isinstance(data, dict):
            return ConnectorResult(
                connector_name=self.name,
                connector_version=self.version,
                source_format="trivy",
                source_file=str(source),
                errors=["Expected JSON object at top level"],
                ok=False,
            )

        # Extract source tool version from descriptor if present
        source_tool_name = data.get("ArtifactName", "Trivy")
        source_tool_version = ""

        results_list = data.get("Results", [])
        if not results_list:
            warnings.append("No results found in Trivy output")

        now = datetime.now(UTC).replace(microsecond=0).isoformat()
        evidence: list[EvidenceItem] = []
        imported = 0
        skipped = 0
        record_index = 0

        for result in results_list:
            target = result.get("Target", "")
            vulns = result.get("Vulnerabilities", [])

            for vuln in vulns:
                record_index += 1

                vuln_id = vuln.get("VulnerabilityID", "")
                pkg_name = vuln.get("PkgName", "")
                installed_ver = vuln.get("InstalledVersion", "")
                fixed_ver = vuln.get("FixedVersion", "")
                severity = vuln.get("Severity", "")
                title = vuln.get("Title", "")
                description = vuln.get("Description", "")
                primary_url = vuln.get("PrimaryURL", "")
                purl = vuln.get("PkgIdentifier", {}).get("PURL", "")

                # Locator: package coordinate, not file location
                has_locator = bool(pkg_name or purl or target)
                has_vuln_id = bool(vuln_id)
                has_message = bool(title or description)

                if not has_locator and not has_vuln_id:
                    skipped += 1
                    warnings.append(f"Skipping record {record_index}: no usable data")
                    continue

                # Confidence (depsec model: locator + vuln ID + message)
                confidence, reason = assign_depsec_confidence(
                    has_locator=has_locator,
                    has_vulnerability_id=has_vuln_id,
                    has_message=has_message,
                )

                # Build summary
                summary = title or f"{vuln_id} in {pkg_name}" or "Trivy vulnerability"
                raw_obs = description or title or ""

                # Provenance
                provenance = ConnectorProvenance(
                    connector_name=self.name,
                    connector_version=self.version,
                    source_format="trivy",
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
                    installed_version=installed_ver,
                    fixed_version=fixed_ver,
                    purl=purl,
                    severity=severity,
                    primary_url=primary_url,
                )

                metadata: dict = {
                    "connector_provenance": provenance.to_metadata_dict(),
                    "package_coordinates": pkg_coords,
                    "target": target,
                    "confidence_reason": reason,
                }

                # EvidenceLocation: conservative — no real file path from Trivy
                # Target is a scan target (image, package type), not a repo file
                location = EvidenceLocation()

                item = EvidenceItem(
                    evidence_id=f"EXT-TRIVY-{record_index:06d}",
                    source=CONNECTOR_EVIDENCE_SOURCE,
                    type="external_scanner_result",
                    category="TD-EXT",
                    location=location,
                    subject=pkg_name,
                    object=vuln_id,
                    summary=summary,
                    raw_observation=raw_obs,
                    confidence=confidence,
                    metadata=metadata,
                )
                evidence.append(item)
                imported += 1

        return ConnectorResult(
            connector_name=self.name,
            connector_version=self.version,
            source_format="trivy",
            source_file=str(source),
            evidence=evidence,
            imported_count=imported,
            skipped_count=skipped,
            warnings=warnings,
            errors=errors,
            ok=True,
        )
