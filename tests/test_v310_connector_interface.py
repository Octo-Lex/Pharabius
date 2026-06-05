"""v3.1.0 — Connector interface, provenance, and confidence tests.

Tests for:
- ConnectorResult model
- ConnectorInterface contract
- ConnectorProvenance serialization
- Confidence assignment (deterministic levels and reasons)
- Negative test: connectors never create DebtFinding
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pharabius.core.connectors.base import (
    CONNECTOR_EVIDENCE_SOURCE,
    ConnectorInterface,
    ConnectorResult,
)
from pharabius.core.connectors.confidence import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    REASON_LOCATION_RULE_MESSAGE,
    REASON_MISSING_LOCATION_OR_FALLBACK,
    REASON_PARTIAL_LOCATION_OR_MISSING_RULE,
    apply_confidence,
    assign_confidence,
)
from pharabius.core.connectors.provenance import ConnectorProvenance
from pharabius.schemas.evidence import EvidenceItem, EvidenceLocation

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "connectors"


# ═══════════════════════════════════════════════════════════════════════
# S01: Connector interface
# ═══════════════════════════════════════════════════════════════════════


class TestConnectorResult:
    def test_default_values(self) -> None:
        r = ConnectorResult(
            connector_name="test",
            connector_version="1.0",
            source_format="test",
            source_file="test.json",
        )
        assert r.ok is True
        assert r.evidence == []
        assert r.imported_count == 0
        assert r.skipped_count == 0
        assert r.warnings == []
        assert r.errors == []

    def test_error_result(self) -> None:
        r = ConnectorResult(
            connector_name="test",
            connector_version="1.0",
            source_format="test",
            source_file="bad.json",
            ok=False,
            errors=["Invalid JSON"],
        )
        assert r.ok is False
        assert r.evidence == []
        assert len(r.errors) == 1

    def test_successful_result(self) -> None:
        item = EvidenceItem(
            evidence_id="EXT-001",
            source=CONNECTOR_EVIDENCE_SOURCE,
            type="external_scanner_result",
            category="TD-EXT",
            summary="Test finding",
        )
        r = ConnectorResult(
            connector_name="test",
            connector_version="1.0",
            source_format="test",
            source_file="test.json",
            evidence=[item],
            imported_count=1,
        )
        assert r.ok is True
        assert len(r.evidence) == 1
        assert r.evidence[0].source == CONNECTOR_EVIDENCE_SOURCE


class TestConnectorInterface:
    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            ConnectorInterface()  # type: ignore[abstract]

    def test_source_constant(self) -> None:
        assert CONNECTOR_EVIDENCE_SOURCE == "external_connector"


# ═══════════════════════════════════════════════════════════════════════
# S04: Provenance
# ═══════════════════════════════════════════════════════════════════════


class TestConnectorProvenance:
    def test_provenance_creation(self) -> None:
        p = ConnectorProvenance(
            connector_name="sarif",
            connector_version="1.0.0",
            source_format="sarif",
            source_file="test.sarif.json",
            source_tool_name="TestScanner",
            source_tool_version="2.0",
            source_rule_id="TS001",
            source_record_index=1,
            imported_at="2026-01-01T00:00:00Z",
        )
        assert p.connector_name == "sarif"
        assert p.source_rule_id == "TS001"

    def test_provenance_to_metadata(self) -> None:
        p = ConnectorProvenance(
            connector_name="semgrep",
            connector_version="1.0.0",
            source_format="semgrep",
            source_file="semgrep.json",
            source_tool_name="semgrep",
            source_record_index=3,
        )
        d = p.to_metadata_dict()
        assert isinstance(d, dict)
        assert d["connector_name"] == "semgrep"
        assert d["source_record_index"] == 3

    def test_provenance_serialization_roundtrip(self) -> None:
        p = ConnectorProvenance(
            connector_name="sarif",
            connector_version="1.0.0",
            source_format="sarif",
            source_file="test.sarif",
            source_tool_name="Tool",
            source_rule_id="R1",
            source_record_index=1,
        )
        serialized = json.dumps(p.to_metadata_dict())
        restored = json.loads(serialized)
        assert restored["connector_name"] == "sarif"
        assert restored["source_rule_id"] == "R1"

    def test_provenance_survives_in_evidence_metadata(self) -> None:
        p = ConnectorProvenance(
            connector_name="sarif",
            connector_version="1.0.0",
            source_format="sarif",
            source_file="test.sarif",
        )
        item = EvidenceItem(
            evidence_id="EXT-001",
            source=CONNECTOR_EVIDENCE_SOURCE,
            type="external_scanner_result",
            category="TD-EXT",
            summary="Test",
            metadata={"connector_provenance": p.to_metadata_dict()},
        )
        assert item.metadata["connector_provenance"]["connector_name"] == "sarif"


# ═══════════════════════════════════════════════════════════════════════
# S05: Confidence model
# ═══════════════════════════════════════════════════════════════════════


class TestConfidenceAssignment:
    def test_high_confidence(self) -> None:
        level, reason = assign_confidence(has_location=True, has_rule_id=True, has_message=True)
        assert level == CONFIDENCE_HIGH
        assert reason == REASON_LOCATION_RULE_MESSAGE

    def test_medium_location_no_rule(self) -> None:
        level, reason = assign_confidence(has_location=True, has_rule_id=False, has_message=True)
        assert level == CONFIDENCE_MEDIUM
        assert reason == REASON_PARTIAL_LOCATION_OR_MISSING_RULE

    def test_medium_rule_no_location(self) -> None:
        level, _reason = assign_confidence(has_location=False, has_rule_id=True, has_message=True)
        assert level == CONFIDENCE_MEDIUM

    def test_low_nothing(self) -> None:
        level, reason = assign_confidence(has_location=False, has_rule_id=False, has_message=False)
        assert level == CONFIDENCE_LOW
        assert reason == REASON_MISSING_LOCATION_OR_FALLBACK

    def test_low_message_only(self) -> None:
        level, _reason = assign_confidence(has_location=False, has_rule_id=False, has_message=True)
        assert level == CONFIDENCE_LOW

    def test_apply_confidence_to_evidence(self) -> None:
        item = EvidenceItem(
            evidence_id="EXT-001",
            source=CONNECTOR_EVIDENCE_SOURCE,
            type="external_scanner_result",
            category="TD-EXT",
            summary="Test",
            location=EvidenceLocation(file="src/main.py", line_start=10),
            metadata={"connector_provenance": {"connector_name": "test", "source_rule_id": "R1"}},
        )
        updated = apply_confidence(item, has_location=True, has_rule_id=True, has_message=True)
        assert updated.confidence == "High"
        assert updated.metadata["confidence_reason"] == REASON_LOCATION_RULE_MESSAGE
        # Original not mutated
        assert "confidence_reason" not in item.metadata


# ═══════════════════════════════════════════════════════════════════════
# Negative: connectors never create DebtFinding
# ═══════════════════════════════════════════════════════════════════════


class TestNoFindingBypass:
    def test_connector_result_evidence_is_evidence_item(self) -> None:
        """ConnectorResult.evidence contains only EvidenceItem, never DebtFinding."""
        from pharabius.schemas.finding import DebtFinding

        item = EvidenceItem(
            evidence_id="EXT-001",
            source=CONNECTOR_EVIDENCE_SOURCE,
            type="external_scanner_result",
            category="TD-EXT",
            summary="Test",
        )
        r = ConnectorResult(
            connector_name="test",
            connector_version="1.0",
            source_format="test",
            source_file="test.json",
            evidence=[item],
            imported_count=1,
        )
        assert all(isinstance(e, EvidenceItem) for e in r.evidence)
        assert not any(isinstance(e, DebtFinding) for e in r.evidence)

    def test_connector_modules_do_not_import_debt_finding(self) -> None:
        """Connector modules should not import DebtFinding."""
        import inspect

        import pharabius.core.connectors.sarif as sarif_mod
        import pharabius.core.connectors.semgrep as semgrep_mod

        for mod in [sarif_mod, semgrep_mod]:
            source = inspect.getsource(mod)
            assert "DebtFinding" not in source, (
                f"{mod.__name__} references DebtFinding — connectors must not create findings"
            )

    def test_evidence_source_is_external_connector(self) -> None:
        """All connector evidence has source='external_connector'."""
        assert CONNECTOR_EVIDENCE_SOURCE == "external_connector"
