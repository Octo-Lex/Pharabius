"""v3.1.0 — Semgrep connector tests.

Tests Semgrep JSON import for:
- Valid fixtures with paths and lines
- Empty results
- Missing paths/lines
- Malformed JSON
- Provenance and confidence on imported items
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pharabius.core.connectors.base import CONNECTOR_EVIDENCE_SOURCE
from pharabius.core.connectors.semgrep import SemgrepConnector

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "connectors" / "semgrep"


@pytest.fixture
def connector() -> SemgrepConnector:
    return SemgrepConnector()


class TestSemgrepConnectorProperties:
    def test_name(self) -> None:
        assert SemgrepConnector().name == "semgrep"

    def test_version(self) -> None:
        assert SemgrepConnector().version == "1.0.0"


class TestSemgrepValidImport:
    def test_minimal_valid(self, connector: SemgrepConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        assert result.ok is True
        assert result.imported_count == 2
        assert len(result.evidence) == 2

    def test_evidence_source(self, connector: SemgrepConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            assert item.source == CONNECTOR_EVIDENCE_SOURCE

    def test_paths_preserved(self, connector: SemgrepConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        paths = [e.location.file for e in result.evidence]
        assert "src/server/handler.py" in paths
        assert "src/utils/compare.py" in paths

    def test_line_numbers_preserved(self, connector: SemgrepConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        lines = {e.location.file: e.location.line_start for e in result.evidence}
        assert lines["src/server/handler.py"] == 33
        assert lines["src/utils/compare.py"] == 12

    def test_check_ids_preserved(self, connector: SemgrepConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        provenance = [e.metadata["connector_provenance"] for e in result.evidence]
        check_ids = {p["source_rule_id"] for p in provenance}
        assert "python.lang.security.audit.dangerous-system-call" in check_ids
        assert "python.lang.correctness.useless-eqeq" in check_ids

    def test_messages_in_summary(self, connector: SemgrepConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        summaries = [e.summary for e in result.evidence]
        assert any("os.system" in s for s in summaries)
        assert any("Identical expressions" in s for s in summaries)

    def test_severity_in_metadata(self, connector: SemgrepConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        severities = [e.metadata.get("source_severity", "") for e in result.evidence]
        assert "ERROR" in severities
        assert "WARNING" in severities

    def test_confidence_high_with_full_data(self, connector: SemgrepConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            assert item.confidence == "High"
            assert item.metadata["confidence_reason"] == "location_rule_and_message_present"

    def test_tool_name_is_semgrep(self, connector: SemgrepConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            assert item.metadata["connector_provenance"]["source_tool_name"] == "semgrep"

    def test_tool_version_from_output(self, connector: SemgrepConnector) -> None:
        result = connector.parse(FIXTURES / "minimal-valid.json")
        for item in result.evidence:
            assert item.metadata["connector_provenance"]["source_tool_version"] == "1.20.0"


class TestSemgrepEmptyResults:
    def test_empty_results_ok(self, connector: SemgrepConnector) -> None:
        result = connector.parse(FIXTURES / "empty-results.json")
        assert result.ok is True
        assert result.imported_count == 0
        assert result.evidence == []
        assert len(result.warnings) == 1


class TestSemgrepMissingLocation:
    def test_missing_data_imports(self, connector: SemgrepConnector) -> None:
        result = connector.parse(FIXTURES / "missing-location.json")
        assert result.ok is True
        assert result.imported_count == 2

    def test_missing_path_lowered_confidence(self, connector: SemgrepConnector) -> None:
        result = connector.parse(FIXTURES / "missing-location.json")
        # First: empty path, has check_id -> Medium
        # Second: no check_id, has path -> Medium
        for item in result.evidence:
            assert item.confidence in ("Medium", "Low")

    def test_missing_data_has_confidence_reason(self, connector: SemgrepConnector) -> None:
        result = connector.parse(FIXTURES / "missing-location.json")
        for item in result.evidence:
            assert "confidence_reason" in item.metadata


class TestSemgrepMalformed:
    def test_malformed_json_not_ok(self, connector: SemgrepConnector) -> None:
        result = connector.parse(FIXTURES / "malformed.json")
        assert result.ok is False
        assert result.imported_count == 0
        assert result.evidence == []
        assert len(result.errors) > 0

    def test_nonexistent_file(self, connector: SemgrepConnector) -> None:
        result = connector.parse(Path("/nonexistent/semgrep.json"))
        assert result.ok is False
        assert len(result.errors) > 0
