"""v3.25.0 — Governance export & machine-readable reporting tests.

Proves exports are inert: no policy behavior, no mutation,
descriptive wording only, stable schema.
"""

from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.governance_export import (
    EXPORT_TYPE,
    SCHEMA_VERSION,
    _validate_no_forbidden_fields,
    build_governance_export,
    write_governance_export,
    write_governance_export_jsonl,
)
from pharabius.core.signals.models import GovernedSignal, SignalDisposition, SignalFamily
from pharabius.core.signals.quality import (
    build_governance_quality_metrics,
)
from pharabius.core.signals.trends import (
    build_governance_trend_summary,
)


def _sig(
    disposition: SignalDisposition = SignalDisposition.FINDING,
    family: SignalFamily = SignalFamily.RUNTIME,
    evidence_ids: list[str] | None = None,
) -> GovernedSignal:
    return GovernedSignal(
        signal_id="test-sig",
        family=family,
        kind="test",
        disposition=disposition,
        category="TD-TEST",
        severity="Medium",
        confidence="High",
        evidence_ids=evidence_ids if evidence_ids is not None else ["ev1"],
        source_signal_ids=[],
        title="Test",
        summary="Test",
        explanation="Test",
        metadata={"spec_kind": "test"},
    )


def _gq_metrics(signals=None):
    return build_governance_quality_metrics(signals or [_sig()])


# ═══════════════════════════════════════════════════════════════════════
# S01 — Schema structure
# ═══════════════════════════════════════════════════════════════════════


class TestSchemaStructure:
    """Export has stable, well-formed schema."""

    def test_schema_version_present(self) -> None:
        export = build_governance_export()
        assert export["schema_version"] == SCHEMA_VERSION

    def test_export_type_present(self) -> None:
        export = build_governance_export()
        assert export["export_type"] == EXPORT_TYPE

    def test_run_id_present(self) -> None:
        export = build_governance_export(run_id="RUN-001")
        assert export["run_id"] == "RUN-001"

    def test_generated_at_present(self) -> None:
        export = build_governance_export()
        assert export["generated_at"] is not None
        assert "T" in export["generated_at"]  # ISO 8601

    def test_metadata_present(self) -> None:
        export = build_governance_export()
        assert export["metadata"]["families_governed"] == 10
        assert export["metadata"]["source"] == "run_history"

    def test_signal_summary_null_when_not_provided(self) -> None:
        export = build_governance_export()
        assert export["signal_summary"] is None

    def test_governance_quality_null_when_not_provided(self) -> None:
        export = build_governance_export()
        assert export["governance_quality"] is None

    def test_governance_trends_null_when_not_provided(self) -> None:
        export = build_governance_export()
        assert export["governance_trends"] is None

    def test_diagnostics_empty_when_no_quality(self) -> None:
        export = build_governance_export()
        assert export["diagnostics"] == []


# ═══════════════════════════════════════════════════════════════════════
# S02 — Export with governance data
# ═══════════════════════════════════════════════════════════════════════


class TestExportWithData:
    """Export includes governance data when provided."""

    def test_signal_summary_included(self) -> None:
        summary = {"total": 10, "by_family": {"runtime": 5}}
        export = build_governance_export(signal_summary=summary)
        assert export["signal_summary"]["total"] == 10

    def test_governance_quality_included(self) -> None:
        metrics = _gq_metrics()
        export = build_governance_export(governance_quality=metrics)
        assert export["governance_quality"]["total_signals"] == 1

    def test_governance_trends_included(self) -> None:
        trend = build_governance_trend_summary(
            [
                {"run_id": "R1", "governance_quality": {"total_signals": 10}},
                {"run_id": "R2", "governance_quality": {"total_signals": 15}},
            ]
        )
        export = build_governance_export(governance_trends=trend)
        assert export["governance_trends"]["runs_compared"] == 2

    def test_diagnostics_included(self) -> None:
        metrics = build_governance_quality_metrics(
            [
                _sig(evidence_ids=[]),  # triggers GQM-001
            ]
        )
        export = build_governance_export(governance_quality=metrics)
        assert len(export["diagnostics"]) > 0
        assert any(d["code"] == "GQM-001" for d in export["diagnostics"])

    def test_recurring_diagnostics_included(self) -> None:
        trend = build_governance_trend_summary(
            [
                {
                    "run_id": "R1",
                    "governance_quality": {
                        "diagnostics": [
                            {"code": "GQM-003", "severity": "info", "family": "runtime"},
                        ]
                    },
                },
                {
                    "run_id": "R2",
                    "governance_quality": {
                        "diagnostics": [
                            {"code": "GQM-003", "severity": "info", "family": "runtime"},
                        ]
                    },
                },
            ]
        )
        export = build_governance_export(governance_trends=trend)
        assert len(export["recurring_diagnostics"]) == 1


