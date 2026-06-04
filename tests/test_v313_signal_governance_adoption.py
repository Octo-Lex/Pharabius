"""v3.13.0 — Signal Governance Adoption: Documentation, Build & Process Advisories.

Contract tests for documentation, build, and process signal adapters.
Validates that signal governance is reusable beyond runtime.

Acceptance criteria:
  1. Documentation signals emit GovernedSignal
  2. Build/CI signals emit GovernedSignal
  3. Runtime governed signal behavior unchanged
  4. Signal summary includes runtime, documentation, and build families
  5. Documentation/build/process advisories do NOT generate work packages
  6. Informational documentation/build signals remain non-actionable
  7. Documentation/build/process findings only from SignalDisposition.FINDING
  8. Report output groups signals by family
  9. Contract tests cover each migrated family
 10. Existing 2232 tests pass
 11. TD-PROCESS advisories use SignalFamily.PROCESS
 12. Signal summary built from GovernedSignal instances, not raw evidence heuristics
 13. Documentation/build/process migrated signals do not emit FINDING in v3.13.0
 14. Migrated analyzers use should_create_advisory(), not should_create_work_package()
 15. Existing advisory titles/descriptions/severity/risk behavior remain unchanged
"""

from __future__ import annotations

import pytest

from pharabius.core.signals.adapters import (
    build_ci_evidence_to_signal,
    build_missing_ci_to_signal,
    docs_evidence_to_signal,
    docs_missing_to_signal,
    process_missing_artifacts_to_signal,
)
from pharabius.core.signals.models import (
    GovernedSignal,
    SignalDisposition,
    SignalFamily,
    make_signal_id,
)
from pharabius.core.signals.policy import (
    is_informational,
    is_reportable,
    should_create_advisory,
    should_create_finding,
    should_create_work_package,
)
from pharabius.core.signals.summary import build_signal_summary

# ── S01: Documentation adapters ───────────────────────────────────────


class TestDocsMissingAdapter:
    """docs_missing_to_signal produces correct ADVISORY governed signals."""

    def test_missing_docs_is_advisory(self) -> None:
        signal = docs_missing_to_signal(evidence_ids=["ev1"])
        assert signal.disposition == SignalDisposition.ADVISORY

    def test_missing_docs_family(self) -> None:
        signal = docs_missing_to_signal(evidence_ids=["ev1"])
        assert signal.family == SignalFamily.DOCUMENTATION

    def test_missing_docs_kind(self) -> None:
        signal = docs_missing_to_signal(evidence_ids=["ev1"])
        assert signal.kind == "missing_documentation"

    def test_missing_docs_category(self) -> None:
        signal = docs_missing_to_signal(evidence_ids=["ev1"])
        assert signal.category == "TD-DOC"

    def test_missing_docs_does_not_create_finding(self) -> None:
        signal = docs_missing_to_signal(evidence_ids=["ev1"])
        assert not should_create_finding(signal)

    def test_missing_docs_does_not_create_work_package(self) -> None:
        signal = docs_missing_to_signal(evidence_ids=["ev1"])
        assert not should_create_work_package(signal)

    def test_missing_docs_creates_advisory(self) -> None:
        signal = docs_missing_to_signal(evidence_ids=["ev1"])
        assert should_create_advisory(signal)

    def test_missing_docs_is_reportable(self) -> None:
        signal = docs_missing_to_signal(evidence_ids=["ev1"])
        assert is_reportable(signal)

    def test_missing_docs_not_informational(self) -> None:
        signal = docs_missing_to_signal(evidence_ids=["ev1"])
        assert not is_informational(signal)

    def test_missing_docs_deterministic_id(self) -> None:
        s1 = docs_missing_to_signal(evidence_ids=["ev1"])
        s2 = docs_missing_to_signal(evidence_ids=["ev1"])
        assert s1.signal_id == s2.signal_id

    def test_missing_docs_metadata(self) -> None:
        signal = docs_missing_to_signal(evidence_ids=["ev1"])
        assert signal.metadata["missing_docs"] is True


