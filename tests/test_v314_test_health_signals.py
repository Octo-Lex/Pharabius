"""v3.14.0 — Signal Governance Adoption: Test Health Signals.

Contract tests for test signal adapters. Validates that test-health signals
are governed correctly — findings for missing tests/coverage gaps,
informational for detected test files and coverage reports.

Acceptance criteria:
  1. Test-health signals emit GovernedSignal
  2. Existing test-health findings/advisories remain behaviorally unchanged
  3. Runtime/docs/build/process governed signal behavior unchanged
  4. Signal summary includes `test`
  5. Report output groups test signals with existing families
  6. Test informational signals remain non-actionable
  7. Test advisories do not generate work packages
  8. Test findings created only from SignalDisposition.FINDING
  9. Contract tests cover test family adapters and analyzer boundaries
 10. Existing 2294 tests pass
"""

from __future__ import annotations

from pharabius.core.signals.adapters import (
    scan_test_coverage_evidence_to_signal,
    scan_test_coverage_gap_to_signal,
    scan_test_evidence_to_signal,
    scan_test_missing_to_signal,
    scan_test_risk_sensitive_without_tests_to_signal,
)
from pharabius.core.signals.models import (
    SignalDisposition,
    SignalFamily,
)
from pharabius.core.signals.policy import (
    is_reportable,
    should_create_advisory,
    should_create_finding,
    should_create_work_package,
)
from pharabius.core.signals.summary import build_signal_summary

# ── S01: Test signal adapters ─────────────────────────────────────────


class TestMissingTestsAdapter:
    """scan_test_missing_to_signal produces FINDING — missing tests is actionable debt."""

    def test_missing_tests_is_finding(self) -> None:
        signal = scan_test_missing_to_signal(evidence_ids=["ev1"])
        assert signal.disposition == SignalDisposition.FINDING

    def test_missing_tests_family(self) -> None:
        signal = scan_test_missing_to_signal(evidence_ids=["ev1"])
        assert signal.family == SignalFamily.TEST

    def test_missing_tests_kind(self) -> None:
        signal = scan_test_missing_to_signal(evidence_ids=["ev1"])
        assert signal.kind == "missing_tests"

    def test_missing_tests_category(self) -> None:
        signal = scan_test_missing_to_signal(evidence_ids=["ev1"])
        assert signal.category == "TD-TEST"

    def test_missing_tests_creates_finding(self) -> None:
        signal = scan_test_missing_to_signal(evidence_ids=["ev1"])
        assert should_create_finding(signal)

    def test_missing_tests_creates_work_package(self) -> None:
        signal = scan_test_missing_to_signal(evidence_ids=["ev1"])
        assert should_create_work_package(signal)

    def test_missing_tests_is_reportable(self) -> None:
        signal = scan_test_missing_to_signal(evidence_ids=["ev1"])
        assert is_reportable(signal)

    def test_missing_tests_with_risk_signals_higher_severity(self) -> None:
        sig_with = scan_test_missing_to_signal(evidence_ids=["ev1"], has_risk_signals=True)
        sig_without = scan_test_missing_to_signal(evidence_ids=["ev1"], has_risk_signals=False)
        assert sig_with.severity != sig_without.severity

    def test_missing_tests_metadata(self) -> None:
        signal = scan_test_missing_to_signal(evidence_ids=["ev1"], has_risk_signals=True)
        assert signal.metadata["has_risk_signals"] is True


class TestRiskSensitiveAdapter:
    """scan_test_risk_sensitive_without_tests_to_signal produces FINDING."""

    def test_risk_sensitive_is_finding(self) -> None:
        signal = scan_test_risk_sensitive_without_tests_to_signal(evidence_ids=["ev1"])
        assert signal.disposition == SignalDisposition.FINDING

    def test_risk_sensitive_family(self) -> None:
        signal = scan_test_risk_sensitive_without_tests_to_signal(evidence_ids=["ev1"])
        assert signal.family == SignalFamily.TEST

    def test_risk_sensitive_category_is_sec(self) -> None:
        signal = scan_test_risk_sensitive_without_tests_to_signal(evidence_ids=["ev1"])
        assert signal.category == "TD-SEC"

    def test_risk_sensitive_creates_finding(self) -> None:
        signal = scan_test_risk_sensitive_without_tests_to_signal(evidence_ids=["ev1"])
        assert should_create_finding(signal)

    def test_risk_sensitive_creates_work_package(self) -> None:
        signal = scan_test_risk_sensitive_without_tests_to_signal(evidence_ids=["ev1"])
        assert should_create_work_package(signal)

    def test_risk_sensitive_severity_high(self) -> None:
        signal = scan_test_risk_sensitive_without_tests_to_signal(evidence_ids=["ev1"])
        assert signal.severity == "High"


