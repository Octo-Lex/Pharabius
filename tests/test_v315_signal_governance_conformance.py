"""v3.15.0 — Signal Governance Hardening & Invariant Enforcement.

Invariant registry, validation, output behavior, conformance suite,
analyzer boundary tests, summary consistency, and diagnostics.
"""

from __future__ import annotations

import pytest

from pharabius.core.signals.models import (
    GovernedSignal,
    SignalDisposition,
    SignalFamily,
    make_signal_id,
)
from pharabius.core.signals.policy import (
    output_behavior,
    should_create_advisory,
    should_create_finding,
    should_create_work_package,
    is_informational,
    is_reportable,
    SignalOutputBehavior,
)
from pharabius.core.signals.invariants import (
    ALL_INVARIANTS,
    SignalInvariant,
    SignalValidationSeverity,
    INV_001_FINDING_ONLY_CREATES_FINDING,
    INV_002_ADVISORY_NEVER_CREATES_WORK_PACKAGE,
    INV_003_INFORMATIONAL_NON_ACTIONABLE,
    INV_004_SUPPRESSED_DIAGNOSTIC_ONLY,
    INV_005_SIGNAL_ID_DETERMINISTIC,
    INV_006_PROMOTED_FINDING_HAS_EVIDENCE,
    INV_007_MIGRATED_ANALYZER_USES_POLICY,
    INV_008_SUMMARY_COUNTS_GOVERNED_SIGNALS,
)
from pharabius.core.signals.validation import (
    validate_governed_signal,
    diagnose_signal,
    SignalValidationResult,
    SignalValidationViolation,
    SignalDiagnostic,
)
from pharabius.core.signals.summary import build_signal_summary


# ── Helpers ────────────────────────────────────────────────────────────


def _signal(
    disposition: SignalDisposition,
    kind: str = "test_kind",
    evidence_ids: list[str] | None = None,
    family: SignalFamily = SignalFamily.RUNTIME,
) -> GovernedSignal:
    return GovernedSignal(
        signal_id=make_signal_id(family.value, kind, evidence_ids or ["ev1"]),
        family=family,
        kind=kind,
        disposition=disposition,
        category="TD-DEP",
        severity="Medium",
        confidence="High",
        evidence_ids=evidence_ids or ["ev1"],
        source_signal_ids=[],
        title=f"Test signal: {disposition.value}",
        summary=f"Summary for {disposition.value}",
        explanation=f"Explanation for {disposition.value}",
        metadata={},
    )


# ── S01: Invariant registry ──────────────────────────────────────────


class TestInvariantRegistry:
    """INV_001 through INV_008 exist and are well-formed."""

    def test_all_eight_invariants_exist(self) -> None:
        assert len(ALL_INVARIANTS) == 8

    def test_invariant_codes_unique(self) -> None:
        codes = [inv.code for inv in ALL_INVARIANTS]
        assert len(codes) == len(set(codes))

    def test_invariant_codes_sequential(self) -> None:
        codes = sorted(inv.code for inv in ALL_INVARIANTS)
        expected = [f"INV_{i:03d}" for i in range(1, 9)]
        assert codes == expected

    def test_invariant_fields_non_empty(self) -> None:
        for inv in ALL_INVARIANTS:
            assert inv.code, f"{inv.code} has empty code"
            assert inv.title, f"{inv.code} has empty title"
            assert inv.description, f"{inv.code} has empty description"

    def test_invariant_severity_valid(self) -> None:
        valid = {SignalValidationSeverity.CRITICAL, SignalValidationSeverity.WARNING, SignalValidationSeverity.INFO}
        for inv in ALL_INVARIANTS:
            assert inv.severity in valid, f"{inv.code} has invalid severity: {inv.severity}"

    def test_severity_enum_values(self) -> None:
        assert SignalValidationSeverity.CRITICAL == "critical"
        assert SignalValidationSeverity.WARNING == "warning"
        assert SignalValidationSeverity.INFO == "info"

    def test_invariants_are_frozen(self) -> None:
        inv = INV_001_FINDING_ONLY_CREATES_FINDING
        with pytest.raises(AttributeError):
            inv.code = "CHANGED"  # type: ignore


# ── S02: Signal validation ────────────────────────────────────────────


