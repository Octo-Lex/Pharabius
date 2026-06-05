"""Connector interface and result model.

Every external evidence connector implements ConnectorInterface and returns
a ConnectorResult. The result carries normalized evidence items plus import
metadata (warnings, errors, counts).

Design rules:
- source field on all EvidenceItem is "external_connector"
- Scanner identity goes in metadata["connector_provenance"]["connector_name"]
- Connectors never create DebtFinding objects
- Malformed input sets ok=False and returns empty evidence list
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from pharabius.schemas.evidence import EvidenceItem

# Stable source value for all connector-generated evidence
CONNECTOR_EVIDENCE_SOURCE = "external_connector"


@dataclass(frozen=True)
class ConnectorResult:
    """Result from parsing an external scanner artifact.

    Attributes:
        connector_name: Identifier for the connector (e.g. "sarif", "semgrep").
        connector_version: Version of the connector implementation.
        source_format: Format of the input file (e.g. "sarif", "semgrep").
        source_file: Path to the input file that was parsed.
        evidence: Normalized evidence items produced from the input.
        imported_count: Number of records successfully imported as evidence.
        skipped_count: Number of records skipped (unsupported fields, etc.).
        warnings: Non-fatal issues encountered during parsing.
        errors: Fatal issues that prevented full parsing.
        ok: Whether the import succeeded. False means the input was malformed
            or unparseable; no artifact should be written.
    """

    connector_name: str
    connector_version: str
    source_format: str
    source_file: str
    evidence: list[EvidenceItem] = field(default_factory=list)
    imported_count: int = 0
    skipped_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    ok: bool = True


class ConnectorInterface(ABC):
    """Base class for external evidence connectors.

    Each connector accepts an external artifact file and produces normalized
    Pharabius evidence. Connectors do not create final findings.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Connector identifier (e.g. "sarif", "semgrep")."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Connector implementation version."""

    @abstractmethod
    def parse(self, source: Path) -> ConnectorResult:
        """Parse an external artifact file into normalized evidence.

        Args:
            source: Path to the external artifact file.

        Returns:
            ConnectorResult with evidence items and import metadata.
            Sets ok=False if the file is malformed or unparseable.
        """
