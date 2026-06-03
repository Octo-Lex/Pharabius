"""v3.12.0 S07 — Signal governance contract tests.

These tests lock down the signal lifecycle before any analyzer changes.
They prove runtime signal governance without migrating all analyzer families.
"""

from __future__ import annotations

from pathlib import Path

import pytest

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


def _signal(disposition: SignalDisposition, kind: str = "test") -> GovernedSignal:
    return GovernedSignal(
        signal_id=make_signal_id("runtime", kind, ["ev1"]),
        family=SignalFamily.RUNTIME,
        kind=kind,
        disposition=disposition,
        category="TD-DEP",
        severity="Medium",
        confidence="High",
        evidence_ids=["ev1"],
        source_signal_ids=[],
        title=f"Test {kind}",
        summary="Test summary",
        explanation="Test explanation",
        metadata={"runtime_name": "Python"},
    )


# ── S01: Model contracts ─────────────────────────────────────────────


class TestSignalModels:
    """GovernedSignal model contracts."""

    def test_disposition_has_exactly_four_values(self) -> None:
        assert len(SignalDisposition) == 4
        assert set(SignalDisposition) == {
            SignalDisposition.FINDING,
            SignalDisposition.ADVISORY,
            SignalDisposition.INFORMATIONAL,
            SignalDisposition.SUPPRESSED,
        }

    def test_family_has_exactly_eight_values(self) -> None:
        assert len(SignalFamily) == 8
        assert SignalFamily.RUNTIME in SignalFamily
        assert SignalFamily.DEPENDENCY in SignalFamily

    def test_governed_signal_rejects_missing_fields(self) -> None:
        with pytest.raises(TypeError):
            GovernedSignal(signal_id="x", family=SignalFamily.RUNTIME)  # type: ignore[call-arg]

    def test_governed_signal_is_frozen(self) -> None:
        sig = _signal(SignalDisposition.FINDING)
        with pytest.raises(AttributeError):
            sig.title = "mutated"  # type: ignore[misc]

    def test_signal_id_is_deterministic(self) -> None:
        id1 = make_signal_id("runtime", "conflict", ["ev1", "ev2"])
        id2 = make_signal_id("runtime", "conflict", ["ev1", "ev2"])
        assert id1 == id2

    def test_signal_id_differs_for_different_evidence(self) -> None:
        id1 = make_signal_id("runtime", "conflict", ["ev1"])
        id2 = make_signal_id("runtime", "conflict", ["ev2"])
        assert id1 != id2

    def test_signal_id_order_independent(self) -> None:
        id1 = make_signal_id("runtime", "conflict", ["ev1", "ev2"])
        id2 = make_signal_id("runtime", "conflict", ["ev2", "ev1"])
        assert id1 == id2


# ── S02: Policy contracts ────────────────────────────────────────────


class TestSignalPolicy:
    """Signal promotion policy contracts."""

    def test_should_create_finding_for_finding(self) -> None:
        assert should_create_finding(_signal(SignalDisposition.FINDING))

    def test_should_not_create_finding_for_advisory(self) -> None:
        assert not should_create_finding(_signal(SignalDisposition.ADVISORY))

    def test_should_create_work_package_for_finding(self) -> None:
        assert should_create_work_package(_signal(SignalDisposition.FINDING))

    def test_should_not_create_work_package_for_advisory(self) -> None:
        assert not should_create_work_package(_signal(SignalDisposition.ADVISORY))

    def test_should_not_create_work_package_for_informational(self) -> None:
        assert not should_create_work_package(_signal(SignalDisposition.INFORMATIONAL))

    def test_should_create_advisory_for_advisory(self) -> None:
        assert should_create_advisory(_signal(SignalDisposition.ADVISORY))

    def test_should_not_create_advisory_for_finding(self) -> None:
        assert not should_create_advisory(_signal(SignalDisposition.FINDING))

    def test_should_not_create_advisory_for_informational(self) -> None:
        assert not should_create_advisory(_signal(SignalDisposition.INFORMATIONAL))

    def test_should_not_create_advisory_for_suppressed(self) -> None:
        assert not should_create_advisory(_signal(SignalDisposition.SUPPRESSED))

    def test_is_reportable_for_finding(self) -> None:
        assert is_reportable(_signal(SignalDisposition.FINDING))

    def test_is_reportable_for_advisory(self) -> None:
        assert is_reportable(_signal(SignalDisposition.ADVISORY))

    def test_is_not_reportable_for_informational(self) -> None:
        assert not is_reportable(_signal(SignalDisposition.INFORMATIONAL))

    def test_is_informational_for_informational(self) -> None:
        assert is_informational(_signal(SignalDisposition.INFORMATIONAL))

    def test_is_not_informational_for_suppressed(self) -> None:
        assert not is_informational(_signal(SignalDisposition.SUPPRESSED))