class TestSignalValidation:
    """validate_governed_signal checks completeness and traceability."""

    def test_valid_signal_passes(self) -> None:
        sig = _signal(SignalDisposition.FINDING)
        result = validate_governed_signal(sig)
        assert result.valid
        assert result.violations == []

    def test_empty_signal_id_violation(self) -> None:
        sig = GovernedSignal(
            signal_id="", family=SignalFamily.RUNTIME, kind="k",
            disposition=SignalDisposition.FINDING, category="TD-DEP",
            severity="Medium", confidence="High", evidence_ids=["ev1"],
            source_signal_ids=[], title="t", summary="s", explanation="e",
            metadata={},
        )
        result = validate_governed_signal(sig)
        assert not result.valid
        assert any("INV_005" in v.invariant_code for v in result.violations)

    def test_malformed_signal_id(self) -> None:
        sig = GovernedSignal(
            signal_id="NOT-A-SIGNAL-ID", family=SignalFamily.RUNTIME, kind="k",
            disposition=SignalDisposition.FINDING, category="TD-DEP",
            severity="Medium", confidence="High", evidence_ids=["ev1"],
            source_signal_ids=[], title="t", summary="s", explanation="e",
            metadata={},
        )
        result = validate_governed_signal(sig)
        assert any("INV_005" in v.invariant_code for v in result.violations)

    def test_empty_kind_violation(self) -> None:
        sig = GovernedSignal(
            signal_id="SIG-RUNTIME-abc123def456", family=SignalFamily.RUNTIME,
            kind="", disposition=SignalDisposition.FINDING, category="TD-DEP",
            severity="Medium", confidence="High", evidence_ids=["ev1"],
            source_signal_ids=[], title="t", summary="s", explanation="e",
            metadata={},
        )
        result = validate_governed_signal(sig)
        assert any("SIG-KIND" in v.invariant_code for v in result.violations)

    def test_empty_category_warning(self) -> None:
        sig = GovernedSignal(
            signal_id="SIG-RUNTIME-abc123def456", family=SignalFamily.RUNTIME,
            kind="k", disposition=SignalDisposition.FINDING, category="",
            severity="Medium", confidence="High", evidence_ids=["ev1"],
            source_signal_ids=[], title="t", summary="s", explanation="e",
            metadata={},
        )
        result = validate_governed_signal(sig)
        assert any("SIG-CATEGORY" in v.invariant_code for v in result.violations)

    def test_empty_title_violation(self) -> None:
        sig = GovernedSignal(
            signal_id="SIG-RUNTIME-abc123def456", family=SignalFamily.RUNTIME,
            kind="k", disposition=SignalDisposition.FINDING, category="TD-DEP",
            severity="Medium", confidence="High", evidence_ids=["ev1"],
            source_signal_ids=[], title="", summary="s", explanation="e",
            metadata={},
        )
        result = validate_governed_signal(sig)
        assert not result.valid
        assert any("SIG-TITLE" in v.invariant_code for v in result.violations)

    def test_finding_without_evidence_violates_inv006(self) -> None:
        sig = GovernedSignal(
            signal_id="SIG-RUNTIME-abc123def456", family=SignalFamily.RUNTIME,
            kind="k", disposition=SignalDisposition.FINDING, category="TD-DEP",
            severity="Medium", confidence="High", evidence_ids=[],
            source_signal_ids=[], title="t", summary="s", explanation="e",
            metadata={},
        )
        result = validate_governed_signal(sig)
        assert not result.valid
        assert any(v.invariant_code == "INV_006" for v in result.violations)

    def test_advisory_without_evidence_or_metadata_warning(self) -> None:
        sig = GovernedSignal(
            signal_id="SIG-RUNTIME-abc123def456", family=SignalFamily.RUNTIME,
            kind="k", disposition=SignalDisposition.ADVISORY, category="TD-DEP",
            severity="Low", confidence="Low", evidence_ids=[],
            source_signal_ids=[], title="t", summary="s", explanation="e",
            metadata={},
        )
        result = validate_governed_signal(sig)
        assert any("SIG-ADVISORY-EVIDENCE" in v.invariant_code for v in result.violations)

    def test_violations_include_invariant_codes(self) -> None:
        """AC18: Violations include invariant codes."""
        sig = GovernedSignal(
            signal_id="", family=SignalFamily.RUNTIME, kind="",
            disposition=SignalDisposition.FINDING, category="",
            severity="Medium", confidence="High", evidence_ids=[],
            source_signal_ids=[], title="", summary="s", explanation="e",
            metadata={},
        )
        result = validate_governed_signal(sig)
        for v in result.violations:
            assert v.invariant_code, "Violation missing invariant code"
            assert v.severity in {
                SignalValidationSeverity.CRITICAL,
                SignalValidationSeverity.WARNING,
                SignalValidationSeverity.INFO,
            }


