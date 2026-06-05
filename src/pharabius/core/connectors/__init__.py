"""External evidence connectors for Pharabius.

Connectors import external scanner output as normalized EvidenceItem objects.
They never create final findings (DebtFinding) directly.

Flow:
    External scanner output
      -> Connector.parse()
      -> ConnectorResult (evidence + metadata)
      -> EvidenceStore artifact (written by CLI)

Connectors are evidence-only. Analysis, scoring, and governance remain
Pharabius-internal responsibilities.
"""

from pharabius.core.connectors.base import (
    ConnectorInterface,
    ConnectorResult,
)
from pharabius.core.connectors.provenance import ConnectorProvenance

__all__ = [
    "ConnectorInterface",
    "ConnectorProvenance",
    "ConnectorResult",
]
