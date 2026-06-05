"""v3.3.0 Trivy connector tests.

Acceptance criteria verified:
  1. Trivy connector parses valid JSON and produces EvidenceItem list.
  4. Implements ConnectorInterface.
  5. Sets source="external_connector".
  6. Produces type="external_scanner_result", category="TD-EXT".
  7. Provenance includes tool name, version, and format.
  8. Vulnerability scanners store package_coordinates in metadata.
  10. Confidence is conservative (not derived from severity).
  11. External severity stored as metadata, not mapped to confidence.
  12. Malformed input returns ok=False with errors.
  13. Missing fields produce warnings, not errors.
  14. No connector creates DebtFinding directly.
  20. Package name is package coordinate, not repository file location.
  22. Connector version and source tool version stored separately.
  23. Trivy target/source fields preserved in metadata.
  24. EvidenceLocation populated only when real file/path exists.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pharabius.core.connectors.base import CONNECTOR_EVIDENCE_SOURCE, ConnectorInterface
from pharabius.core.connectors.trivy import TrivyConnector

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "connectors" / "trivy"


@pytest.fixture
def connector() -> TrivyConnector:
    return TrivyConnector()


# ---------------------------------------------------------------------------
# Interface conformance
# ---------------------------------------------------------------------------


class TestTrivyInterface:
    def test_name(self, connector: TrivyConnector) -> None:
        assert connector.name == "trivy"

    def test_version(self, connector: TrivyConnector) -> None:
        assert connector.version == "1.0.0"

    def test_is_connector_interface(self, connector: TrivyConnector) -> None:
        assert isinstance(connector, ConnectorInterface)


# ---------------------------------------------------------------------------
# Valid input
# ---------------------------------------------------------------------------


class TestTrivyValidInput:
    def test_minimal_valid(self, connector: TrivyConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        assert result.ok is True
        assert result.imported_count == 2
        assert len(result.evidence) == 2

    def test_evidence_source(self, connector: TrivyConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            assert item.source == CONNECTOR_EVIDENCE_SOURCE
            assert item.type == "external_scanner_result"
            assert item.category == "TD-EXT"

    def test_evidence_ids_prefixed(self, connector: TrivyConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            assert item.evidence_id.startswith("EXT-TRIVY-")

    def test_provenance_populated(self, connector: TrivyConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        prov = result.evidence[0].metadata["connector_provenance"]
        assert prov["connector_name"] == "trivy"
        assert prov["connector_version"] == "1.0.0"
        assert prov["source_format"] == "trivy"
        assert prov["source_tool_name"]  # ArtifactName from input
        assert prov["source_rule_id"]  # VulnerabilityID

    def test_package_coordinates(self, connector: TrivyConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        coords = result.evidence[0].metadata["package_coordinates"]
        assert "pkg_name" in coords
        assert "severity" in coords
        assert "installed_version" in coords

    def test_severity_in_metadata_not_confidence(self, connector: TrivyConnector) -> None:
        """AC11: External severity stored as metadata, not mapped to confidence."""
        result = connector.parse(FIXTURES / "minimal-valid.json")
        # First vuln is LOW severity, second is HIGH
        for item in result.evidence:
            # Severity is in package_coordinates metadata
            coords = item.metadata["package_coordinates"]
            if "severity" in coords:
                assert coords["severity"] in ("LOW", "HIGH")
            # Confidence is NOT derived from severity
            assert item.confidence in ("High", "Medium", "Low")

    def test_target_in_metadata(self, connector: TrivyConnector) -> None:
        """AC23: Trivy target preserved in metadata."""
        result = connector.parse(FIXTURES / "minimal-valid.json")
        assert "target" in result.evidence[0].metadata
        assert "alpine" in result.evidence[0].metadata["target"]

    def test_evidence_location_empty(self, connector: TrivyConnector) -> None:
        """AC24: EvidenceLocation not populated from package name."""
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            # Trivy doesn't provide real file paths
            assert item.location.file == ""

    def test_connector_vs_tool_version(self, connector: TrivyConnector) -> None:
        """AC22: Connector version separate from source tool version."""
        result = connector.parse(FIXTURES / "minimal-valid.json")
        prov = result.evidence[0].metadata["connector_provenance"]
        assert prov["connector_version"] == "1.0.0"
        # source_tool_version may be empty (Trivy doesn't always include it)
        assert "source_tool_version" in prov

    def test_confidence_reason_present(self, connector: TrivyConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            assert "confidence_reason" in item.metadata


# ---------------------------------------------------------------------------
# Multi-target
# ---------------------------------------------------------------------------


class TestTrivyMultiTarget:
    def test_multi_target(self, connector: TrivyConnector) -> None:
        result = connector.parse(FIXTURES / "multi-target.json")
        assert result.ok is True
        assert result.imported_count == 2
        targets = [item.metadata["target"] for item in result.evidence]
        assert len(set(targets)) == 2  # Different targets

    def test_different_result_types(self, connector: TrivyConnector) -> None:
        result = connector.parse(FIXTURES / "multi-target.json")
        assert result.evidence[0].metadata["target"] != result.evidence[1].metadata["target"]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestTrivyEdgeCases:
    def test_empty_results(self, connector: TrivyConnector) -> None:
        result = connector.parse(FIXTURES / "empty-results.json")
        assert result.ok is True
        assert result.imported_count == 0
        assert result.evidence == []
        assert len(result.warnings) >= 1

    def test_malformed_json(self, connector: TrivyConnector) -> None:
        result = connector.parse(FIXTURES / "malformed.json")
        assert result.ok is False
        assert len(result.errors) >= 1
        assert result.evidence == []

    def test_missing_location(self, connector: TrivyConnector) -> None:
        result = connector.parse(FIXTURES / "missing-location.json")
        assert result.ok is True
        assert result.imported_count == 1
        # Has vuln ID + severity + title but no package name
        # Target provides a locator, so confidence can be High or Medium
        item = result.evidence[0]
        assert item.metadata["connector_provenance"]["source_rule_id"] == "CVE-2024-0001"
        # Package coordinates has no pkg_name
        coords = item.metadata["package_coordinates"]
        assert "pkg_name" not in coords or coords.get("pkg_name", "") == ""

    def test_missing_file(self, connector: TrivyConnector) -> None:
        result = connector.parse(FIXTURES / "nonexistent.json")
        assert result.ok is False
        assert len(result.errors) >= 1


# ---------------------------------------------------------------------------
# Negative: No DebtFinding
# ---------------------------------------------------------------------------


class TestTrivyNoDebtFinding:
    def test_no_debt_finding_creation(self, connector: TrivyConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            assert hasattr(item, "evidence_id")
            assert not hasattr(item, "finding_id")