# ── S03: Output behavior ──────────────────────────────────────────────


class TestOutputBehavior:
    """output_behavior maps dispositions to complete behavior."""

    def test_finding_behavior(self) -> None:
        sig = _signal(SignalDisposition.FINDING)
        behav = output_behavior(sig)
        assert behav.creates_finding is True
        assert behav.creates_work_package is True
        assert behav.appears_in_report_detail is True
        assert behav.appears_in_summary is True
        assert behav.diagnostics_only is False

    def test_advisory_behavior(self) -> None:
        sig = _signal(SignalDisposition.ADVISORY)
        behav = output_behavior(sig)
        assert behav.creates_advisory is True
        assert behav.creates_finding is False
        assert behav.creates_work_package is False
        assert behav.appears_in_report_detail is True
        assert behav.appears_in_summary is True

    def test_informational_behavior(self) -> None:
        sig = _signal(SignalDisposition.INFORMATIONAL)
        behav = output_behavior(sig)
        assert behav.creates_finding is False
        assert behav.creates_advisory is False
        assert behav.creates_work_package is False
        assert behav.appears_in_report_detail is False
        assert behav.appears_in_summary is True
        assert behav.diagnostics_only is False

    def test_suppressed_behavior(self) -> None:
        sig = _signal(SignalDisposition.SUPPRESSED)
        behav = output_behavior(sig)
        assert behav.diagnostics_only is True
        assert behav.creates_finding is False
        assert behav.creates_advisory is False
        assert behav.creates_work_package is False
        assert behav.appears_in_report_detail is False
        assert behav.appears_in_summary is False

    def test_output_behavior_consistent_with_predicates(self) -> None:
        for disp in SignalDisposition:
            sig = _signal(disp)
            behav = output_behavior(sig)
            assert behav.creates_finding == should_create_finding(sig)
            assert behav.creates_advisory == should_create_advisory(sig)
            assert behav.creates_work_package == should_create_work_package(sig)

    def test_output_behavior_frozen(self) -> None:
        sig = _signal(SignalDisposition.FINDING)
        behav = output_behavior(sig)
        with pytest.raises(AttributeError):
            behav.creates_finding = False  # type: ignore

    def test_finding_is_reportable(self) -> None:
        sig = _signal(SignalDisposition.FINDING)
        assert is_reportable(sig) is True

    def test_suppressed_not_reportable(self) -> None:
        sig = _signal(SignalDisposition.SUPPRESSED)
        assert is_reportable(sig) is False


# ── S04: Migrated-family conformance ──────────────────────────────────


# Adapter fixtures for each family
_FAMILY_ADAPTER_FACTORIES = {
    "runtime": lambda: [
        _signal(SignalDisposition.FINDING, kind="runtime_conflict", family=SignalFamily.RUNTIME),
        _signal(SignalDisposition.ADVISORY, kind="runtime_missing_pin", family=SignalFamily.RUNTIME),
        _signal(SignalDisposition.INFORMATIONAL, kind="runtime_evidence", family=SignalFamily.RUNTIME),
    ],
    "documentation": lambda: [
        GovernedSignal(
            signal_id=make_signal_id("documentation", "missing_documentation", ["ev1"]),
            family=SignalFamily.DOCUMENTATION, kind="missing_documentation",
            disposition=SignalDisposition.ADVISORY, category="TD-DOC",
            severity="Low", confidence="Low", evidence_ids=["ev1"],
            source_signal_ids=[], title="Missing docs", summary="No docs",
            explanation="Missing docs", metadata={"missing_docs": True},
        ),
    ],
    "build": lambda: [
        GovernedSignal(
            signal_id=make_signal_id("build", "missing_ci_cd", ["ev1"]),
            family=SignalFamily.BUILD, kind="missing_ci_cd",
            disposition=SignalDisposition.ADVISORY, category="TD-BUILD",
            severity="Low", confidence="Low", evidence_ids=["ev1"],
            source_signal_ids=[], title="Missing CI", summary="No CI",
            explanation="Missing CI", metadata={"missing_ci": True},
        ),
    ],
    "process": lambda: [
        GovernedSignal(
            signal_id=make_signal_id("process", "missing_process_artifacts", ["ev1"]),
            family=SignalFamily.PROCESS, kind="missing_process_artifacts",
            disposition=SignalDisposition.ADVISORY, category="TD-PROCESS",
            severity="Low", confidence="Low", evidence_ids=["ev1"],
            source_signal_ids=[], title="Missing process", summary="No artifacts",
            explanation="Missing artifacts", metadata={"missing_artifacts": ["CODEOWNERS"]},
        ),
    ],
    "test": lambda: [
        GovernedSignal(
            signal_id=make_signal_id("test", "missing_tests", ["ev1"]),
            family=SignalFamily.TEST, kind="missing_tests",
            disposition=SignalDisposition.FINDING, category="TD-TEST",
            severity="Medium", confidence="Medium", evidence_ids=["ev1"],
            source_signal_ids=[], title="No tests", summary="No test evidence",
            explanation="Missing tests", metadata={},
        ),
    ],
}


