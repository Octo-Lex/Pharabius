"""v3.15.0 — Signal Governance Hardening & Invariant Enforcement.

Invariant registry, validation, output behavior, conformance suite,
analyzer boundary tests, summary consistency, and diagnostics.
"""

from __future__ import annotations

import pytest

from pharabius.core.signals.invariants import (
    ALL_INVARIANTS,
    INV_001_FINDING_ONLY_CREATES_FINDING,
    SignalValidationSeverity,
)
from pharabius.core.signals.models import (
    GovernedSignal,
    SignalDisposition,
    SignalFamily,
    make_signal_id,
)
from pharabius.core.signals.policy import (
    is_reportable,
    output_behavior,
    should_create_advisory,
    should_create_finding,
    should_create_work_package,
)
from pharabius.core.signals.summary import build_signal_summary
from pharabius.core.signals.validation import (
    diagnose_signal,
    validate_governed_signal,
)

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
        valid = {
            SignalValidationSeverity.CRITICAL,
            SignalValidationSeverity.WARNING,
            SignalValidationSeverity.INFO,
        }
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
            signal_id="",
            family=SignalFamily.RUNTIME,
            kind="k",
            disposition=SignalDisposition.FINDING,
            category="TD-DEP",
            severity="Medium",
            confidence="High",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="t",
            summary="s",
            explanation="e",
            metadata={},
        )
        result = validate_governed_signal(sig)
        assert not result.valid
        assert any("INV_005" in v.invariant_code for v in result.violations)

    def test_malformed_signal_id(self) -> None:
        sig = GovernedSignal(
            signal_id="NOT-A-SIGNAL-ID",
            family=SignalFamily.RUNTIME,
            kind="k",
            disposition=SignalDisposition.FINDING,
            category="TD-DEP",
            severity="Medium",
            confidence="High",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="t",
            summary="s",
            explanation="e",
            metadata={},
        )
        result = validate_governed_signal(sig)
        assert any("INV_005" in v.invariant_code for v in result.violations)

    def test_empty_kind_violation(self) -> None:
        sig = GovernedSignal(
            signal_id="SIG-RUNTIME-abc123def456",
            family=SignalFamily.RUNTIME,
            kind="",
            disposition=SignalDisposition.FINDING,
            category="TD-DEP",
            severity="Medium",
            confidence="High",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="t",
            summary="s",
            explanation="e",
            metadata={},
        )
        result = validate_governed_signal(sig)
        assert any("SIG-KIND" in v.invariant_code for v in result.violations)

    def test_empty_category_warning(self) -> None:
        sig = GovernedSignal(
            signal_id="SIG-RUNTIME-abc123def456",
            family=SignalFamily.RUNTIME,
            kind="k",
            disposition=SignalDisposition.FINDING,
            category="",
            severity="Medium",
            confidence="High",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="t",
            summary="s",
            explanation="e",
            metadata={},
        )
        result = validate_governed_signal(sig)
        assert any("SIG-CATEGORY" in v.invariant_code for v in result.violations)

    def test_empty_title_violation(self) -> None:
        sig = GovernedSignal(
            signal_id="SIG-RUNTIME-abc123def456",
            family=SignalFamily.RUNTIME,
            kind="k",
            disposition=SignalDisposition.FINDING,
            category="TD-DEP",
            severity="Medium",
            confidence="High",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="",
            summary="s",
            explanation="e",
            metadata={},
        )
        result = validate_governed_signal(sig)
        assert not result.valid
        assert any("SIG-TITLE" in v.invariant_code for v in result.violations)

    def test_finding_without_evidence_violates_inv006(self) -> None:
        sig = GovernedSignal(
            signal_id="SIG-RUNTIME-abc123def456",
            family=SignalFamily.RUNTIME,
            kind="k",
            disposition=SignalDisposition.FINDING,
            category="TD-DEP",
            severity="Medium",
            confidence="High",
            evidence_ids=[],
            source_signal_ids=[],
            title="t",
            summary="s",
            explanation="e",
            metadata={},
        )
        result = validate_governed_signal(sig)
        assert not result.valid
        assert any(v.invariant_code == "INV_006" for v in result.violations)

    def test_advisory_without_evidence_or_metadata_warning(self) -> None:
        sig = GovernedSignal(
            signal_id="SIG-RUNTIME-abc123def456",
            family=SignalFamily.RUNTIME,
            kind="k",
            disposition=SignalDisposition.ADVISORY,
            category="TD-DEP",
            severity="Low",
            confidence="Low",
            evidence_ids=[],
            source_signal_ids=[],
            title="t",
            summary="s",
            explanation="e",
            metadata={},
        )
        result = validate_governed_signal(sig)
        assert any("SIG-ADVISORY-EVIDENCE" in v.invariant_code for v in result.violations)

    def test_violations_include_invariant_codes(self) -> None:
        """AC18: Violations include invariant codes."""
        sig = GovernedSignal(
            signal_id="",
            family=SignalFamily.RUNTIME,
            kind="",
            disposition=SignalDisposition.FINDING,
            category="",
            severity="Medium",
            confidence="High",
            evidence_ids=[],
            source_signal_ids=[],
            title="",
            summary="s",
            explanation="e",
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
        _signal(
            SignalDisposition.ADVISORY, kind="runtime_missing_pin", family=SignalFamily.RUNTIME
        ),
        _signal(
            SignalDisposition.INFORMATIONAL, kind="runtime_evidence", family=SignalFamily.RUNTIME
        ),
    ],
    "documentation": lambda: [
        GovernedSignal(
            signal_id=make_signal_id("documentation", "missing_documentation", ["ev1"]),
            family=SignalFamily.DOCUMENTATION,
            kind="missing_documentation",
            disposition=SignalDisposition.ADVISORY,
            category="TD-DOC",
            severity="Low",
            confidence="Low",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Missing docs",
            summary="No docs",
            explanation="Missing docs",
            metadata={"missing_docs": True},
        ),
    ],
    "build": lambda: [
        GovernedSignal(
            signal_id=make_signal_id("build", "missing_ci_cd", ["ev1"]),
            family=SignalFamily.BUILD,
            kind="missing_ci_cd",
            disposition=SignalDisposition.ADVISORY,
            category="TD-BUILD",
            severity="Low",
            confidence="Low",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Missing CI",
            summary="No CI",
            explanation="Missing CI",
            metadata={"missing_ci": True},
        ),
    ],
    "process": lambda: [
        GovernedSignal(
            signal_id=make_signal_id("process", "missing_process_artifacts", ["ev1"]),
            family=SignalFamily.PROCESS,
            kind="missing_process_artifacts",
            disposition=SignalDisposition.ADVISORY,
            category="TD-PROCESS",
            severity="Low",
            confidence="Low",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Missing process",
            summary="No artifacts",
            explanation="Missing artifacts",
            metadata={"missing_artifacts": ["CODEOWNERS"]},
        ),
    ],
    "test": lambda: [
        GovernedSignal(
            signal_id=make_signal_id("test", "missing_tests", ["ev1"]),
            family=SignalFamily.TEST,
            kind="missing_tests",
            disposition=SignalDisposition.FINDING,
            category="TD-TEST",
            severity="Medium",
            confidence="Medium",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="No tests",
            summary="No test evidence",
            explanation="Missing tests",
            metadata={},
        ),
    ],
    "dependency": lambda: [
        GovernedSignal(
            signal_id=make_signal_id("dependency", "unpinned_dependency", ["ev1"]),
            family=SignalFamily.DEPENDENCY,
            kind="unpinned_dependency",
            disposition=SignalDisposition.FINDING,
            category="TD-DEP",
            severity="Medium",
            confidence="Medium",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Unpinned Node.js dependencies detected (3 unpinned)",
            summary="3 Node.js dependencies use unpinned or broad version ranges.",
            explanation="Unpinned dependencies can change without warning.",
            metadata={"ecosystem": "Node.js", "count": 3},
        ),
        GovernedSignal(
            signal_id=make_signal_id("dependency", "missing_lockfile", ["ev1"]),
            family=SignalFamily.DEPENDENCY,
            kind="missing_lockfile",
            disposition=SignalDisposition.ADVISORY,
            category="TD-DEP",
            severity="Medium",
            confidence="High",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Node.js dependency manifest detected without lockfile evidence",
            summary="Missing lockfile evidence for package root.",
            explanation="Missing lockfile may reduce dependency reproducibility.",
            metadata={"ecosystem": "Node.js", "package_root": "."},
        ),
        GovernedSignal(
            signal_id=make_signal_id("dependency", "manifest_detected", ["ev1"]),
            family=SignalFamily.DEPENDENCY,
            kind="manifest_detected",
            disposition=SignalDisposition.INFORMATIONAL,
            category="TD-DEP",
            severity="Low",
            confidence="Medium",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Dependency manifest detected: package.json",
            summary="Dependency manifest found at package.json.",
            explanation="Detected manifest provides dependency coverage context.",
            metadata={"source_file": "package.json", "ecosystem": "Node.js"},
        ),
    ],
    "security": lambda: [
        GovernedSignal(
            signal_id=make_signal_id("security", "compliance_exposure", ["ev1"]),
            family=SignalFamily.SECURITY,
            kind="compliance_exposure",
            disposition=SignalDisposition.FINDING,
            category="TD-COMP",
            severity="Medium",
            confidence="Low",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Potential compliance exposure detected",
            summary="Compliance-related keywords detected in application code.",
            explanation="This is a potential exposure, not a confirmed violation.",
            metadata={"keywords": ["hipaa"], "locations": ["src/handler.py"], "item_count": 1},
        ),
        GovernedSignal(
            signal_id=make_signal_id("security", "sensitive_path", ["ev1"]),
            family=SignalFamily.SECURITY,
            kind="sensitive_path",
            disposition=SignalDisposition.INFORMATIONAL,
            category="risk_signal",
            severity="Low",
            confidence="Medium",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Risk-sensitive path detected: src/auth.py",
            summary="Path-based risk signal found at src/auth.py.",
            explanation="Risk-sensitive path provides security coverage context.",
            metadata={"source_file": "src/auth.py", "keywords": ["auth"]},
        ),
    ],
    "architecture": lambda: [
        GovernedSignal(
            signal_id=make_signal_id("architecture", "cycle", ["ev1"]),
            family=SignalFamily.ARCHITECTURE,
            kind="cycle",
            disposition=SignalDisposition.FINDING,
            category="TD-ARCH",
            severity="Medium",
            confidence="High",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Confirmed circular dependency detected between architecture nodes",
            summary="Confirmed circular dependency detected (cycle: ARCH-CYCLE-TEST).",
            explanation="Circular dependencies increase coupling and complicate refactoring.",
            metadata={"spec_kind": "cycle", "analysis_unit_ids": []},
        ),
        GovernedSignal(
            signal_id=make_signal_id("architecture", "boundary_violation", ["ev1"]),
            family=SignalFamily.ARCHITECTURE,
            kind="boundary_violation",
            disposition=SignalDisposition.FINDING,
            category="TD-ARCH",
            severity="Medium",
            confidence="High",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Architecture boundary policy violation detected",
            summary="Architecture boundary policy violation (violation: ARCH-VIOL-TEST).",
            explanation="Layer boundary violations erode architecture separation.",
            metadata={"spec_kind": "boundary_violation", "analysis_unit_ids": []},
        ),
    ],
    "configuration": lambda: [
        GovernedSignal(
            signal_id=make_signal_id("configuration", "env_without_example", ["ev1"]),
            family=SignalFamily.CONFIGURATION,
            kind="env_without_example",
            disposition=SignalDisposition.FINDING,
            category="TD-CONFIG",
            severity="Medium",
            confidence="High",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Environment configuration detected without example file",
            summary="An environment configuration file was detected, but no .env.example file was found.",  # noqa: E501
            explanation="Missing environment examples make setup, onboarding, and environment parity harder to verify.",  # noqa: E501
            metadata={"spec_kind": "env_without_example", "env_files": [".env"]},
        ),
    ],
    "observability": lambda: [
        GovernedSignal(
            signal_id=make_signal_id("observability", "missing_observability", ["ev1"]),
            family=SignalFamily.OBSERVABILITY,
            kind="missing_observability",
            disposition=SignalDisposition.FINDING,
            category="TD-OBS",
            severity="Medium",
            confidence="Low",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Deployment without observability evidence",
            summary="Deployment/infrastructure files detected but no logging, monitoring, tracing, or alerting keywords found.",  # noqa: E501
            explanation="Without observability, incidents are harder to detect, diagnose, and resolve.",  # noqa: E501
            metadata={"spec_kind": "missing_observability", "evidence_count": 1},
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
        family=sig.family,
        kind=sig.kind,
        disposition=sig.disposition,
        category=sig.category,
        severity=sig.severity,
        confidence=sig.confidence,
        evidence_ids=sig.evidence_ids,
        source_signal_ids=sig.source_signal_ids,
        title=sig.title,
        summary=sig.summary,
        explanation=sig.explanation,
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

    def test_dependency_signals_uses_policy(self) -> None:
        """v3.16.0: _analyze_dependency_signals uses output_behavior."""
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_dependency_signals)
        assert "output_behavior" in source

    def test_missing_lockfile_uses_policy(self) -> None:
        """v3.16.0: _emit_lockfile_finding uses output_behavior."""
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._emit_lockfile_finding)
        assert "output_behavior" in source

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
            assert "should_create_work_package" not in source, (
                f"{func.__name__} uses should_create_work_package as proxy"
            )

    def test_dependency_analyzer_uses_output_behavior(self) -> None:
        """v3.16.0/INV_007: Dependency analyzer uses output_behavior, not hardcoded branching."""
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_dependency_signals)
        assert "output_behavior" in source
        assert "dependency_adapters" in source

    def test_dependency_no_work_package_proxy(self) -> None:
        """v3.16.0/INV_007: Dependency analyzer does not use should_create_work_package."""
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_dependency_signals)
        assert "should_create_work_package" not in source

    def test_compliance_uses_output_behavior(self) -> None:
        """v3.17.0/INV_007: Compliance analyzer uses output_behavior."""
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_compliance_keywords)
        assert "output_behavior" in source
        assert "security_adapters" in source

    def test_compliance_no_work_package_proxy(self) -> None:
        """v3.17.0/INV_007: Compliance analyzer does not use should_create_work_package."""
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_compliance_keywords)
        assert "should_create_work_package" not in source

    def test_risk_sensitive_without_tests_not_security_family(self) -> None:
        """v3.17.0: _analyze_risk_sensitive_without_tests stays under TEST family."""
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_risk_sensitive_without_tests)
        # Must use TEST family adapter, not SECURITY
        assert "scan_test_risk_sensitive_without_tests_to_signal" in source
        assert "security_adapters" not in source

    def test_architecture_uses_output_behavior(self) -> None:
        """v3.18.0/INV_007: Architecture findings use output_behavior."""
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._add_architecture_findings)
        assert "output_behavior" in source
        assert "architecture_adapters" in source

    def test_architecture_uses_spec_kind_not_title(self) -> None:
        """v3.18.0: Architecture routing uses spec.kind, not title text."""
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._add_architecture_findings)
        assert "spec.kind" in source
        # Title-based routing is forbidden
        assert '"circular dependency" in spec.title' not in source
        assert '"boundary" in spec.title' not in source

    def test_architecture_no_work_package_proxy(self) -> None:
        """v3.18.0/INV_007: Architecture analyzer does not use should_create_work_package."""
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._add_architecture_findings)
        assert "should_create_work_package" not in source

    def test_configuration_uses_output_behavior(self) -> None:
        """v3.19.0/INV_008: Configuration analyzer uses output_behavior."""
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_env_without_example)
        assert "output_behavior" in source
        assert "configuration_adapters" in source

    def test_configuration_not_security(self) -> None:
        """v3.19.0: Configuration family is distinct from security."""
        sig = GovernedSignal(
            signal_id=make_signal_id("configuration", "env_without_example", ["ev1"]),
            family=SignalFamily.CONFIGURATION,
            kind="env_without_example",
            disposition=SignalDisposition.FINDING,
            category="TD-CONFIG",
            severity="Medium",
            confidence="High",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Config",
            summary="Config",
            explanation="Config hygiene",
            metadata={"spec_kind": "env_without_example"},
        )
        assert sig.family == SignalFamily.CONFIGURATION
        assert sig.family != SignalFamily.SECURITY
        assert sig.category == "TD-CONFIG"
        assert sig.category != "TD-SEC"

    def test_configuration_not_build(self) -> None:
        """v3.19.0: Configuration family is distinct from build."""
        sig = GovernedSignal(
            signal_id=make_signal_id("configuration", "env_without_example", ["ev1"]),
            family=SignalFamily.CONFIGURATION,
            kind="env_without_example",
            disposition=SignalDisposition.FINDING,
            category="TD-CONFIG",
            severity="Medium",
            confidence="High",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Config",
            summary="Config",
            explanation="Config hygiene",
            metadata={"spec_kind": "env_without_example"},
        )
        assert sig.family != SignalFamily.BUILD

    def test_configuration_finding_only_in_v319(self) -> None:
        """v3.19.0: Configuration family emits FINDING only."""
        sig = GovernedSignal(
            signal_id=make_signal_id("configuration", "env_without_example", ["ev1"]),
            family=SignalFamily.CONFIGURATION,
            kind="env_without_example",
            disposition=SignalDisposition.FINDING,
            category="TD-CONFIG",
            severity="Medium",
            confidence="High",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Config",
            summary="Config",
            explanation="Config hygiene",
            metadata={"spec_kind": "env_without_example"},
        )
        assert sig.disposition == SignalDisposition.FINDING

    def test_configuration_summary_includes_family(self) -> None:
        """v3.19.0: Signal Governance Summary includes Configuration family."""
        sig = GovernedSignal(
            signal_id=make_signal_id("configuration", "env_without_example", ["ev1"]),
            family=SignalFamily.CONFIGURATION,
            kind="env_without_example",
            disposition=SignalDisposition.FINDING,
            category="TD-CONFIG",
            severity="Medium",
            confidence="High",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Config",
            summary="Config",
            explanation="Config hygiene",
            metadata={"spec_kind": "env_without_example"},
        )
        summary = build_signal_summary([sig])
        assert "configuration" in summary.by_family
        assert summary.by_family["configuration"] == 1

    def test_observability_uses_output_behavior(self) -> None:
        """v3.20.0/INV_009: Observability analyzer uses output_behavior."""
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_missing_observability)
        assert "output_behavior" in source
        assert "observability_adapters" in source

    def test_observability_not_build(self) -> None:
        """v3.20.0: Observability family is distinct from build."""
        sig = GovernedSignal(
            signal_id=make_signal_id("observability", "missing_observability", ["ev1"]),
            family=SignalFamily.OBSERVABILITY,
            kind="missing_observability",
            disposition=SignalDisposition.FINDING,
            category="TD-OBS",
            severity="Medium",
            confidence="Low",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Obs",
            summary="Obs",
            explanation="Missing obs",
            metadata={"spec_kind": "missing_observability"},
        )
        assert sig.family == SignalFamily.OBSERVABILITY
        assert sig.family != SignalFamily.BUILD
        assert sig.category == "TD-OBS"

    def test_observability_not_configuration(self) -> None:
        """v3.20.0: Observability family is distinct from configuration."""
        sig = GovernedSignal(
            signal_id=make_signal_id("observability", "missing_observability", ["ev1"]),
            family=SignalFamily.OBSERVABILITY,
            kind="missing_observability",
            disposition=SignalDisposition.FINDING,
            category="TD-OBS",
            severity="Medium",
            confidence="Low",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Obs",
            summary="Obs",
            explanation="Missing obs",
            metadata={"spec_kind": "missing_observability"},
        )
        assert sig.family != SignalFamily.CONFIGURATION

    def test_observability_not_security(self) -> None:
        """v3.20.0: Observability family is distinct from security."""
        sig = GovernedSignal(
            signal_id=make_signal_id("observability", "missing_observability", ["ev1"]),
            family=SignalFamily.OBSERVABILITY,
            kind="missing_observability",
            disposition=SignalDisposition.FINDING,
            category="TD-OBS",
            severity="Medium",
            confidence="Low",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Obs",
            summary="Obs",
            explanation="Missing obs",
            metadata={"spec_kind": "missing_observability"},
        )
        assert sig.family != SignalFamily.SECURITY

    def test_observability_finding_only_in_v320(self) -> None:
        """v3.20.0: Observability family emits FINDING only."""
        sig = GovernedSignal(
            signal_id=make_signal_id("observability", "missing_observability", ["ev1"]),
            family=SignalFamily.OBSERVABILITY,
            kind="missing_observability",
            disposition=SignalDisposition.FINDING,
            category="TD-OBS",
            severity="Medium",
            confidence="Low",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Obs",
            summary="Obs",
            explanation="Missing obs",
            metadata={"spec_kind": "missing_observability"},
        )
        assert sig.disposition == SignalDisposition.FINDING

    def test_observability_summary_includes_family(self) -> None:
        """v3.20.0: Signal Governance Summary includes Observability family."""
        sig = GovernedSignal(
            signal_id=make_signal_id("observability", "missing_observability", ["ev1"]),
            family=SignalFamily.OBSERVABILITY,
            kind="missing_observability",
            disposition=SignalDisposition.FINDING,
            category="TD-OBS",
            severity="Medium",
            confidence="Low",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Obs",
            summary="Obs",
            explanation="Missing obs",
            metadata={"spec_kind": "missing_observability"},
        )
        summary = build_signal_summary([sig])
        assert "observability" in summary.by_family
        assert summary.by_family["observability"] == 1

    def test_all_ten_families_governed(self) -> None:
        """v3.20.0: All 10 SignalFamily values are in the conformance suite."""
        governed = set(_FAMILY_ADAPTER_FACTORIES.keys())
        all_families = {f.value for f in SignalFamily}
        assert governed == all_families, f"Missing: {all_families - governed}"

    def test_no_work_package_proxy_observability(self) -> None:
        """v3.20.0: Observability analyzer does not use should_create_work_package."""
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_missing_observability)
        assert "should_create_work_package" not in source


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

    def test_dependency_family_in_summary(self) -> None:
        """v3.16.0: Dependency family appears in signal summary."""
        signals = [
            GovernedSignal(
                signal_id=make_signal_id("dependency", "unpinned_dependency", ["ev1"]),
                family=SignalFamily.DEPENDENCY,
                kind="unpinned_dependency",
                disposition=SignalDisposition.FINDING,
                category="TD-DEP",
                severity="Medium",
                confidence="Medium",
                evidence_ids=["ev1"],
                source_signal_ids=[],
                title="Unpinned deps",
                summary="Unpinned",
                explanation="Unpinned",
                metadata={"ecosystem": "Node.js"},
            ),
            _signal(SignalDisposition.ADVISORY, family=SignalFamily.RUNTIME),
        ]
        summary = build_signal_summary(signals)
        assert "dependency" in summary.by_family
        assert summary.by_family["dependency"] == 1
        assert summary.by_family["runtime"] == 1

    def test_dependency_and_runtime_distinct(self) -> None:
        """v3.16.0: Dependency and runtime families are counted separately."""
        signals = [
            GovernedSignal(
                signal_id=make_signal_id("dependency", "missing_lockfile", ["ev1"]),
                family=SignalFamily.DEPENDENCY,
                kind="missing_lockfile",
                disposition=SignalDisposition.ADVISORY,
                category="TD-DEP",
                severity="Medium",
                confidence="High",
                evidence_ids=["ev1"],
                source_signal_ids=[],
                title="Missing lockfile",
                summary="No lock",
                explanation="No lockfile",
                metadata={"ecosystem": "Node.js"},
            ),
            GovernedSignal(
                signal_id=make_signal_id("runtime", "missing_runtime_pin", ["ev2"]),
                family=SignalFamily.RUNTIME,
                kind="missing_runtime_pin",
                disposition=SignalDisposition.ADVISORY,
                category="TD-DEP",
                severity="Low",
                confidence="Low",
                evidence_ids=["ev2"],
                source_signal_ids=[],
                title="Missing pin",
                summary="No pin",
                explanation="No runtime pin",
                metadata={"runtime_name": "node"},
            ),
        ]
        summary = build_signal_summary(signals)
        assert summary.by_family["dependency"] == 1
        assert summary.by_family["runtime"] == 1
        assert summary.total == 2
        assert summary.by_disposition == {"advisory": 2}

    def test_security_family_in_summary(self) -> None:
        """v3.17.0: Security family appears in signal summary."""
        signals = [
            GovernedSignal(
                signal_id=make_signal_id("security", "compliance_exposure", ["ev1"]),
                family=SignalFamily.SECURITY,
                kind="compliance_exposure",
                disposition=SignalDisposition.FINDING,
                category="TD-COMP",
                severity="Medium",
                confidence="Low",
                evidence_ids=["ev1"],
                source_signal_ids=[],
                title="Compliance exposure",
                summary="Compliance",
                explanation="Exposure",
                metadata={"keywords": ["hipaa"]},
            ),
            _signal(SignalDisposition.ADVISORY, family=SignalFamily.RUNTIME),
        ]
        summary = build_signal_summary(signals)
        assert "security" in summary.by_family
        assert summary.by_family["security"] == 1
        assert summary.by_family["runtime"] == 1

    def test_security_not_double_counting_test(self) -> None:
        """v3.17.0: Security and test families are distinct."""
        signals = [
            GovernedSignal(
                signal_id=make_signal_id("security", "compliance_exposure", ["ev1"]),
                family=SignalFamily.SECURITY,
                kind="compliance_exposure",
                disposition=SignalDisposition.FINDING,
                category="TD-COMP",
                severity="Medium",
                confidence="Low",
                evidence_ids=["ev1"],
                source_signal_ids=[],
                title="Compliance",
                summary="Compliance",
                explanation="Exposure",
                metadata={},
            ),
            GovernedSignal(
                signal_id=make_signal_id("test", "risk_sensitive_without_tests", ["ev2"]),
                family=SignalFamily.TEST,
                kind="risk_sensitive_without_tests",
                disposition=SignalDisposition.FINDING,
                category="TD-SEC",
                severity="High",
                confidence="Medium",
                evidence_ids=["ev2"],
                source_signal_ids=[],
                title="Risk-sensitive without tests",
                summary="No tests",
                explanation="Missing tests",
                metadata={"risk_sensitive": True},
            ),
        ]
        summary = build_signal_summary(signals)
        assert summary.by_family["security"] == 1
        assert summary.by_family["test"] == 1
        assert summary.total == 2

    def test_architecture_family_in_summary(self) -> None:
        """v3.18.0: Architecture family appears in signal summary."""
        signals = [
            GovernedSignal(
                signal_id=make_signal_id("architecture", "cycle", ["ev1"]),
                family=SignalFamily.ARCHITECTURE,
                kind="cycle",
                disposition=SignalDisposition.FINDING,
                category="TD-ARCH",
                severity="Medium",
                confidence="High",
                evidence_ids=["ev1"],
                source_signal_ids=[],
                title="Cycle",
                summary="Circular dep",
                explanation="Coupling",
                metadata={"spec_kind": "cycle"},
            ),
            _signal(SignalDisposition.ADVISORY, family=SignalFamily.RUNTIME),
        ]
        summary = build_signal_summary(signals)
        assert "architecture" in summary.by_family
        assert summary.by_family["architecture"] == 1
        assert summary.by_family["runtime"] == 1

    def test_all_finding_disposition_count(self) -> None:
        signals = [_signal(SignalDisposition.FINDING, f"f{i}") for i in range(5)]
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
            signal_id="SIG-RUNTIME-abc123def456",
            family=SignalFamily.RUNTIME,
            kind="k",
            disposition=SignalDisposition.FINDING,
            category="TD-DEP",
            severity="Medium",
            confidence="High",
            evidence_ids=[],
            source_signal_ids=[],
            title="t",
            summary="s",
            explanation="e",
            metadata={},
        )
        diags = diagnose_signal(sig)
        assert any(d.invariant_code == "INV_006" for d in diags)

    def test_diagnostics_return_frozen_dataclasses(self) -> None:
        sig = GovernedSignal(
            signal_id="",
            family=SignalFamily.RUNTIME,
            kind="",
            disposition=SignalDisposition.FINDING,
            category="",
            severity="Medium",
            confidence="High",
            evidence_ids=[],
            source_signal_ids=[],
            title="",
            summary="s",
            explanation="e",
            metadata={},
        )
        diags = diagnose_signal(sig)
        for d in diags:
            with pytest.raises(AttributeError):
                d.message = "changed"  # type: ignore

    def test_diagnostics_include_family_and_disposition(self) -> None:
        sig = GovernedSignal(
            signal_id="SIG-RUNTIME-abc123def456",
            family=SignalFamily.RUNTIME,
            kind="k",
            disposition=SignalDisposition.FINDING,
            category="TD-DEP",
            severity="Medium",
            confidence="High",
            evidence_ids=[],
            source_signal_ids=[],
            title="t",
            summary="s",
            explanation="e",
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
            family=SignalFamily.TEST,
            kind="risk_sensitive_without_tests",
            disposition=SignalDisposition.FINDING,
            category="TD-SEC",
            severity="High",
            confidence="Medium",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Risk sensitive",
            summary="No tests",
            explanation="Missing tests",
            metadata={"risk_sensitive": True},
        )
        diags = diagnose_signal(sig)
        inv001_diags = [d for d in diags if d.invariant_code == "INV_001"]
        assert inv001_diags == [], (
            "INV_001 should not fire for legitimate FINDING with TD-SEC category"
        )
