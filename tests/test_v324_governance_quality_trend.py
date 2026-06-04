"""v3.24.0 tests — Governance Quality Trend Baseline.

Descriptive-only trend/delta between governance quality snapshots.
No gates, thresholds, enforcement, or signal mutation.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pharabius.core.signals.quality import (
    GovernanceQualityMetrics,
    GovernanceQualityTrend,
    build_governance_quality_trend,
    governance_quality_trend_to_dict,
)


# ══════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════

def _make_metrics(
    total: int = 10,
    finding_ev: float = 0.8,
    finding_meta: float = 0.6,
    advisory_ev: float = 1.0,
    informational_ev: float = 1.0,
    diagnostics: list | None = None,
) -> GovernanceQualityMetrics:
    return GovernanceQualityMetrics(
        total_signals=total,
        by_family={"test": total},
        by_disposition={"FINDING": total},
        by_severity={"High": total},
        by_confidence={"High": total},
        finding_evidence_coverage=finding_ev,
        finding_metadata_coverage=finding_meta,
        advisory_evidence_coverage=advisory_ev,
        informational_evidence_coverage=informational_ev,
        diagnostics=diagnostics or [],
    )


def _make_dict_metrics(
    total: int = 10,
    finding_ev: float = 0.8,
    finding_meta: float = 0.6,
    advisory_ev: float = 1.0,
    informational_ev: float = 1.0,
    diagnostics: list | None = None,
) -> dict:
    return {
        "total_signals": total,
        "finding_evidence_coverage": finding_ev,
        "finding_metadata_coverage": finding_meta,
        "advisory_evidence_coverage": advisory_ev,
        "informational_evidence_coverage": informational_ev,
        "diagnostics": diagnostics or [],
    }


# ══════════════════════════════════════════════════════════════════
# Test: Model
# ══════════════════════════════════════════════════════════════════

class TestModel:
    def test_trend_is_frozen(self):
        trend = build_governance_quality_trend(
            current=_make_metrics(), previous=None,
        )
        with pytest.raises(AttributeError):
            trend.has_previous = True  # type: ignore[misc]

    def test_schema_version(self):
        trend = build_governance_quality_trend(
            current=_make_metrics(), previous=None,
        )
        assert trend.schema_version == "governance_quality_trend.v1"

    def test_notes_are_immutable_tuple(self):
        trend = build_governance_quality_trend(
            current=_make_metrics(), previous=None,
        )
        assert isinstance(trend.notes, tuple)


# ══════════════════════════════════════════════════════════════════
# Test: Builder
# ══════════════════════════════════════════════════════════════════

class TestBuilder:
    def test_no_previous_returns_has_previous_false(self):
        trend = build_governance_quality_trend(
            current=_make_metrics(), previous=None,
        )
        assert trend.has_previous is False

    def test_no_previous_deltas_are_zero(self):
        trend = build_governance_quality_trend(
            current=_make_metrics(), previous=None,
        )
        assert trend.total_signals_delta == 0
        assert trend.evidence_coverage_delta == 0.0
        assert trend.diagnostic_count_delta == 0

    def test_computes_total_signals_delta(self):
        trend = build_governance_quality_trend(
            current=_make_metrics(total=12),
            previous=_make_dict_metrics(total=10),
        )
        assert trend.total_signals_delta == 2

    def test_computes_evidence_coverage_delta(self):
        trend = build_governance_quality_trend(
            current=_make_metrics(finding_ev=0.9),
            previous=_make_dict_metrics(finding_ev=0.8),
        )
        assert trend.evidence_coverage_delta != 0.0

    def test_computes_metadata_coverage_delta(self):
        trend = build_governance_quality_trend(
            current=_make_metrics(finding_meta=0.8),
            previous=_make_dict_metrics(finding_meta=0.6),
        )
        assert trend.metadata_coverage_delta > 0

    def test_computes_finding_evidence_coverage_delta(self):
        trend = build_governance_quality_trend(
            current=_make_metrics(finding_ev=0.9),
            previous=_make_dict_metrics(finding_ev=0.7),
        )
        assert trend.finding_evidence_coverage_delta > 0

    def test_computes_advisory_basis_coverage_delta(self):
        trend = build_governance_quality_trend(
            current=_make_metrics(advisory_ev=1.0),
            previous=_make_dict_metrics(advisory_ev=0.8),
        )
        assert trend.advisory_basis_coverage_delta > 0

    def test_computes_diagnostic_count_delta(self):
        trend = build_governance_quality_trend(
            current=_make_metrics(diagnostics=[{"code": "GQM-001"}]),
            previous=_make_dict_metrics(diagnostics=[]),
        )
        assert trend.diagnostic_count_delta == 1

    def test_supports_dict_current_and_previous(self):
        trend = build_governance_quality_trend(
            current=_make_dict_metrics(total=15),
            previous=_make_dict_metrics(total=10),
        )
        assert trend.has_previous is True
        assert trend.total_signals_delta == 5

    def test_missing_previous_governance_quality_non_throwing(self):
        # previous is None → no exception
        trend = build_governance_quality_trend(
            current=_make_metrics(), previous=None,
        )
        assert trend.has_previous is False

    def test_missing_metric_fields_non_throwing(self):
        prev = {"total_signals": 5}  # missing coverage fields
        trend = build_governance_quality_trend(
            current=_make_metrics(), previous=prev,
        )
        assert trend.has_previous is True

    def test_negative_deltas_preserved(self):
        trend = build_governance_quality_trend(
            current=_make_metrics(total=5),
            previous=_make_dict_metrics(total=10),
        )
        assert trend.total_signals_delta == -5

    def test_positive_deltas_preserved(self):
        trend = build_governance_quality_trend(
            current=_make_metrics(total=15),
            previous=_make_dict_metrics(total=10),
        )
        assert trend.total_signals_delta == 5

    def test_zero_deltas_preserved(self):
        trend = build_governance_quality_trend(
            current=_make_metrics(total=10),
            previous=_make_dict_metrics(total=10),
        )
        assert trend.total_signals_delta == 0

    def test_supports_nested_governance_quality_metrics_dict(self):
        nested_prev = {"metrics": _make_dict_metrics(total=8)}
        trend = build_governance_quality_trend(
            current=_make_metrics(total=12),
            previous=nested_prev,
        )
        assert trend.has_previous is True
        assert trend.total_signals_delta == 4

    def test_diagnostic_count_uses_diagnostics_list_length(self):
        diags = [{"code": "GQM-001"}, {"code": "GQM-002"}, {"code": "GQM-003"}]
        trend = build_governance_quality_trend(
            current=_make_metrics(diagnostics=diags),
            previous=_make_dict_metrics(diagnostics=[]),
        )
        assert trend.diagnostic_count_delta == 3


# ══════════════════════════════════════════════════════════════════
# Test: Serialization
# ══════════════════════════════════════════════════════════════════

class TestSerialization:
    def test_trend_to_dict_includes_all_fields(self):
        trend = build_governance_quality_trend(
            current=_make_metrics(total=12),
            previous=_make_dict_metrics(total=10),
        )
        d = governance_quality_trend_to_dict(trend)
        expected_keys = {
            "schema_version", "has_previous", "total_signals_delta",
            "evidence_coverage_delta", "metadata_coverage_delta",
            "finding_evidence_coverage_delta", "advisory_basis_coverage_delta",
            "diagnostic_count_delta", "notes",
        }
        assert set(d.keys()) == expected_keys

    def test_trend_to_dict_preserves_values(self):
        trend = build_governance_quality_trend(
            current=_make_metrics(total=15),
            previous=_make_dict_metrics(total=10),
        )
        d = governance_quality_trend_to_dict(trend)
        assert d["total_signals_delta"] == 5
        assert d["has_previous"] is True

    def test_trend_to_dict_preserves_notes(self):
        trend = build_governance_quality_trend(
            current=_make_metrics(), previous=None,
        )
        d = governance_quality_trend_to_dict(trend)
        assert isinstance(d["notes"], list)
        assert len(d["notes"]) >= 1


# ══════════════════════════════════════════════════════════════════
# Test: Run history
# ══════════════════════════════════════════════════════════════════

class TestRunHistory:
    def test_snapshot_includes_governance_quality_trend(self, tmp_path):
        from pharabius.core.run_history import build_current_run_snapshot
        # Create minimal workspace structure
        ws = tmp_path / ".ai-debt"
        ws.mkdir()
        (ws / "debt-register.json").write_text('{"findings": []}', encoding="utf-8")
        (ws / "evidence.json").write_text('{"evidence": []}', encoding="utf-8")
        snapshot = build_current_run_snapshot(ws, "RUN-001")
        assert "governance_quality_trend" in snapshot

    def test_old_snapshot_without_governance_quality_produces_no_previous(self, tmp_path):
        from pharabius.core.run_history import (
            build_current_run_snapshot,
            write_run_history_snapshot,
        )
        ws = tmp_path / ".ai-debt"
        ws.mkdir()
        (ws / "debt-register.json").write_text('{"findings": []}', encoding="utf-8")
        (ws / "evidence.json").write_text('{"evidence": []}', encoding="utf-8")

        # Write an old snapshot without governance_quality
        old = {"run_id": "RUN-000", "some_field": "value"}
        write_run_history_snapshot(ws, old)

        snapshot = build_current_run_snapshot(ws, "RUN-001")
        trend = snapshot.get("governance_quality_trend", {})
        assert trend.get("has_previous") is False

    def test_run_history_remains_backward_compatible(self, tmp_path):
        from pharabius.core.run_history import build_current_run_snapshot
        ws = tmp_path / ".ai-debt"
        ws.mkdir()
        (ws / "debt-register.json").write_text('{"findings": []}', encoding="utf-8")
        (ws / "evidence.json").write_text('{"evidence": []}', encoding="utf-8")
        snapshot = build_current_run_snapshot(ws, "RUN-001")
        # All existing fields should still be present
        assert "run_id" in snapshot
        assert "governance_quality" in snapshot
        assert "signal_summary" in snapshot


# ══════════════════════════════════════════════════════════════════
# Test: No behavior change
# ══════════════════════════════════════════════════════════════════

class TestNoBehaviorChange:
    def test_signals_are_not_mutated(self):
        metrics = _make_metrics()
        build_governance_quality_trend(current=metrics, previous=None)
        # Metrics unchanged — frozen dataclass
        assert metrics.total_signals == 10

    def test_diagnostics_not_promoted_or_demoted(self):
        diags = [{"code": "GQM-001"}]
        metrics = _make_metrics(diagnostics=diags)
        trend = build_governance_quality_trend(
            current=metrics, previous=_make_dict_metrics(),
        )
        # Trend only records count delta, never changes diagnostics
        assert trend.diagnostic_count_delta == 1
        assert metrics.diagnostics == diags
