"""v3.23.0 — Governance quality metrics tests.

Proves metrics are read-only: no behavior change, no mutation,
no findings/advisories/work packages from diagnostics.
"""

from __future__ import annotations

import pytest

from pharabius.core.signals.models import GovernedSignal, SignalDisposition, SignalFamily
from pharabius.core.signals.policy import output_behavior
from pharabius.core.signals.quality import (
    GovernanceQualityDiagnostic,
    build_governance_quality_metrics,
    governance_quality_metrics_to_dict,
)


def _sig(
    disposition: SignalDisposition = SignalDisposition.FINDING,
    family: SignalFamily = SignalFamily.RUNTIME,
    evidence_ids: list[str] | None = None,
    metadata: dict | None = None,
    severity: str = "Medium",
    confidence: str = "High",
) -> GovernedSignal:
    return GovernedSignal(
        signal_id="test-sig",
        family=family,
        kind="test",
        disposition=disposition,
        category="TD-TEST",
        severity=severity,
        confidence=confidence,
        evidence_ids=evidence_ids if evidence_ids is not None else ["ev1"],
        source_signal_ids=[],
        title="Test",
        summary="Test",
        explanation="Test",
        metadata=metadata if metadata is not None else {"spec_kind": "test"},
    )


# ═══════════════════════════════════════════════════════════════════════
# S01 — Model structure
# ═══════════════════════════════════════════════════════════════════════


class TestModelStructure:
    """Quality metric dataclasses are frozen and well-formed."""

    def test_metrics_frozen(self) -> None:
        m = build_governance_quality_metrics([])
        with pytest.raises(AttributeError):
            m.total_signals = 99  # type: ignore

    def test_diagnostic_frozen(self) -> None:
        d = GovernanceQualityDiagnostic(code="GQM-001", severity="warning", message="test")
        with pytest.raises(AttributeError):
            d.code = "other"  # type: ignore

    def test_diagnostic_severity_values(self) -> None:
        """Diagnostics use only 'info' or 'warning' severity."""
        d1 = GovernanceQualityDiagnostic(code="GQM-001", severity="info", message="t")
        d2 = GovernanceQualityDiagnostic(code="GQM-002", severity="warning", message="t")
        assert d1.severity in ("info", "warning")
        assert d2.severity in ("info", "warning")


# ═══════════════════════════════════════════════════════════════════════
# S02 — Coverage metrics
# ═══════════════════════════════════════════════════════════════════════


class TestCoverageMetrics:
    """Evidence coverage ratios computed correctly."""

    def test_finding_with_evidence_coverage_1(self) -> None:
        m = build_governance_quality_metrics([_sig(SignalDisposition.FINDING)])
        assert m.finding_evidence_coverage == 1.0

    def test_finding_without_evidence_coverage_0(self) -> None:
        m = build_governance_quality_metrics(
            [
                _sig(SignalDisposition.FINDING, evidence_ids=[]),
            ]
        )
        assert m.finding_evidence_coverage == 0.0

    def test_advisory_with_evidence_coverage_1(self) -> None:
        m = build_governance_quality_metrics([_sig(SignalDisposition.ADVISORY)])
        assert m.advisory_evidence_coverage == 1.0

    def test_informational_with_evidence_coverage_1(self) -> None:
        m = build_governance_quality_metrics([_sig(SignalDisposition.INFORMATIONAL)])
        assert m.informational_evidence_coverage == 1.0

    def test_mixed_coverage(self) -> None:
        sigs = [
            _sig(SignalDisposition.FINDING, evidence_ids=["ev1"]),
            _sig(SignalDisposition.FINDING, evidence_ids=[]),
        ]
        m = build_governance_quality_metrics(sigs)
        assert m.finding_evidence_coverage == 0.5

    def test_metadata_coverage(self) -> None:
        sigs = [
            _sig(SignalDisposition.FINDING, metadata={"key": "val"}),
            _sig(SignalDisposition.FINDING, metadata={}),
        ]
        m = build_governance_quality_metrics(sigs)
        assert m.finding_metadata_coverage == 0.5