class TestFamilyConformance:
    """All migrated families pass the same governance contract."""

    @pytest.mark.parametrize("family_name", list(_FAMILY_ADAPTER_FACTORIES.keys()))
    def test_adapters_produce_valid_signals(self, family_name: str) -> None:
        signals = _FAMILY_ADAPTER_FACTORIES[family_name]()
        for sig in signals:
            result = validate_governed_signal(sig)
            assert result.valid, f"{family_name}: {sig.kind} validation failed: {result.violations}"

    @pytest.mark.parametrize("family_name", list(_FAMILY_ADAPTER_FACTORIES.keys()))
    def test_signal_ids_are_deterministic(self, family_name: str) -> None:
        signals = _FAMILY_ADAPTER_FACTORIES[family_name]()
        for sig in signals:
            sig2 = _rebuild_signal(sig)
            assert sig.signal_id == sig2.signal_id, f"{family_name}: non-deterministic ID"

    @pytest.mark.parametrize("family_name", list(_FAMILY_ADAPTER_FACTORIES.keys()))
    def test_family_enum_correct(self, family_name: str) -> None:
        signals = _FAMILY_ADAPTER_FACTORIES[family_name]()
        for sig in signals:
            assert sig.family.value == family_name

    @pytest.mark.parametrize("family_name", list(_FAMILY_ADAPTER_FACTORIES.keys()))
    def test_disposition_valid(self, family_name: str) -> None:
        signals = _FAMILY_ADAPTER_FACTORIES[family_name]()
        for sig in signals:
            assert sig.disposition in list(SignalDisposition)

    @pytest.mark.parametrize("family_name", list(_FAMILY_ADAPTER_FACTORIES.keys()))
    def test_severity_standard(self, family_name: str) -> None:
        signals = _FAMILY_ADAPTER_FACTORIES[family_name]()
        for sig in signals:
            assert sig.severity in {"Low", "Medium", "High"}, f"{family_name}: {sig.severity}"

    @pytest.mark.parametrize("family_name", list(_FAMILY_ADAPTER_FACTORIES.keys()))
    def test_confidence_standard(self, family_name: str) -> None:
        signals = _FAMILY_ADAPTER_FACTORIES[family_name]()
        for sig in signals:
            assert sig.confidence in {"Low", "Medium", "High"}, f"{family_name}: {sig.confidence}"

    @pytest.mark.parametrize("family_name", list(_FAMILY_ADAPTER_FACTORIES.keys()))
    def test_output_behavior_consistent(self, family_name: str) -> None:
        signals = _FAMILY_ADAPTER_FACTORIES[family_name]()
        for sig in signals:
            behav = output_behavior(sig)
            assert behav.creates_finding == should_create_finding(sig)
            assert behav.creates_work_package == should_create_work_package(sig)

    @pytest.mark.parametrize("family_name", list(_FAMILY_ADAPTER_FACTORIES.keys()))
    def test_metadata_is_dict(self, family_name: str) -> None:
        signals = _FAMILY_ADAPTER_FACTORIES[family_name]()
        for sig in signals:
            assert isinstance(sig.metadata, dict), f"{family_name}: metadata not dict"


