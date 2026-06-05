"""Connector provenance metadata.

Every imported evidence item carries provenance metadata in its
metadata["connector_provenance"] field. This allows distinguishing
connector-sourced evidence from native repository scan evidence.

EvidenceItem.source is always "external_connector".
The specific scanner identity is in provenance.connector_name.
"""

from __future__ import annotations

from pydantic import BaseModel


class ConnectorProvenance(BaseModel):
    """Provenance metadata for connector-imported evidence.

    Stored in EvidenceItem.metadata["connector_provenance"].
    """

    connector_name: str
    connector_version: str
    source_format: str
    source_file: str
    source_tool_name: str = ""
    source_tool_version: str = ""
    source_rule_id: str = ""
    source_record_index: int = 0
    imported_at: str = ""
    raw_fingerprint: str = ""

    def to_metadata_dict(self) -> dict[str, str | int]:
        """Convert to a flat dict suitable for EvidenceItem.metadata."""
        return self.model_dump()