class TestDocsEvidenceAdapter:
    """docs_evidence_to_signal produces correct INFORMATIONAL governed signals."""

    def test_docs_evidence_is_informational(self) -> None:
        class FakeEv:
            evidence_id = "ev-doc-1"

            class location:
                file = "README.md"

        signal = docs_evidence_to_signal(FakeEv())
        assert signal.disposition == SignalDisposition.INFORMATIONAL

    def test_docs_evidence_family(self) -> None:
        class FakeEv:
            evidence_id = "ev-doc-1"

            class location:
                file = "README.md"

        signal = docs_evidence_to_signal(FakeEv())
        assert signal.family == SignalFamily.DOCUMENTATION

    def test_docs_evidence_kind(self) -> None:
        class FakeEv:
            evidence_id = "ev-doc-1"

            class location:
                file = "README.md"

        signal = docs_evidence_to_signal(FakeEv())
        assert signal.kind == "documentation_evidence"

    def test_docs_evidence_does_not_create_advisory(self) -> None:
        class FakeEv:
            evidence_id = "ev-doc-1"

            class location:
                file = "README.md"

        signal = docs_evidence_to_signal(FakeEv())
        assert not should_create_advisory(signal)

    def test_docs_evidence_does_not_create_work_package(self) -> None:
        class FakeEv:
            evidence_id = "ev-doc-1"

            class location:
                file = "README.md"

        signal = docs_evidence_to_signal(FakeEv())
        assert not should_create_work_package(signal)


# ── S02: Build adapters ───────────────────────────────────────────────


class TestBuildMissingCIAdapter:
    """build_missing_ci_to_signal produces correct ADVISORY governed signals."""

    def test_missing_ci_is_advisory(self) -> None:
        signal = build_missing_ci_to_signal(evidence_ids=["ev1"])
        assert signal.disposition == SignalDisposition.ADVISORY

    def test_missing_ci_family(self) -> None:
        signal = build_missing_ci_to_signal(evidence_ids=["ev1"])
        assert signal.family == SignalFamily.BUILD

    def test_missing_ci_kind(self) -> None:
        signal = build_missing_ci_to_signal(evidence_ids=["ev1"])
        assert signal.kind == "missing_ci_cd"

    def test_missing_ci_category(self) -> None:
        signal = build_missing_ci_to_signal(evidence_ids=["ev1"])
        assert signal.category == "TD-BUILD"

    def test_missing_ci_does_not_create_finding(self) -> None:
        signal = build_missing_ci_to_signal(evidence_ids=["ev1"])
        assert not should_create_finding(signal)

    def test_missing_ci_does_not_create_work_package(self) -> None:
        signal = build_missing_ci_to_signal(evidence_ids=["ev1"])
        assert not should_create_work_package(signal)

    def test_missing_ci_creates_advisory(self) -> None:
        signal = build_missing_ci_to_signal(evidence_ids=["ev1"])
        assert should_create_advisory(signal)

    def test_missing_ci_metadata(self) -> None:
        signal = build_missing_ci_to_signal(evidence_ids=["ev1"])
        assert signal.metadata["missing_ci"] is True


class TestBuildCIEvidenceAdapter:
    """build_ci_evidence_to_signal produces correct INFORMATIONAL governed signals."""

    def test_ci_evidence_is_informational(self) -> None:
        class FakeEv:
            evidence_id = "ev-ci-1"

            class location:
                file = ".github/workflows/ci.yml"

        signal = build_ci_evidence_to_signal(FakeEv())
        assert signal.disposition == SignalDisposition.INFORMATIONAL

    def test_ci_evidence_family(self) -> None:
        class FakeEv:
            evidence_id = "ev-ci-1"

            class location:
                file = ".github/workflows/ci.yml"

        signal = build_ci_evidence_to_signal(FakeEv())
        assert signal.family == SignalFamily.BUILD

    def test_ci_evidence_does_not_create_advisory(self) -> None:
        class FakeEv:
            evidence_id = "ev-ci-1"

            class location:
                file = ".github/workflows/ci.yml"

        signal = build_ci_evidence_to_signal(FakeEv())
        assert not should_create_advisory(signal)