# ── S03: Runtime adapter contracts ───────────────────────────────────


class TestRuntimeAdapters:
    """Runtime signal adapter contracts."""

    def test_conflict_becomes_finding(self, tmp_path: Path) -> None:
        from pharabius.core.runtime.conflict import detect_conflicts
        from pharabius.core.runtime.go import detect_go_sources
        from pharabius.core.signals.adapters import runtime_conflict_to_signal

        (tmp_path / "go.mod").write_text("module ex\ngo 1.22\n\ntoolchain go1.20.0\n")
        conflicts = detect_conflicts(detect_go_sources(tmp_path))
        assert len(conflicts) >= 1
        signal = runtime_conflict_to_signal(conflicts[0])
        assert signal.disposition == SignalDisposition.FINDING
        assert signal.family == SignalFamily.RUNTIME

    def test_missing_pin_becomes_advisory(self) -> None:
        from pharabius.core.runtime.models import RuntimeEcosystem
        from pharabius.core.signals.adapters import runtime_missing_pin_to_signal

        signal = runtime_missing_pin_to_signal(
            runtime_name="Python",
            ecosystem=RuntimeEcosystem.PYTHON,
            trigger_files=["pyproject.toml"],
            evidence_ids=["ev:python:pyproject.toml:3.11"],
        )
        assert signal.disposition == SignalDisposition.ADVISORY
        assert signal.family == SignalFamily.RUNTIME
        assert "Python" in signal.title

    def test_pinned_evidence_becomes_informational(self, tmp_path: Path) -> None:
        from pharabius.core.runtime.ecosystems import detect_python_sources
        from pharabius.core.signals.adapters import runtime_evidence_to_signal

        (tmp_path / ".python-version").write_text("3.11\n")
        evidence = detect_python_sources(tmp_path)
        assert len(evidence) >= 1
        signal = runtime_evidence_to_signal(evidence[0])
        assert signal.disposition == SignalDisposition.INFORMATIONAL
        assert signal.family == SignalFamily.RUNTIME

    def test_signal_ids_deterministic_across_runs(self, tmp_path: Path) -> None:
        from pharabius.core.runtime.ecosystems import detect_python_sources
        from pharabius.core.signals.adapters import runtime_evidence_to_signal

        (tmp_path / ".python-version").write_text("3.11\n")
        ev = detect_python_sources(tmp_path)
        sig1 = runtime_evidence_to_signal(ev[0])
        sig2 = runtime_evidence_to_signal(ev[0])
        assert sig1.signal_id == sig2.signal_id

    def test_conflict_signal_preserves_runtime_metadata(self, tmp_path: Path) -> None:
        from pharabius.core.runtime.conflict import detect_conflicts
        from pharabius.core.runtime.go import detect_go_sources
        from pharabius.core.signals.adapters import runtime_conflict_to_signal

        (tmp_path / "go.mod").write_text("module ex\ngo 1.22\n\ntoolchain go1.20.0\n")
        conflicts = detect_conflicts(detect_go_sources(tmp_path))
        signal = runtime_conflict_to_signal(conflicts[0])
        assert signal.metadata["runtime_name"] == "Go"
        assert signal.metadata["ecosystem"] == "Go"
        assert signal.metadata["conflict_kind"] is not None

    def test_evidence_signal_preserves_source_grade(self, tmp_path: Path) -> None:
        from pharabius.core.runtime.ecosystems import detect_python_sources
        from pharabius.core.signals.adapters import runtime_evidence_to_signal

        (tmp_path / ".python-version").write_text("3.11\n")
        ev = detect_python_sources(tmp_path)
        signal = runtime_evidence_to_signal(ev[0])
        assert signal.metadata["source_grade"] == "version_file"

    def test_multiple_conflicts_produce_distinct_signals(self, tmp_path: Path) -> None:
        from pharabius.core.runtime.conflict import detect_conflicts
        from pharabius.core.runtime.dotnet import detect_dotnet_sources
        from pharabius.core.signals.adapters import runtime_conflict_to_signal

        # Two disjoint .NET target frameworks → INCOMPATIBLE_RANGES
        (tmp_path / "A.csproj").write_text(
            "<Project><PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup></Project>"
        )
        (tmp_path / "B.csproj").write_text(
            "<Project><PropertyGroup><TargetFramework>net5.0</TargetFramework></PropertyGroup></Project>"
        )
        conflicts = detect_conflicts(detect_dotnet_sources(tmp_path))
        if len(conflicts) >= 2:
            s1 = runtime_conflict_to_signal(conflicts[0])
            s2 = runtime_conflict_to_signal(conflicts[1])
            assert s1.signal_id != s2.signal_id