class TestCoverageGapAdapter:
    """scan_test_coverage_gap_to_signal produces FINDING."""

    def test_coverage_gap_is_finding(self) -> None:
        signal = scan_test_coverage_gap_to_signal(
            evidence_ids=["ev1"],
            low_count=3,
            threshold_pct=60.0,
        )
        assert signal.disposition == SignalDisposition.FINDING

    def test_coverage_gap_family(self) -> None:
        signal = scan_test_coverage_gap_to_signal(
            evidence_ids=["ev1"],
            low_count=3,
            threshold_pct=60.0,
        )
        assert signal.family == SignalFamily.TEST

    def test_coverage_gap_category(self) -> None:
        signal = scan_test_coverage_gap_to_signal(
            evidence_ids=["ev1"],
            low_count=3,
            threshold_pct=60.0,
        )
        assert signal.category == "TD-TEST"

    def test_coverage_gap_creates_finding(self) -> None:
        signal = scan_test_coverage_gap_to_signal(
            evidence_ids=["ev1"],
            low_count=3,
            threshold_pct=60.0,
        )
        assert should_create_finding(signal)

    def test_coverage_gap_creates_work_package(self) -> None:
        signal = scan_test_coverage_gap_to_signal(
            evidence_ids=["ev1"],
            low_count=3,
            threshold_pct=60.0,
        )
        assert should_create_work_package(signal)

    def test_coverage_gap_title_includes_counts(self) -> None:
        signal = scan_test_coverage_gap_to_signal(
            evidence_ids=["ev1"],
            low_count=3,
            threshold_pct=60.0,
        )
        assert "3" in signal.title
        assert "60" in signal.title

    def test_coverage_gap_metadata(self) -> None:
        signal = scan_test_coverage_gap_to_signal(
            evidence_ids=["ev1"],
            low_count=3,
            threshold_pct=60.0,
        )
        assert signal.metadata["low_count"] == 3
        assert signal.metadata["threshold_pct"] == 60.0


class TestEvidenceAdapter:
    """scan_test_evidence_to_signal produces INFORMATIONAL."""

    def test_evidence_is_informational(self) -> None:
        class FakeEv:
            evidence_id = "ev-test-1"

            class location:
                file = "tests/test_main.py"

        signal = scan_test_evidence_to_signal(FakeEv())
        assert signal.disposition == SignalDisposition.INFORMATIONAL

    def test_evidence_family(self) -> None:
        class FakeEv:
            evidence_id = "ev-test-1"

            class location:
                file = "tests/test_main.py"

        signal = scan_test_evidence_to_signal(FakeEv())
        assert signal.family == SignalFamily.TEST

    def test_evidence_does_not_create_finding(self) -> None:
        class FakeEv:
            evidence_id = "ev-test-1"

            class location:
                file = "tests/test_main.py"

        signal = scan_test_evidence_to_signal(FakeEv())
        assert not should_create_finding(signal)

    def test_evidence_does_not_create_work_package(self) -> None:
        class FakeEv:
            evidence_id = "ev-test-1"

            class location:
                file = "tests/test_main.py"

        signal = scan_test_evidence_to_signal(FakeEv())
        assert not should_create_work_package(signal)

    def test_evidence_is_not_reportable(self) -> None:
        class FakeEv:
            evidence_id = "ev-test-1"

            class location:
                file = "tests/test_main.py"

        signal = scan_test_evidence_to_signal(FakeEv())
        assert not is_reportable(signal)


class TestCoverageEvidenceAdapter:
    """scan_test_coverage_evidence_to_signal produces INFORMATIONAL."""

    def test_coverage_evidence_is_informational(self) -> None:
        class FakeEv:
            evidence_id = "ev-cov-1"
            type = "coverage_report_detected"

            class location:
                file = "coverage/lcov.info"

        signal = scan_test_coverage_evidence_to_signal(FakeEv())
        assert signal.disposition == SignalDisposition.INFORMATIONAL

    def test_coverage_evidence_family(self) -> None:
        class FakeEv:
            evidence_id = "ev-cov-1"
            type = "coverage_report_detected"

            class location:
                file = "coverage/lcov.info"

        signal = scan_test_coverage_evidence_to_signal(FakeEv())
        assert signal.family == SignalFamily.TEST

    def test_coverage_evidence_does_not_create_finding(self) -> None:
        class FakeEv:
            evidence_id = "ev-cov-1"
            type = "coverage_report_detected"

            class location:
                file = "coverage/lcov.info"

        signal = scan_test_coverage_evidence_to_signal(FakeEv())
        assert not should_create_finding(signal)


# ── Adapter contracts ─────────────────────────────────────────────────


class TestAdapterContracts:
    """All test adapters share common contract expectations."""

    def test_all_adapters_use_test_family(self) -> None:
        s1 = scan_test_missing_to_signal(evidence_ids=["ev1"])
        s2 = scan_test_risk_sensitive_without_tests_to_signal(evidence_ids=["ev1"])
        s3 = scan_test_coverage_gap_to_signal(evidence_ids=["ev1"], low_count=1, threshold_pct=60.0)
        assert s1.family == SignalFamily.TEST
        assert s2.family == SignalFamily.TEST
        assert s3.family == SignalFamily.TEST

    def test_all_adapters_produce_deterministic_ids(self) -> None:
        s1 = scan_test_missing_to_signal(evidence_ids=["ev1"])
        s2 = scan_test_missing_to_signal(evidence_ids=["ev1"])
        assert s1.signal_id == s2.signal_id

    def test_different_kinds_produce_different_ids(self) -> None:
        s1 = scan_test_missing_to_signal(evidence_ids=["ev1"])
        s3 = scan_test_coverage_gap_to_signal(evidence_ids=["ev1"], low_count=1, threshold_pct=60.0)
        assert s1.signal_id != s3.signal_id


