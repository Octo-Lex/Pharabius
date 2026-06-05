"""v3.3.0 Syft connector tests.

Acceptance criteria verified:
  3. Syft connector parses valid JSON and produces EvidenceItem list.
  4-7, 9, 12-14, 21-24 same pattern.
  21. Syft confidence is SBOM-aware and does not require vulnerability rule IDs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pharabius.core.connectors.base import CONNECTOR_EVIDENCE_SOURCE, ConnectorInterface
from pharabius.core.connectors.syft import SyftConnector

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "connectors" / "syft"


@pytest.fixture
def connector() -> SyftConnector:
    return SyftConnector()


class TestSyftInterface:
    def test_name(self, connector: SyftConnector) -> None:
        assert connector.name == "syft"

    def test_version(self, connector: SyftConnector) -> None:
        assert connector.version == "1.0.0"

    def test_is_connector_interface(self, connector: SyftConnector) -> None:
        assert isinstance(connector, ConnectorInterface)


class TestSyftValidInput:
    def test_minimal_valid(self, connector: SyftConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        assert result.ok is True
        assert result.imported_count == 2
        assert len(result.evidence) == 2

    def test_evidence_source(self, connector: SyftConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            assert item.source == CONNECTOR_EVIDENCE_SOURCE
            assert item.type == "external_scanner_result"
            assert item.category == "TD-EXT"

    def test_evidence_ids_prefixed(self, connector: SyftConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            assert item.evidence_id.startswith("EXT-SYFT-")

    def test_provenance_populated(self, connector: SyftConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        prov = result.evidence[0].metadata["connector_provenance"]
        assert prov["connector_name"] == "syft"
        assert prov["connector_version"] == "1.0.0"
        assert prov["source_format"] == "syft"
        # SBOM has no rules
        assert prov["source_rule_id"] == ""

    def test_tool_version_from_descriptor(self, connector: SyftConnector) -> None:
        """AC22: Source tool version extracted from Syft descriptor."""
        result = connector.parse(FIXTURES / "minimal-valid.json")
        prov = result.evidence[0].metadata["connector_provenance"]
        assert prov["connector_version"] == "1.0.0"
        assert prov["source_tool_version"] == "1.20.0"
        assert prov["source_tool_name"] == "syft"

    def test_sbom_coordinates(self, connector: SyftConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        coords = result.evidence[0].metadata["package_coordinates"]
        assert "pkg_name" in coords
        assert "version" in coords
        assert "purl" in coords
        assert "language" in coords

    def test_licenses_in_coordinates(self, connector: SyftConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        coords = result.evidence[0].metadata["package_coordinates"]
        assert "licenses" in coords
        assert isinstance(coords["licenses"], list)

    def test_evidence_location_from_real_path(self, connector: SyftConnector) -> None:
        """AC24: Syft provides real file paths from locations[].path."""
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            assert item.location.file == "requirements.txt"

    def test_sbom_confidence_high(self, connector: SyftConnector) -> None:
        """AC21: SBOM confidence uses name+version/purl+location, not vuln IDs."""
        result = connector.parse(FIXTURES / "minimal-valid.json")
        # Has name + version + purl + location → High
        for item in result.evidence:
            assert item.confidence == "High"
            assert "sbom" in item.metadata["confidence_reason"]

    def test_no_vulnerability_id_required(self, connector: SyftConnector) -> None:
        """AC21: Syft confidence is not penalized for lacking vulnerability IDs."""
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            # No vuln ID, but still High confidence
            prov = item.metadata["connector_provenance"]
            assert prov["source_rule_id"] == ""
            assert item.confidence == "High"

    def test_confidence_reason_present(self, connector: SyftConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            assert "confidence_reason" in item.metadata


class TestSyftMultiTarget:
    def test_multi_target(self, connector: SyftConnector) -> None:
        result = connector.parse(FIXTURES / "multi-target.json")
        assert result.ok is True
        assert result.imported_count == 3

    def test_different_package_types(self, connector: SyftConnector) -> None:
        result = connector.parse(FIXTURES / "multi-target.json")
        types = [
            item.metadata["package_coordinates"].get("pkg_type", "") for item in result.evidence
        ]
        assert "apk" in types
        assert "python" in types

    def test_real_file_paths_populated(self, connector: SyftConnector) -> None:
        result = connector.parse(FIXTURES / "multi-target.json")
        for item in result.evidence:
            assert item.location.file != ""


class TestSyftEdgeCases:
    def test_empty_results(self, connector: SyftConnector) -> None:
        result = connector.parse(FIXTURES / "empty-results.json")
        assert result.ok is True
        assert result.imported_count == 0
        assert result.evidence == []
        assert len(result.warnings) >= 1

    def test_malformed_json(self, connector: SyftConnector) -> None:
        result = connector.parse(FIXTURES / "malformed.json")
        assert result.ok is False
        assert len(result.errors) >= 1

    def test_missing_location_medium_confidence(self, connector: SyftConnector) -> None:
        """SBOM without location gets Medium (has name, no version/purl)."""
        result = connector.parse(FIXTURES / "missing-location.json")
        assert result.ok is True
        assert result.imported_count == 1
        item = result.evidence[0]
        # Has name but no version, no purl, no location → Medium or Low
        assert item.confidence in ("Medium", "Low")

    def test_missing_file(self, connector: SyftConnector) -> None:
        result = connector.parse(FIXTURES / "nonexistent.json")
        assert result.ok is False


class TestSyftNoDebtFinding:
    def test_no_debt_finding_creation(self, connector: SyftConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            assert hasattr(item, "evidence_id")
            assert not hasattr(item, "finding_id")