def _rebuild_signal(sig: GovernedSignal) -> GovernedSignal:
    """Rebuild a signal with same inputs to verify determinism."""
    return GovernedSignal(
        signal_id=make_signal_id(sig.family.value, sig.kind, sig.evidence_ids),
        family=sig.family, kind=sig.kind, disposition=sig.disposition,
        category=sig.category, severity=sig.severity, confidence=sig.confidence,
        evidence_ids=sig.evidence_ids, source_signal_ids=sig.source_signal_ids,
        title=sig.title, summary=sig.summary, explanation=sig.explanation,
        metadata=sig.metadata,
    )


# ── S05: Static analyzer boundary tests ───────────────────────────────


class TestAnalyzerBoundaries:
    """Migrated analyzers use signal policy helpers, not bypasses."""

    def test_runtime_version_signals_uses_policy(self) -> None:
        import inspect
        from pharabius.core import analyzer
        source = inspect.getsource(analyzer._analyze_runtime_version_signals)
        assert "should_create_finding" in source or "should_create_advisory" in source

    def test_missing_docs_uses_policy(self) -> None:
        import inspect
        from pharabius.core import analyzer
        source = inspect.getsource(analyzer._analyze_missing_docs)
        assert "should_create_advisory" in source

    def test_missing_ci_uses_policy(self) -> None:
        import inspect
        from pharabius.core import analyzer
        source = inspect.getsource(analyzer._analyze_missing_ci)
        assert "should_create_advisory" in source

    def test_missing_process_uses_policy(self) -> None:
        import inspect
        from pharabius.core import analyzer
        source = inspect.getsource(analyzer._analyze_missing_process_artifacts)
        assert "should_create_advisory" in source

    def test_missing_tests_uses_policy(self) -> None:
        import inspect
        from pharabius.core import analyzer
        source = inspect.getsource(analyzer._analyze_missing_tests)
        assert "should_create_finding" in source

    def test_risk_sensitive_uses_policy(self) -> None:
        import inspect
        from pharabius.core import analyzer
        source = inspect.getsource(analyzer._analyze_risk_sensitive_without_tests)
        assert "should_create_finding" in source

    def test_coverage_gaps_uses_policy(self) -> None:
        import inspect
        from pharabius.core import analyzer
        source = inspect.getsource(analyzer._analyze_coverage_gaps)
        assert "should_create_finding" in source

    def test_no_analyzer_uses_work_package_as_proxy(self) -> None:
        """AC14/INV_007: No migrated analyzer uses should_create_work_package()."""
        import inspect
        from pharabius.core import analyzer
        targets = [
            analyzer._analyze_missing_docs,
            analyzer._analyze_missing_ci,
            analyzer._analyze_missing_process_artifacts,
        ]
        for func in targets:
            source = inspect.getsource(func)
            assert "should_create_work_package" not in source, \
                f"{func.__name__} uses should_create_work_package as proxy"


# ── S06: Summary consistency ──────────────────────────────────────────