# ═══════════════════════════════════════════════════════════════════════
# S03 — Trend unavailable handling
# ═══════════════════════════════════════════════════════════════════════


class TestTrendUnavailable:
    """Governance trends handle unavailability gracefully."""

    def test_trends_unavailable_reason(self) -> None:
        trend = build_governance_trend_summary([])
        export = build_governance_export(governance_trends=trend)
        assert export["governance_trends"]["unavailable_reason"] is not None

    def test_no_trends_still_valid_export(self) -> None:
        export = build_governance_export()
        assert export["schema_version"] == SCHEMA_VERSION
        assert export["governance_trends"] is None


# ═══════════════════════════════════════════════════════════════════════
# S04 — Diagnostics export
# ═══════════════════════════════════════════════════════════════════════


class TestDiagnosticsExport:
    """Diagnostics export correctly without changing semantics."""

    def test_diagnostic_fields(self) -> None:
        metrics = build_governance_quality_metrics(
            [
                _sig(evidence_ids=[]),
            ]
        )
        export = build_governance_export(governance_quality=metrics)
        for d in export["diagnostics"]:
            assert "code" in d
            assert "severity" in d
            assert "message" in d

    def test_diagnostics_not_findings(self) -> None:
        """Diagnostics are not findings or advisories."""
        metrics = build_governance_quality_metrics(
            [
                _sig(evidence_ids=[]),
            ]
        )
        export = build_governance_export(governance_quality=metrics)
        for d in export["diagnostics"]:
            assert "disposition" not in d
            assert "risk_score" not in d

    def test_recurring_diagnostic_occurrences(self) -> None:
        """Recurring diagnostics count runs, not instances."""
        trend = build_governance_trend_summary(
            [
                {
                    "run_id": "R1",
                    "governance_quality": {
                        "diagnostics": [
                            {"code": "GQM-003", "severity": "info", "family": "runtime"},
                            {
                                "code": "GQM-003",
                                "severity": "info",
                                "family": "runtime",
                            },  # dup in same run
                        ]
                    },
                },
                {
                    "run_id": "R2",
                    "governance_quality": {
                        "diagnostics": [
                            {"code": "GQM-003", "severity": "info", "family": "runtime"},
                        ]
                    },
                },
            ]
        )
        export = build_governance_export(governance_trends=trend)
        rd = export["recurring_diagnostics"]
        assert len(rd) == 1
        assert rd[0]["occurrences"] == 2  # 2 runs, not 3


# ═══════════════════════════════════════════════════════════════════════
# S05 — Schema/versioning tests
# ═══════════════════════════════════════════════════════════════════════


class TestSchemaVersioning:
    """Export shape is stable and additive."""

    def test_required_keys_exist(self) -> None:
        export = build_governance_export()
        required = [
            "schema_version",
            "export_type",
            "run_id",
            "generated_at",
            "signal_summary",
            "governance_quality",
            "governance_trends",
            "diagnostics",
            "recurring_diagnostics",
            "metadata",
        ]
        for key in required:
            assert key in export, f"Missing required key: {key}"

    def test_value_types_stable(self) -> None:
        metrics = _gq_metrics()
        trend = build_governance_trend_summary(
            [
                {"run_id": "R1", "governance_quality": {"total_signals": 10}},
                {"run_id": "R2", "governance_quality": {"total_signals": 15}},
            ]
        )
        export = build_governance_export(
            signal_summary={"total": 10},
            governance_quality=metrics,
            governance_trends=trend,
            run_id="R2",
        )
        assert isinstance(export["schema_version"], str)
        assert isinstance(export["export_type"], str)
        assert isinstance(export["run_id"], str)
        assert isinstance(export["generated_at"], str)
        assert isinstance(export["signal_summary"], dict)
        assert isinstance(export["governance_quality"], dict)
        assert isinstance(export["governance_trends"], dict)
        assert isinstance(export["diagnostics"], list)
        assert isinstance(export["recurring_diagnostics"], list)
        assert isinstance(export["metadata"], dict)

    def test_no_forbidden_policy_labels(self) -> None:
        """No health/pass/fail/compliance judgment labels."""
        metrics = _gq_metrics()
        export = build_governance_export(governance_quality=metrics)
        export_json = json.dumps(export).lower()
        forbidden = [
            "healthy",
            "unhealthy",
            "compliant",
            "noncompliant",
            '"pass"',
            '"fail"',
            '"score"',
            '"grade"',
        ]
        for term in forbidden:
            assert term not in export_json, f"Forbidden term in export: {term}"

    def test_schema_is_additive(self) -> None:
        """New fields can be added without breaking consumers."""
        export = build_governance_export()
        # Adding a new field should not break
        export["future_field"] = "future_value"
        assert "future_field" in export