# ── S02b: Process adapters ────────────────────────────────────────────


class TestProcessMissingArtifactsAdapter:
    """process_missing_artifacts_to_signal produces correct ADVISORY governed signals."""

    def test_missing_process_is_advisory(self) -> None:
        signal = process_missing_artifacts_to_signal(
            missing_artifacts=["CODEOWNERS", "CONTRIBUTING.md"],
            evidence_ids=["ev1"],
        )
        assert signal.disposition == SignalDisposition.ADVISORY

    def test_missing_process_family_is_process_not_build(self) -> None:
        """AC11: TD-PROCESS uses SignalFamily.PROCESS, not BUILD."""
        signal = process_missing_artifacts_to_signal(
            missing_artifacts=["CODEOWNERS"],
            evidence_ids=["ev1"],
        )
        assert signal.family == SignalFamily.PROCESS
        assert signal.family != SignalFamily.BUILD

    def test_missing_process_category(self) -> None:
        signal = process_missing_artifacts_to_signal(
            missing_artifacts=["CODEOWNERS"],
            evidence_ids=["ev1"],
        )
        assert signal.category == "TD-PROCESS"

    def test_missing_process_does_not_create_finding(self) -> None:
        signal = process_missing_artifacts_to_signal(
            missing_artifacts=["CODEOWNERS"],
            evidence_ids=["ev1"],
        )
        assert not should_create_finding(signal)

    def test_missing_process_does_not_create_work_package(self) -> None:
        signal = process_missing_artifacts_to_signal(
            missing_artifacts=["CODEOWNERS"],
            evidence_ids=["ev1"],
        )
        assert not should_create_work_package(signal)

    def test_missing_process_creates_advisory(self) -> None:
        signal = process_missing_artifacts_to_signal(
            missing_artifacts=["CODEOWNERS"],
            evidence_ids=["ev1"],
        )
        assert should_create_advisory(signal)

    def test_missing_process_metadata(self) -> None:
        signal = process_missing_artifacts_to_signal(
            missing_artifacts=["CODEOWNERS", "CONTRIBUTING.md"],
            evidence_ids=["ev1"],
        )
        assert signal.metadata["missing_artifacts"] == ["CODEOWNERS", "CONTRIBUTING.md"]


# ── S03: Adapter contracts ────────────────────────────────────────────


class TestAdapterContracts:
    """All adapters share common contract expectations."""

    def test_documentation_adapter_uses_documentation_family(self) -> None:
        sig = docs_missing_to_signal(evidence_ids=["ev1"])
        assert sig.family == SignalFamily.DOCUMENTATION

    def test_build_adapter_uses_build_family(self) -> None:
        sig = build_missing_ci_to_signal(evidence_ids=["ev1"])
        assert sig.family == SignalFamily.BUILD

    def test_process_adapter_uses_process_family(self) -> None:
        sig = process_missing_artifacts_to_signal(
            missing_artifacts=["CODEOWNERS"],
            evidence_ids=["ev1"],
        )
        assert sig.family == SignalFamily.PROCESS

    def test_all_adapters_produce_deterministic_ids(self) -> None:
        s1 = docs_missing_to_signal(evidence_ids=["ev1"])
        s2 = build_missing_ci_to_signal(evidence_ids=["ev1"])
        s3 = process_missing_artifacts_to_signal(
            missing_artifacts=["CODEOWNERS"],
            evidence_ids=["ev1"],
        )
        # Same evidence_ids but different families → different IDs
        ids = {s1.signal_id, s2.signal_id, s3.signal_id}
        assert len(ids) == 3

    def test_categories_match_analyzer_categories(self) -> None:
        doc = docs_missing_to_signal(evidence_ids=["ev1"])
        build = build_missing_ci_to_signal(evidence_ids=["ev1"])
        process = process_missing_artifacts_to_signal(
            missing_artifacts=["CODEOWNERS"],
            evidence_ids=["ev1"],
        )
        assert doc.category == "TD-DOC"
        assert build.category == "TD-BUILD"
        assert process.category == "TD-PROCESS"