class TestZeroDenominator:
    """Zero denominator → coverage = 1.0."""

    def test_no_finding_signals_coverage_1(self) -> None:
        m = build_governance_quality_metrics([_sig(SignalDisposition.ADVISORY)])
        assert m.finding_evidence_coverage == 1.0
        assert m.finding_metadata_coverage == 1.0

    def test_no_advisory_signals_coverage_1(self) -> None:
        m = build_governance_quality_metrics([_sig(SignalDisposition.FINDING)])
        assert m.advisory_evidence_coverage == 1.0

    def test_no_informational_signals_coverage_1(self) -> None:
        m = build_governance_quality_metrics([_sig(SignalDisposition.FINDING)])
        assert m.informational_evidence_coverage == 1.0

    def test_empty_signals_all_coverage_1(self) -> None:
        m = build_governance_quality_metrics([])
        assert m.total_signals == 0
        assert m.finding_evidence_coverage == 1.0
        assert m.advisory_evidence_coverage == 1.0
        assert m.informational_evidence_coverage == 1.0


# ═══════════════════════════════════════════════════════════════════════
# S03 — Diagnostics
# ═══════════════════════════════════════════════════════════════════════


class TestDiagnostics:
    """Threshold-free diagnostics are info/warning only."""

    def test_gqm001_finding_no_evidence(self) -> None:
        m = build_governance_quality_metrics(
            [
                _sig(SignalDisposition.FINDING, evidence_ids=[]),
            ]
        )
        codes = [d.code for d in m.diagnostics]
        assert "GQM-001" in codes
        diag = next(d for d in m.diagnostics if d.code == "GQM-001")
        assert diag.severity == "warning"

    def test_gqm002_advisory_no_evidence_no_metadata(self) -> None:
        m = build_governance_quality_metrics(
            [
                _sig(SignalDisposition.ADVISORY, evidence_ids=[], metadata={}),
            ]
        )
        codes = [d.code for d in m.diagnostics]
        assert "GQM-002" in codes
        diag = next(d for d in m.diagnostics if d.code == "GQM-002")
        assert diag.severity == "info"

    def test_gqm003_informational_no_evidence(self) -> None:
        m = build_governance_quality_metrics(
            [
                _sig(SignalDisposition.INFORMATIONAL, evidence_ids=[]),
            ]
        )
        codes = [d.code for d in m.diagnostics]
        assert "GQM-003" in codes

    def test_gqm004_empty_metadata(self) -> None:
        m = build_governance_quality_metrics(
            [
                _sig(SignalDisposition.FINDING, metadata={}),
            ]
        )
        codes = [d.code for d in m.diagnostics]
        assert "GQM-004" in codes

    def test_gqm005_unexpected_severity(self) -> None:
        m = build_governance_quality_metrics(
            [
                _sig(SignalDisposition.FINDING, severity="Extreme"),
            ]
        )
        codes = [d.code for d in m.diagnostics]
        assert "GQM-005" in codes

    def test_diagnostics_never_critical(self) -> None:
        m = build_governance_quality_metrics(
            [
                _sig(SignalDisposition.FINDING, evidence_ids=[], metadata={}, severity="Extreme"),
            ]
        )
        for d in m.diagnostics:
            assert d.severity in ("info", "warning"), f"{d.code}: {d.severity}"

    def test_no_diagnostics_for_clean_signals(self) -> None:
        m = build_governance_quality_metrics(
            [
                _sig(SignalDisposition.FINDING),
            ]
        )
        assert len(m.diagnostics) == 0


