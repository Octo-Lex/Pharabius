"""v3.3.0 Grype connector tests.

Acceptance criteria verified:
  2. Grype connector parses valid JSON and produces EvidenceItem list.
  4-8, 10-14, 20, 22-24 same as Trivy.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pharabius.core.connectors.base import CONNECTOR_EVIDENCE_SOURCE, ConnectorInterface
from pharabius.core.connectors.grype import GrypeConnector

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "connectors" / "grype"


@pytest.fixture
def connector() -> GrypeConnector:
    return GrypeConnector()


class TestGrypeInterface:
    def test_name(self, connector: GrypeConnector) -> None:
        assert connector.name == "grype"

    def test_version(self, connector: GrypeConnector) -> None:
        assert connector.version == "1.0.0"

    def test_is_connector_interface(self, connector: GrypeConnector) -> None:
        assert isinstance(connector, ConnectorInterface)


class TestGrypeValidInput:
    def test_minimal_valid(self, connector: GrypeConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        assert result.ok is True
        assert result.imported_count == 2
        assert len(result.evidence) == 2

    def test_evidence_source(self, connector: GrypeConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            assert item.source == CONNECTOR_EVIDENCE_SOURCE
            assert item.type == "external_scanner_result"
            assert item.category == "TD-EXT"

    def test_evidence_ids_prefixed(self, connector: GrypeConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            assert item.evidence_id.startswith("EXT-GRYPE-")

    def test_provenance_populated(self, connector: GrypeConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        prov = result.evidence[0].metadata["connector_provenance"]
        assert prov["connector_name"] == "grype"
        assert prov["connector_version"] == "1.0.0"
        assert prov["source_format"] == "grype"
        assert prov["source_rule_id"]  # CVE ID

    def test_tool_version_from_descriptor(self, connector: GrypeConnector) -> None:
        """AC22: Source tool version extracted from Grype descriptor."""
        result = connector.parse(FIXTURES / "minimal-valid.json")
        prov = result.evidence[0].metadata["connector_provenance"]
        assert prov["connector_version"] == "1.0.0"
        assert prov["source_tool_version"] == "0.80.0"
        assert prov["source_tool_name"] == "grype"

    def test_package_coordinates(self, connector: GrypeConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        coords = result.evidence[0].metadata["package_coordinates"]
        assert "pkg_name" in coords
        assert "severity" in coords

    def test_severity_in_metadata_not_confidence(self, connector: GrypeConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            coords = item.metadata["package_coordinates"]
            if "severity" in coords:
                assert coords["severity"] in ("Low", "High")
            assert item.confidence in ("High", "Medium", "Low")

    def test_source_target_in_metadata(self, connector: GrypeConnector) -> None:
        """AC23: Source target preserved in metadata."""
        result = connector.parse(FIXTURES / "minimal-valid.json")
        assert "source_target" in result.evidence[0].metadata

    def test_evidence_location_empty(self, connector: GrypeConnector) -> None:
        """AC24: No real file path from Grype."""
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            assert item.location.file == ""

    def test_match_details(self, connector: GrypeConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        item = result.evidence[0]
        assert item.metadata.get("match_type") == "exact-direct-match"
        assert "matcher" in item.metadata

    def test_confidence_reason_present(self, connector: GrypeConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            assert "confidence_reason" in item.metadata


class TestGrypeMultiTarget:
    def test_multi_target(self, connector: GrypeConnector) -> None:
        result = connector.parse(FIXTURES / "multi-target.json")
        assert result.ok is True
        assert result.imported_count == 2

    def test_different_artifact_types(self, connector: GrypeConnector) -> None:
        result = connector.parse(FIXTURES / "multi-target.json")
        types = [item.metadata.get("artifact_type", "") for item in result.evidence]
        assert "apk" in types
        assert "python" in types


class TestGrypeEdgeCases:
    def test_empty_results(self, connector: GrypeConnector) -> None:
        result = connector.parse(FIXTURES / "empty-results.json")
        assert result.ok is True
        assert result.imported_count == 0
        assert result.evidence == []
        assert len(result.warnings) >= 1

    def test_malformed_json(self, connector: GrypeConnector) -> None:
        result = connector.parse(FIXTURES / "malformed.json")
        assert result.ok is False
        assert len(result.errors) >= 1

    def test_missing_location(self, connector: GrypeConnector) -> None:
        result = connector.parse(FIXTURES / "missing-location.json")
        assert result.ok is True
        assert result.imported_count == 1
        # Has vuln ID but no package name
        item = result.evidence[0]
        assert item.confidence in ("Medium", "Low")

    def test_missing_file(self, connector: GrypeConnector) -> None:
        result = connector.parse(FIXTURES / "nonexistent.json")
        assert result.ok is False


class TestGrypeNoDebtFinding:
    def test_no_debt_finding_creation(self, connector: GrypeConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            assert hasattr(item, "evidence_id")
            assert not hasattr(item, "finding_id")