# ── Signal summary includes test family ───────────────────────────────


class TestSignalSummaryWithTest:
    """Signal summary includes test family."""

    def test_summary_includes_test_family(self) -> None:
        signals = [
            scan_test_missing_to_signal(evidence_ids=["ev1"]),
            scan_test_coverage_gap_to_signal(evidence_ids=["ev2"], low_count=2, threshold_pct=60.0),
        ]
        summary = build_signal_summary(signals)
        assert "test" in summary.by_family

    def test_summary_counts_test_findings(self) -> None:
        signals = [
            scan_test_missing_to_signal(evidence_ids=["ev1"]),
            scan_test_risk_sensitive_without_tests_to_signal(evidence_ids=["ev2"]),
            scan_test_coverage_gap_to_signal(evidence_ids=["ev3"], low_count=1, threshold_pct=60.0),
        ]
        summary = build_signal_summary(signals)
        assert summary.by_disposition.get("finding", 0) == 3

    def test_summary_mixed_families(self) -> None:
        from pharabius.core.signals.adapters import docs_missing_to_signal

        signals = [
            scan_test_missing_to_signal(evidence_ids=["ev1"]),
            docs_missing_to_signal(evidence_ids=["ev2"]),
        ]
        summary = build_signal_summary(signals)
        assert "test" in summary.by_family
        assert "documentation" in summary.by_family


# ── Migration boundary tests ──────────────────────────────────────────


class TestMigrationBoundary:
    """Migrated test analyzers use should_create_finding()."""

    def test_missing_tests_analyzer_imports_should_create_finding(self) -> None:
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_missing_tests)
        assert "should_create_finding" in source

    def test_risk_sensitive_analyzer_imports_should_create_finding(self) -> None:
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_risk_sensitive_without_tests)
        assert "should_create_finding" in source

    def test_coverage_gaps_analyzer_imports_should_create_finding(self) -> None:
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_coverage_gaps)
        assert "should_create_finding" in source

    def test_missing_tests_does_not_use_should_create_work_package(self) -> None:
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_missing_tests)
        assert "should_create_work_package" not in source

    def test_risk_sensitive_does_not_use_should_create_work_package(self) -> None:
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_risk_sensitive_without_tests)
        assert "should_create_work_package" not in source

    def test_coverage_gaps_does_not_use_should_create_work_package(self) -> None:
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_coverage_gaps)
        assert "should_create_work_package" not in source


# ── Behavior preservation ─────────────────────────────────────────────


class TestBehaviorPreserved:
    """AC2: Existing test-health findings/advisories remain unchanged."""

    def test_missing_tests_title(self) -> None:
        signal = scan_test_missing_to_signal(evidence_ids=["ev1"])
        assert signal.title == "No test evidence detected"

    def test_risk_sensitive_title(self) -> None:
        signal = scan_test_risk_sensitive_without_tests_to_signal(evidence_ids=["ev1"])
        assert signal.title == "Risk-sensitive areas detected without test evidence"

    def test_coverage_gap_custom_title(self) -> None:
        signal = scan_test_coverage_gap_to_signal(
            evidence_ids=["ev1"],
            low_count=5,
            threshold_pct=80.0,
        )
        assert "5" in signal.title
        assert "80" in signal.title

    def test_missing_tests_category_td_test(self) -> None:
        signal = scan_test_missing_to_signal(evidence_ids=["ev1"])
        assert signal.category == "TD-TEST"

    def test_risk_sensitive_category_td_sec(self) -> None:
        signal = scan_test_risk_sensitive_without_tests_to_signal(evidence_ids=["ev1"])
        assert signal.category == "TD-SEC"

    def test_coverage_gap_category_td_test(self) -> None:
        signal = scan_test_coverage_gap_to_signal(
            evidence_ids=["ev1"],
            low_count=1,
            threshold_pct=60.0,
        )
        assert signal.category == "TD-TEST"


# ── Advisory boundary: test signals should NOT be advisories ──────────


class TestNoAdvisoryLeakage:
    """Test findings are not advisories — they are real technical debt."""

    def test_missing_tests_not_advisory(self) -> None:
        signal = scan_test_missing_to_signal(evidence_ids=["ev1"])
        assert not should_create_advisory(signal)

    def test_risk_sensitive_not_advisory(self) -> None:
        signal = scan_test_risk_sensitive_without_tests_to_signal(evidence_ids=["ev1"])
        assert not should_create_advisory(signal)

    def test_coverage_gap_not_advisory(self) -> None:
        signal = scan_test_coverage_gap_to_signal(
            evidence_ids=["ev1"],
            low_count=1,
            threshold_pct=60.0,
        )
        assert not should_create_advisory(signal)