class TestAdvisoryMetadataBasis:
    """Advisory with non-empty metadata counts as having basis."""

    def test_advisory_with_metadata_no_gqm002(self) -> None:
        """Advisory with metadata (even without evidence_ids) has basis."""
        m = build_governance_quality_metrics(
            [
                _sig(SignalDisposition.ADVISORY, evidence_ids=[], metadata={"reason": "missing"}),
            ]
        )
        codes = [d.code for d in m.diagnostics]
        assert "GQM-002" not in codes

    def test_advisory_with_evidence_no_gqm002(self) -> None:
        m = build_governance_quality_metrics(
            [
                _sig(SignalDisposition.ADVISORY, evidence_ids=["ev1"]),
            ]
        )
        codes = [d.code for d in m.diagnostics]
        assert "GQM-002" not in codes


# ═══════════════════════════════════════════════════════════════════════
# S07 — No behavior change
# ═══════════════════════════════════════════════════════════════════════


class TestNoBehaviorChange:
    """Metrics do not alter signal behavior."""

    def test_metrics_do_not_mutate_signals(self) -> None:
        sig = _sig(SignalDisposition.FINDING)
        original_id = sig.signal_id
        original_disposition = sig.disposition
        build_governance_quality_metrics([sig])
        assert sig.signal_id == original_id
        assert sig.disposition == original_disposition

    def test_metrics_do_not_change_output_behavior(self) -> None:
        sig = _sig(SignalDisposition.FINDING)
        behav_before = output_behavior(sig)
        build_governance_quality_metrics([sig])
        behav_after = output_behavior(sig)
        assert behav_before == behav_after

    def test_diagnostics_not_findings(self) -> None:
        """GQM diagnostics are not findings, advisories, or work packages."""
        m = build_governance_quality_metrics(
            [
                _sig(SignalDisposition.FINDING, evidence_ids=[]),
            ]
        )
        for d in m.diagnostics:
            # Diagnostic is a plain dataclass, not a GovernedSignal
            assert not isinstance(d, GovernedSignal)
            assert not hasattr(d, "disposition")

    def test_diagnostics_do_not_affect_output_behavior(self) -> None:
        sig = _sig(SignalDisposition.FINDING, evidence_ids=[])
        behav_before = output_behavior(sig)
        m = build_governance_quality_metrics([sig])
        # Diagnostics generated but behavior unchanged
        behav_after = output_behavior(sig)
        assert behav_before == behav_after
        assert len(m.diagnostics) > 0  # Diagnostics exist but don't change anything


# ═══════════════════════════════════════════════════════════════════════
# S04 — Serialization
# ═══════════════════════════════════════════════════════════════════════


class TestSerialization:
    """governance_quality_metrics_to_dict() serializes without data loss."""

    def test_all_fields_present(self) -> None:
        m = build_governance_quality_metrics([_sig(SignalDisposition.FINDING)])
        d = governance_quality_metrics_to_dict(m)
        assert "total_signals" in d
        assert "by_family" in d
        assert "by_disposition" in d
        assert "by_severity" in d
        assert "by_confidence" in d
        assert "finding_evidence_coverage" in d
        assert "finding_metadata_coverage" in d
        assert "advisory_evidence_coverage" in d
        assert "informational_evidence_coverage" in d
        assert "diagnostics" in d

    def test_values_preserved(self) -> None:
        m = build_governance_quality_metrics([_sig(SignalDisposition.FINDING)])
        d = governance_quality_metrics_to_dict(m)
        assert d["total_signals"] == m.total_signals
        assert d["finding_evidence_coverage"] == m.finding_evidence_coverage
        assert d["diagnostics"] == [
            {
                "code": diag.code,
                "severity": diag.severity,
                "message": diag.message,
                "family": diag.family,
            }
            for diag in m.diagnostics
        ]

    def test_diagnostics_serialized(self) -> None:
        m = build_governance_quality_metrics(
            [
                _sig(SignalDisposition.FINDING, evidence_ids=[]),
            ]
        )
        d = governance_quality_metrics_to_dict(m)
        assert len(d["diagnostics"]) > 0
        for diag_dict in d["diagnostics"]:
            assert "code" in diag_dict
            assert "severity" in diag_dict
            assert "message" in diag_dict