# ── AC13: No FINDING disposition in v3.13.0 migrated families ─────────


class TestNoFindingInV313:
    """AC13: Documentation/build/process signals do not emit FINDING."""

    def test_docs_missing_not_finding(self) -> None:
        sig = docs_missing_to_signal(evidence_ids=["ev1"])
        assert sig.disposition != SignalDisposition.FINDING

    def test_docs_evidence_not_finding(self) -> None:
        class FakeEv:
            evidence_id = "ev1"

            class location:
                file = "README.md"

        sig = docs_evidence_to_signal(FakeEv())
        assert sig.disposition != SignalDisposition.FINDING

    def test_build_missing_ci_not_finding(self) -> None:
        sig = build_missing_ci_to_signal(evidence_ids=["ev1"])
        assert sig.disposition != SignalDisposition.FINDING

    def test_build_ci_evidence_not_finding(self) -> None:
        class FakeEv:
            evidence_id = "ev1"

            class location:
                file = "ci.yml"

        sig = build_ci_evidence_to_signal(FakeEv())
        assert sig.disposition != SignalDisposition.FINDING

    def test_process_missing_not_finding(self) -> None:
        sig = process_missing_artifacts_to_signal(
            missing_artifacts=["CODEOWNERS"],
            evidence_ids=["ev1"],
        )
        assert sig.disposition != SignalDisposition.FINDING


# ── AC12: Signal summary is signal-driven ─────────────────────────────


class TestSignalSummaryIsSignalDriven:
    """AC12: Summary is built from GovernedSignal instances."""

    def test_summary_from_mixed_families(self) -> None:
        signals = [
            docs_missing_to_signal(evidence_ids=["ev1"]),
            build_missing_ci_to_signal(evidence_ids=["ev2"]),
            process_missing_artifacts_to_signal(
                missing_artifacts=["CODEOWNERS"],
                evidence_ids=["ev3"],
            ),
        ]
        summary = build_signal_summary(signals)
        assert summary.total == 3
        assert "documentation" in summary.by_family
        assert "build" in summary.by_family
        assert "process" in summary.by_family

    def test_summary_disposition_counts(self) -> None:
        signals = [
            docs_missing_to_signal(evidence_ids=["ev1"]),
            build_missing_ci_to_signal(evidence_ids=["ev2"]),
            process_missing_artifacts_to_signal(
                missing_artifacts=["CODEOWNERS"],
                evidence_ids=["ev3"],
            ),
        ]
        summary = build_signal_summary(signals)
        assert summary.by_disposition.get("advisory", 0) == 3
        assert summary.by_disposition.get("finding", 0) == 0

    def test_runtime_summary_unchanged(self) -> None:
        """AC3: Runtime summary behavior unchanged."""
        from pharabius.core.runtime.conflict import RuntimeConflictKind
        from pharabius.core.runtime.models import (
            Confidence,
            RuntimeConflictGroup,
            RuntimeConstraint,
            RuntimeConstraintKind,
            RuntimeEcosystem,
            RuntimeEvidence,
            RuntimeSignalClassification,
            RuntimeSourceGrade,
            RuntimeSourceType,
        )
        from pharabius.core.signals.adapters import runtime_conflict_to_signal

        ev = RuntimeEvidence(
            runtime_evidence_id="rt1",
            runtime_name="Python",
            ecosystem=RuntimeEcosystem.PYTHON,
            constraint=RuntimeConstraint(
                value="3.12",
                kind=RuntimeConstraintKind.EXACT,
            ),
            source_type=RuntimeSourceType.MANIFEST,
            source_path="pyproject.toml",
            source_detail="requires-python",
            source_grade=RuntimeSourceGrade.MANIFEST_PIN,
            confidence=Confidence.HIGH,
        )
        conflict = RuntimeConflictGroup(
            runtime_name="Python",
            ecosystem=RuntimeEcosystem.PYTHON,
            conflict_kind=RuntimeConflictKind.EXACT_EXACT_MISMATCH,
            explanation="test conflict",
            evidence=[ev],
        )
        sig = runtime_conflict_to_signal(conflict)
        assert sig.disposition == SignalDisposition.FINDING
        assert sig.family == SignalFamily.RUNTIME