class TestSummaryConsistency:
    """Signal summaries are consistent with governed signals."""

    def test_summary_counts_match_manual(self) -> None:
        signals = [
            _signal(SignalDisposition.FINDING, "f1"),
            _signal(SignalDisposition.ADVISORY, "a1"),
            _signal(SignalDisposition.INFORMATIONAL, "i1"),
        ]
        summary = build_signal_summary(signals)
        assert summary.total == 3
        assert summary.by_disposition == {"finding": 1, "advisory": 1, "informational": 1}

    def test_mixed_families_correct_counts(self) -> None:
        signals = [
            _signal(SignalDisposition.FINDING, family=SignalFamily.RUNTIME),
            _signal(SignalDisposition.FINDING, family=SignalFamily.TEST),
            _signal(SignalDisposition.ADVISORY, family=SignalFamily.DOCUMENTATION),
        ]
        summary = build_signal_summary(signals)
        assert summary.by_family == {"runtime": 1, "test": 1, "documentation": 1}

    def test_all_finding_disposition_count(self) -> None:
        signals = [
            _signal(SignalDisposition.FINDING, f"f{i}") for i in range(5)
        ]
        summary = build_signal_summary(signals)
        assert summary.by_disposition["finding"] == 5
        assert summary.total == 5

    def test_suppressed_excluded_from_normal_summary(self) -> None:
        """AC16: SUPPRESSED excluded from normal summary."""
        signals = [
            _signal(SignalDisposition.FINDING, "f1"),
            _signal(SignalDisposition.SUPPRESSED, "s1"),
        ]
        summary = build_signal_summary(signals)
        assert summary.total == 1
        assert "suppressed" not in summary.by_disposition

    def test_suppressed_included_in_diagnostics_summary(self) -> None:
        """AC16: SUPPRESSED included with include_diagnostics=True."""
        signals = [
            _signal(SignalDisposition.FINDING, "f1"),
            _signal(SignalDisposition.SUPPRESSED, "s1"),
        ]
        summary = build_signal_summary(signals, include_diagnostics=True)
        assert summary.total == 2
        assert "suppressed" in summary.by_disposition

    def test_empty_signals_summary(self) -> None:
        summary = build_signal_summary([])
        assert summary.total == 0
        assert summary.by_family == {}
        assert summary.by_disposition == {}

    def test_signal_summary_to_dict_roundtrip(self) -> None:
        from pharabius.core.signals.summary import signal_summary_to_dict
        signals = [_signal(SignalDisposition.FINDING, "f1")]
        summary = build_signal_summary(signals)
        d = signal_summary_to_dict(summary)
        assert d["total"] == 1
        assert "by_family" in d
        assert "by_disposition" in d


# ── S07: Diagnostics ──────────────────────────────────────────────────


class TestDiagnostics:
    """diagnose_signal returns structured diagnostics."""

    def test_valid_signal_no_diagnostics(self) -> None:
        sig = _signal(SignalDisposition.FINDING)
        diags = diagnose_signal(sig)
        assert diags == []

    def test_finding_no_evidence_inv006(self) -> None:
        sig = GovernedSignal(
            signal_id="SIG-RUNTIME-abc123def456", family=SignalFamily.RUNTIME,
            kind="k", disposition=SignalDisposition.FINDING, category="TD-DEP",
            severity="Medium", confidence="High", evidence_ids=[],
            source_signal_ids=[], title="t", summary="s", explanation="e",
            metadata={},
        )
        diags = diagnose_signal(sig)
        assert any(d.invariant_code == "INV_006" for d in diags)

    def test_diagnostics_return_frozen_dataclasses(self) -> None:
        sig = GovernedSignal(
            signal_id="", family=SignalFamily.RUNTIME, kind="",
            disposition=SignalDisposition.FINDING, category="",
            severity="Medium", confidence="High", evidence_ids=[],
            source_signal_ids=[], title="", summary="s", explanation="e",
            metadata={},
        )
        diags = diagnose_signal(sig)
        for d in diags:
            with pytest.raises(AttributeError):
                d.message = "changed"  # type: ignore

    def test_diagnostics_include_family_and_disposition(self) -> None:
        sig = GovernedSignal(
            signal_id="SIG-RUNTIME-abc123def456", family=SignalFamily.RUNTIME,
            kind="k", disposition=SignalDisposition.FINDING, category="TD-DEP",
            severity="Medium", confidence="High", evidence_ids=[],
            source_signal_ids=[], title="t", summary="s", explanation="e",
            metadata={},
        )
        diags = diagnose_signal(sig)
        for d in diags:
            assert d.family == "runtime"
            assert d.disposition == "finding"

    def test_no_category_inference_in_diagnostics(self) -> None:
        """AC19: Diagnostics do not infer finding eligibility from category alone."""
        # An ADVISORY with TD-SEC category should NOT produce INV_001 diagnostic
        sig = GovernedSignal(
            signal_id=make_signal_id("test", "risk_sensitive", ["ev1"]),
            family=SignalFamily.TEST, kind="risk_sensitive_without_tests",
            disposition=SignalDisposition.FINDING, category="TD-SEC",
            severity="High", confidence="Medium", evidence_ids=["ev1"],
            source_signal_ids=[], title="Risk sensitive", summary="No tests",
            explanation="Missing tests", metadata={"risk_sensitive": True},
        )
        diags = diagnose_signal(sig)
        inv001_diags = [d for d in diags if d.invariant_code == "INV_001"]
        assert inv001_diags == [], "INV_001 should not fire for legitimate FINDING with TD-SEC category"