# ═══════════════════════════════════════════════════════════════════════
# S06 — No-policy regression
# ═══════════════════════════════════════════════════════════════════════


class TestNoPolicyRegression:
    """Exports do not alter findings, signals, runs, or work packages."""

    def test_export_does_not_mutate_metrics(self) -> None:
        metrics = _gq_metrics()
        original_total = metrics.total_signals
        build_governance_export(governance_quality=metrics)
        assert metrics.total_signals == original_total

    def test_export_does_not_mutate_trends(self) -> None:
        trend = build_governance_trend_summary(
            [
                {"run_id": "R1", "governance_quality": {"total_signals": 10}},
                {"run_id": "R2", "governance_quality": {"total_signals": 15}},
            ]
        )
        original_runs = trend.runs_compared
        build_governance_export(governance_trends=trend)
        assert trend.runs_compared == original_runs

    def test_export_does_not_create_findings(self) -> None:
        export = build_governance_export()
        assert not hasattr(export, "findings")
        assert "findings" not in export

    def test_export_does_not_create_work_packages(self) -> None:
        export = build_governance_export()
        assert "work_packages" not in export

    def test_export_does_not_affect_signal_disposition(self) -> None:
        sig = _sig()
        original_disp = sig.disposition
        metrics = build_governance_quality_metrics([sig])
        build_governance_export(governance_quality=metrics)
        assert sig.disposition == original_disp

    def test_export_does_not_change_risk_scores(self) -> None:
        sig = _sig()
        original_sev = sig.severity
        metrics = build_governance_quality_metrics([sig])
        build_governance_export(governance_quality=metrics)
        assert sig.severity == original_sev


# ═══════════════════════════════════════════════════════════════════════
# S07 — File write tests
# ═══════════════════════════════════════════════════════════════════════


class TestFileWrites:
    """Export files are written correctly."""

    def test_json_export(self, tmp_path: Path) -> None:
        export = build_governance_export(run_id="RUN-001")
        path = write_governance_export(export, tmp_path / "governance-summary.json")
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_version"] == SCHEMA_VERSION
        assert data["run_id"] == "RUN-001"

    def test_jsonl_export(self, tmp_path: Path) -> None:
        export = build_governance_export(run_id="RUN-001")
        path = write_governance_export_jsonl(export, tmp_path / "governance-summary.jsonl")
        assert path.exists()
        content = path.read_text(encoding="utf-8").strip()
        data = json.loads(content)
        assert data["schema_version"] == SCHEMA_VERSION

    def test_json_creates_parent_dirs(self, tmp_path: Path) -> None:
        export = build_governance_export()
        path = write_governance_export(export, tmp_path / "deep" / "dir" / "gov.json")
        assert path.exists()

    def test_jsonl_is_single_line(self, tmp_path: Path) -> None:
        export = build_governance_export()
        path = write_governance_export_jsonl(export, tmp_path / "gov.jsonl")
        content = path.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        assert len(lines) == 1

    def test_export_import_roundtrip(self, tmp_path: Path) -> None:
        """Write and read back — no data loss."""
        metrics = _gq_metrics()
        trend = build_governance_trend_summary(
            [
                {"run_id": "R1", "governance_quality": {"total_signals": 10}},
                {"run_id": "R2", "governance_quality": {"total_signals": 15}},
            ]
        )
        export = build_governance_export(
            signal_summary={"total": 10},
            governance_quality=metrics,
            governance_trends=trend,
            run_id="R2",
        )
        path = write_governance_export(export, tmp_path / "gov.json")
        reloaded = json.loads(path.read_text(encoding="utf-8"))

        assert reloaded["schema_version"] == export["schema_version"]
        assert reloaded["run_id"] == export["run_id"]
        assert reloaded["signal_summary"] == export["signal_summary"]
        assert reloaded["governance_quality"]["total_signals"] == 1
        assert reloaded["governance_trends"]["runs_compared"] == 2
        assert reloaded["metadata"]["families_governed"] == 10


# ═══════════════════════════════════════════════════════════════════════
# Forbidden field validation
# ═══════════════════════════════════════════════════════════════════════


class TestForbiddenFieldValidation:
    """Forbidden policy/gate field detection."""

    def test_clean_export_no_warnings(self) -> None:
        export = build_governance_export()
        warnings = _validate_no_forbidden_fields(export)
        assert len(warnings) == 0

    def test_forbidden_field_detected(self) -> None:
        data = {"pass": True, "valid_field": "ok"}
        warnings = _validate_no_forbidden_fields(data)
        assert len(warnings) == 1
        assert "pass" in warnings[0]