# ── AC14: Migration boundary tests ────────────────────────────────────


class TestMigrationBoundary:
    """AC14: Migrated analyzers use should_create_advisory()."""

    def test_missing_docs_analyzer_imports_should_create_advisory(self) -> None:
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_missing_docs)
        assert "should_create_advisory" in source

    def test_missing_ci_analyzer_imports_should_create_advisory(self) -> None:
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_missing_ci)
        assert "should_create_advisory" in source

    def test_missing_process_analyzer_imports_should_create_advisory(self) -> None:
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_missing_process_artifacts)
        assert "should_create_advisory" in source

    def test_missing_docs_analyzer_does_not_use_should_create_work_package(self) -> None:
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_missing_docs)
        assert "should_create_work_package" not in source

    def test_missing_ci_analyzer_does_not_use_should_create_work_package(self) -> None:
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_missing_ci)
        assert "should_create_work_package" not in source

    def test_missing_process_analyzer_does_not_use_should_create_work_package(self) -> None:
        import inspect

        from pharabius.core import analyzer

        source = inspect.getsource(analyzer._analyze_missing_process_artifacts)
        assert "should_create_work_package" not in source


# ── AC11: PROCESS family exists ───────────────────────────────────────


class TestProcessFamily:
    """AC11: TD-PROCESS uses SignalFamily.PROCESS."""

    def test_process_family_exists(self) -> None:
        assert hasattr(SignalFamily, "PROCESS")

    def test_process_family_value(self) -> None:
        assert SignalFamily.PROCESS.value == "process"

    def test_process_distinct_from_build(self) -> None:
        assert SignalFamily.PROCESS != SignalFamily.BUILD


# ── AC15: Titles and descriptions preserved ───────────────────────────


class TestAnalyzerOutputPreserved:
    """AC15: Existing advisory titles/descriptions/severity unchanged."""

    def test_docs_missing_title(self) -> None:
        sig = docs_missing_to_signal(evidence_ids=["ev1"])
        assert sig.title == "No documentation evidence detected"

    def test_build_missing_ci_title(self) -> None:
        sig = build_missing_ci_to_signal(evidence_ids=["ev1"])
        assert sig.title == "No CI/CD workflow evidence detected"

    def test_process_missing_title(self) -> None:
        sig = process_missing_artifacts_to_signal(
            missing_artifacts=["CODEOWNERS"],
            evidence_ids=["ev1"],
        )
        assert sig.title == "Missing repository process artifacts"

    def test_docs_severity_low(self) -> None:
        sig = docs_missing_to_signal(evidence_ids=["ev1"])
        assert sig.severity == "Low"

    def test_build_severity_low(self) -> None:
        sig = build_missing_ci_to_signal(evidence_ids=["ev1"])
        assert sig.severity == "Low"

    def test_process_severity_low(self) -> None:
        sig = process_missing_artifacts_to_signal(
            missing_artifacts=["CODEOWNERS"],
            evidence_ids=["ev1"],
        )
        assert sig.severity == "Low"
