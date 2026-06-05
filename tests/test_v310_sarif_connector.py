"""v3.1.0 — SARIF connector tests.

Tests SARIF v2.1.0 import for:
- Valid fixtures with locations
- Empty results
- Missing locations
- Malformed JSON
- Multi-run files
- Provenance and confidence on imported items
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pharabius.core.connectors.base import CONNECTOR_EVIDENCE_SOURCE
from pharabius.core.connectors.sarif import SarifConnector

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "connectors" / "sarif"


@pytest.fixture
def connector() -> SarifConnector:
    return SarifConnector()


class TestSarifConnectorProperties:
    def test_name(self) -> None:
        assert SarifConnector().name == "sarif"

    def test_version(self) -> None:
        assert SarifConnector().version == "1.0.0"


class TestSarifValidImport:
    def test_minimal_valid(self, connector: SarifConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.sarif.json")
        assert result.ok is True
        assert result.imported_count == 2
        assert result.skipped_count == 0
        assert len(result.evidence) == 2

    def test_evidence_source(self, connector: SarifConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.sarif.json")
        for item in result.evidence:
            assert item.source == CONNECTOR_EVIDENCE_SOURCE

    def test_file_paths_preserved(self, connector: SarifConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.sarif.json")
        paths = [e.location.file for e in result.evidence]
        assert "src/db/query.py" in paths
        assert "src/config/settings.py" in paths

    def test_line_numbers_preserved(self, connector: SarifConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.sarif.json")
        lines = {e.location.file: e.location.line_start for e in result.evidence}
        assert lines["src/db/query.py"] == 42
        assert lines["src/config/settings.py"] == 15

    def test_rule_ids_preserved(self, connector: SarifConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.sarif.json")
        provenance = [e.metadata["connector_provenance"] for e in result.evidence]
        rule_ids = {p["source_rule_id"] for p in provenance}
        assert "TS001" in rule_ids
        assert "TS002" in rule_ids

    def test_tool_name_preserved(self, connector: SarifConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.sarif.json")
        p = result.evidence[0].metadata["connector_provenance"]
        assert p["source_tool_name"] == "TestScanner"
        assert p["source_tool_version"] == "1.2.3"

    def test_messages_in_summary(self, connector: SarifConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.sarif.json")
        summaries = [e.summary for e in result.evidence]
        assert any("SQL injection" in s for s in summaries)
        assert any("Hardcoded secret" in s for s in summaries)

    def test_confidence_high_with_full_data(self, connector: SarifConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.sarif.json")
        # All items have location, rule_id, and message
        for item in result.evidence:
            assert item.confidence == "High"
            assert item.metadata.get("confidence_reason") == "location_rule_and_message_present"

    def test_evidence_ids_sequential(self, connector: SarifConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.sarif.json")
        ids = [e.evidence_id for e in result.evidence]
        assert ids[0] == "EXT-SARIF-000001"
        assert ids[1] == "EXT-SARIF-000002"


class TestSarifEmptyResults:
    def test_empty_results_ok(self, connector: SarifConnector) -> None:
        result = connector.parse(FIXTURES / "empty-results.sarif.json")
        assert result.ok is True
        assert result.imported_count == 0
        assert result.evidence == []


class TestSarifMissingLocation:
    def test_missing_location_imports(self, connector: SarifConnector) -> None:
        result = connector.parse(FIXTURES / "missing-location.sarif.json")
        assert result.ok is True
        assert result.imported_count == 2

    def test_missing_location_lowered_confidence(self, connector: SarifConnector) -> None:
        result = connector.parse(FIXTURES / "missing-location.sarif.json")
        # First has rule_id but no location -> Medium
        # Second has rule_id but empty locations -> Medium
        for item in result.evidence:
            assert item.confidence in ("Medium", "Low")

    def test_missing_location_has_reason(self, connector: SarifConnector) -> None:
        result = connector.parse(FIXTURES / "missing-location.sarif.json")
        for item in result.evidence:
            assert "confidence_reason" in item.metadata


class TestSarifMalformed:
    def test_malformed_json_not_ok(self, connector: SarifConnector) -> None:
        result = connector.parse(FIXTURES / "malformed.sarif.json")
        assert result.ok is False
        assert result.imported_count == 0
        assert result.evidence == []
        assert len(result.errors) > 0

    def test_malformed_json_has_error_detail(self, connector: SarifConnector) -> None:
        result = connector.parse(FIXTURES / "malformed.sarif.json")
        assert any("Invalid JSON" in e or "Cannot read" in e for e in result.errors)

    def test_nonexistent_file(self, connector: SarifConnector) -> None:
        result = connector.parse(Path("/nonexistent/file.sarif"))
        assert result.ok is False
        assert len(result.errors) > 0


class TestSarifMultiRun:
    def test_multi_run_imports_all(self, connector: SarifConnector) -> None:
        result = connector.parse(FIXTURES / "multi-run.sarif.json")
        assert result.ok is True
        assert result.imported_count == 2

    def test_multi_run_different_tools(self, connector: SarifConnector) -> None:
        result = connector.parse(FIXTURES / "multi-run.sarif.json")
        tools = {e.metadata["connector_provenance"]["source_tool_name"] for e in result.evidence}
        assert tools == {"Scanner1", "Scanner2"}

    def test_multi_run_different_rule_ids(self, connector: SarifConnector) -> None:
        result = connector.parse(FIXTURES / "multi-run.sarif.json")
        rules = {e.metadata["connector_provenance"]["source_rule_id"] for e in result.evidence}
        assert rules == {"S1-001", "S2-001"}