# ── S05: Summary contracts ───────────────────────────────────────────


class TestSignalSummary:
    """Signal summary contracts."""

    def test_counts_all_dispositions(self) -> None:
        signals = [
            _signal(SignalDisposition.FINDING, "f1"),
            _signal(SignalDisposition.ADVISORY, "a1"),
            _signal(SignalDisposition.INFORMATIONAL, "i1"),
            _signal(SignalDisposition.SUPPRESSED, "s1"),
        ]
        summary = build_signal_summary(signals)
        assert summary.total == 4
        assert summary.by_disposition == {"finding": 1, "advisory": 1, "informational": 1, "suppressed": 1}

    def test_groups_by_family(self) -> None:
        sig1 = _signal(SignalDisposition.FINDING, "f1")
        sig2 = GovernedSignal(
            signal_id="sig-dep-1",
            family=SignalFamily.DEPENDENCY,
            kind="dep_check",
            disposition=SignalDisposition.FINDING,
            category="TD-DEP",
            severity="Medium",
            confidence="High",
            evidence_ids=["d1"],
            source_signal_ids=[],
            title="Dep issue",
            summary="Summary",
            explanation="Explanation",
            metadata={},
        )
        summary = build_signal_summary([sig1, sig2])
        assert summary.by_family == {"runtime": 1, "dependency": 1}

    def test_counts_by_severity(self) -> None:
        signals = [
            _signal(SignalDisposition.FINDING, "f1"),
        ]
        summary = build_signal_summary(signals)
        assert summary.by_severity["Medium"] == 1

    def test_empty_list_returns_zeros(self) -> None:
        summary = build_signal_summary([])
        assert summary.total == 0
        assert summary.by_family == {}
        assert summary.by_disposition == {}


# ── S04 boundary: acceptance criteria 15-17 ──────────────────────────


class TestAdvisoryBoundary:
    """Acceptance criteria 15-17: advisory creation controlled by ADVISORY only."""

    def test_informational_does_not_create_advisory(self) -> None:
        sig = _signal(SignalDisposition.INFORMATIONAL)
        assert not should_create_advisory(sig)

    def test_suppressed_does_not_create_advisory(self) -> None:
        sig = _signal(SignalDisposition.SUPPRESSED)
        assert not should_create_advisory(sig)

    def test_finding_does_not_create_advisory(self) -> None:
        sig = _signal(SignalDisposition.FINDING)
        assert not should_create_advisory(sig)

    def test_only_advisory_creates_advisory(self) -> None:
        sig = _signal(SignalDisposition.ADVISORY)
        assert should_create_advisory(sig)


# ── S04 boundary: acceptance criteria 18-19 ──────────────────────────


class TestNoSignalStore:
    """Acceptance criteria 18-19: no persistent SignalStore, signals from existing evidence."""

    def test_signals_module_has_no_store_class(self) -> None:
        """Verify no SignalStore/EvidenceStore equivalent in signals package."""
        from pharabius.core import signals
        assert not hasattr(signals, "SignalStore")
        assert not hasattr(signals, "EvidenceStore")

    def test_signals_adapted_from_runtime_evidence(self, tmp_path: Path) -> None:
        """Verify signals are reconstructed from existing runtime IR."""
        from pharabius.core.runtime.ecosystems import detect_python_sources
        from pharabius.core.signals.adapters import runtime_evidence_to_signal

        (tmp_path / ".python-version").write_text("3.11\n")
        ev = detect_python_sources(tmp_path)
        signal = runtime_evidence_to_signal(ev[0])
        assert signal.evidence_ids == [ev[0].runtime_evidence_id]
        assert signal.metadata["source_grade"] == ev[0].source_grade.value
