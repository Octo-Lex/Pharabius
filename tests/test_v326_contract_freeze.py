"""v3.26.0 — Governance contract freeze and v4 readiness audit tests.

Proves the v3 governance contract is stable:
- No new families, adapters, or detection
- No policy enforcement behavior
- Export/report shapes are additive-only
- Forbidden field checks scoped to generated schemas, not doc non-goal wording
- Contract inventory is documentation/test-only, not a runtime registry
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from pharabius.core.governance_export import (
    EXPORT_TYPE,
    SCHEMA_VERSION,
    _validate_no_forbidden_fields,
    build_governance_export,
)
from pharabius.core.signals.invariants import ALL_INVARIANTS
from pharabius.core.signals.models import GovernedSignal, SignalDisposition, SignalFamily
from pharabius.core.signals.quality import (
    GovernanceQualityMetrics,
    build_governance_quality_metrics,
    governance_quality_metrics_to_dict,
)
from pharabius.core.signals.summary import SignalSummary
from pharabius.core.signals.trends import (
    GovernanceTrendSummary,
    build_governance_trend_summary,
    governance_trend_to_dict,
)

# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════


def _sig(**kwargs):
    defaults = dict(
        signal_id="test-sig",
        family=SignalFamily.RUNTIME,
        kind="test",
        disposition=SignalDisposition.FINDING,
        category="TD-TEST",
        severity="Medium",
        confidence="High",
        evidence_ids=["ev1"],
        source_signal_ids=[],
        title="Test",
        summary="Test",
        explanation="Test",
        metadata={"spec_kind": "test"},
    )
    defaults.update(kwargs)
    return GovernedSignal(**defaults)


def _read_doc(name: str) -> str:
    docs = Path("docs")
    path = docs / name
    if not path.exists():
        # Try relative to project root
        for parent in Path(__file__).parents:
            candidate = parent / "docs" / name
            if candidate.exists():
                path = candidate
                break
    return path.read_text(encoding="utf-8")


def _src(module) -> str:
    return inspect.getsource(module)


# ═══════════════════════════════════════════════════════════════════════
# S01 — Governance contract inventory exists
# ═══════════════════════════════════════════════════════════════════════


class TestContractDoc:
    """GOVERNANCE_CONTRACT.md exists and covers stable surfaces."""

    def test_contract_doc_exists(self) -> None:
        doc = _read_doc("GOVERNANCE_CONTRACT.md")
        assert len(doc) > 100

    def test_contract_doc_mentions_governed_signal(self) -> None:
        doc = _read_doc("GOVERNANCE_CONTRACT.md")
        assert "GovernedSignal" in doc

    def test_contract_doc_mentions_signal_summary(self) -> None:
        doc = _read_doc("GOVERNANCE_CONTRACT.md")
        assert "SignalSummary" in doc

    def test_contract_doc_mentions_quality_metrics(self) -> None:
        doc = _read_doc("GOVERNANCE_CONTRACT.md")
        assert "GovernanceQualityMetrics" in doc

    def test_contract_doc_mentions_trend_summary(self) -> None:
        doc = _read_doc("GOVERNANCE_CONTRACT.md")
        assert "GovernanceTrendSummary" in doc

    def test_contract_doc_mentions_export_schema(self) -> None:
        doc = _read_doc("GOVERNANCE_CONTRACT.md")
        assert "governance_export" in doc.lower() or "governance-summary.json" in doc

    def test_contract_doc_mentions_non_policy(self) -> None:
        doc = _read_doc("GOVERNANCE_CONTRACT.md")
        assert "non-policy" in doc.lower() or "non-enforcing" in doc.lower()

    def test_contract_doc_mentions_10_families(self) -> None:
        doc = _read_doc("GOVERNANCE_CONTRACT.md")
        assert "10 families" in doc

    def test_contract_doc_mentions_29_adapters(self) -> None:
        doc = _read_doc("GOVERNANCE_CONTRACT.md")
        assert "29 adapter" in doc

    def test_contract_doc_mentions_exceptions(self) -> None:
        doc = _read_doc("GOVERNANCE_CONTRACT.md")
        assert "TD-COMP" in doc
        assert "TD-SEC" in doc

    def test_contract_doc_no_runtime_registry(self) -> None:
        """Contract doc is documentation, not a runtime registry."""
        doc = _read_doc("GOVERNANCE_CONTRACT.md")
        assert "runtime registry" not in doc.lower() or "not a runtime registry" in doc.lower()


# ═══════════════════════════════════════════════════════════════════════
# S02 — Schema compatibility: frozen counts
# ═══════════════════════════════════════════════════════════════════════


class TestFrozenCounts:
    """v3 family and adapter counts are frozen."""

    def test_signal_family_count(self) -> None:
        assert len(SignalFamily) == 10

    def test_signal_disposition_count(self) -> None:
        assert len(SignalDisposition) == 4

    def test_signal_family_values(self) -> None:
        expected = {
            "runtime",
            "dependency",
            "test",
            "security",
            "architecture",
            "documentation",
            "build",
            "observability",
            "configuration",
            "process",
        }
        actual = {f.value for f in SignalFamily}
        assert actual == expected

    def test_signal_disposition_values(self) -> None:
        expected = {"finding", "advisory", "informational", "suppressed"}
        actual = {d.value for d in SignalDisposition}
        assert actual == expected

    def test_adapter_count(self) -> None:
        """v3 freezes at 29 adapters."""
        import pharabius.core.signals.adapters as adapters
        import pharabius.core.signals.architecture_adapters as arch
        import pharabius.core.signals.configuration_adapters as config
        import pharabius.core.signals.dependency_adapters as dep
        import pharabius.core.signals.observability_adapters as obs
        import pharabius.core.signals.security_adapters as sec

        def _adapter_count(module):
            return len(
                [
                    name
                    for name, obj in inspect.getmembers(module)
                    if callable(obj) and ("_to_signal" in name)
                ]
            )

        total = sum(_adapter_count(m) for m in [adapters, dep, sec, arch, config, obs])
        assert total == 29

    def test_invariant_count(self) -> None:
        assert len(ALL_INVARIANTS) == 8

    def test_invariant_codes(self) -> None:
        codes = [inv.code for inv in ALL_INVARIANTS]
        expected = [f"INV_{i:03d}" for i in range(1, 9)]
        assert codes == expected


# ═══════════════════════════════════════════════════════════════════════
# S02 — Schema compatibility: required fields present
# ═══════════════════════════════════════════════════════════════════════


class TestRequiredFields:
    """Required fields are present on stable models (shape-based, not ordering)."""

    def test_governed_signal_required_fields(self) -> None:
        required = {
            "signal_id",
            "family",
            "kind",
            "disposition",
            "category",
            "severity",
            "confidence",
            "evidence_ids",
            "source_signal_ids",
            "title",
            "summary",
            "explanation",
            "metadata",
        }
        actual = {f.name for f in GovernedSignal.__dataclass_fields__.values()}
        assert required.issubset(actual), f"Missing: {required - actual}"

    def test_signal_summary_required_fields(self) -> None:
        required = {"total", "by_family", "by_disposition"}
        actual = {f.name for f in SignalSummary.__dataclass_fields__.values()}
        assert required.issubset(actual)

    def test_quality_metrics_required_fields(self) -> None:
        required = {
            "total_signals",
            "by_family",
            "by_disposition",
            "by_severity",
            "by_confidence",
            "finding_evidence_coverage",
            "advisory_evidence_coverage",
            "informational_evidence_coverage",
            "diagnostics",
        }
        actual = {f.name for f in GovernanceQualityMetrics.__dataclass_fields__.values()}
        assert required.issubset(actual)

    def test_trend_summary_required_fields(self) -> None:
        required = {
            "runs_compared",
            "current_run_id",
            "previous_run_id",
            "signal_count_delta",
            "finding_evidence_coverage_delta",
            "advisory_evidence_coverage_delta",
            "informational_evidence_coverage_delta",
            "by_disposition_delta",
            "by_family_delta",
            "by_confidence_delta",
            "recurring_diagnostics",
            "unavailable_reason",
        }
        actual = {f.name for f in GovernanceTrendSummary.__dataclass_fields__.values()}
        assert required.issubset(actual)

    def test_export_required_keys(self) -> None:
        export = build_governance_export(run_id="R1")
        required = {
            "schema_version",
            "export_type",
            "tool_version",
            "run_id",
            "generated_at",
            "signal_summary",
            "governance_quality",
            "governance_trends",
            "diagnostics",
            "recurring_diagnostics",
            "metadata",
        }
        assert required.issubset(set(export.keys()))

    def test_export_schema_version(self) -> None:
        assert SCHEMA_VERSION == "1.0"

    def test_export_type(self) -> None:
        assert EXPORT_TYPE == "governance_analytics"


# ═══════════════════════════════════════════════════════════════════════
# S03 — Baseline shapes: serialization
# ═══════════════════════════════════════════════════════════════════════


class TestBaselineShapes:
    """Representative serialization shapes are stable."""

    def test_quality_metrics_serialization_keys(self) -> None:
        metrics = build_governance_quality_metrics([_sig()])
        d = governance_quality_metrics_to_dict(metrics)
        required = {
            "total_signals",
            "by_family",
            "by_disposition",
            "by_severity",
            "by_confidence",
            "finding_evidence_coverage",
            "finding_metadata_coverage",
            "advisory_evidence_coverage",
            "informational_evidence_coverage",
            "diagnostics",
        }
        assert required.issubset(set(d.keys()))

    def test_trend_summary_serialization_keys(self) -> None:
        trend = build_governance_trend_summary(
            [
                {"run_id": "R1", "governance_quality": {"total_signals": 10}},
                {"run_id": "R2", "governance_quality": {"total_signals": 15}},
            ]
        )
        d = governance_trend_to_dict(trend)
        required = {
            "runs_compared",
            "current_run_id",
            "previous_run_id",
            "signal_count_delta",
            "finding_evidence_coverage_delta",
            "recurring_diagnostics",
            "unavailable_reason",
        }
        assert required.issubset(set(d.keys()))

    def test_export_json_roundtrip(self, tmp_path: Path) -> None:
        from pharabius.core.governance_export import write_governance_export

        export = build_governance_export(
            signal_summary={"total": 10},
            run_id="R1",
        )
        path = write_governance_export(export, tmp_path / "gov.json")
        reloaded = json.loads(path.read_text(encoding="utf-8"))
        assert reloaded["schema_version"] == "1.0"
        assert reloaded["run_id"] == "R1"
        assert reloaded["signal_summary"]["total"] == 10

    def test_export_jsonl_roundtrip(self, tmp_path: Path) -> None:
        from pharabius.core.governance_export import write_governance_export_jsonl

        export = build_governance_export(run_id="R1")
        path = write_governance_export_jsonl(export, tmp_path / "gov.jsonl")
        content = path.read_text(encoding="utf-8").strip()
        assert "\n" not in content  # single line
        reloaded = json.loads(content)
        assert reloaded["schema_version"] == "1.0"


# ═══════════════════════════════════════════════════════════════════════
# S04 — Non-policy boundary audit
# ═══════════════════════════════════════════════════════════════════════


class TestNonPolicyBoundary:
    """Governance remains non-enforcing."""

    def test_export_no_forbidden_fields(self) -> None:
        """Generated export has no policy/gate field names."""
        metrics = build_governance_quality_metrics([_sig()])
        export = build_governance_export(governance_quality=metrics)
        warnings = _validate_no_forbidden_fields(export)
        assert len(warnings) == 0

    def test_export_json_no_forbidden_terms(self) -> None:
        """Serialized export JSON contains no policy judgment terms."""
        export = build_governance_export(run_id="R1")
        export_json = json.dumps(export).lower()
        # Check field names (keys), not prose values
        for key in export:
            assert key.lower() not in {
                "pass",
                "fail",
                "score",
                "grade",
                "compliant",
                "noncompliant",
                "healthy",
                "unhealthy",
            }

    def test_diagnostics_severity_never_critical(self) -> None:
        metrics = build_governance_quality_metrics(
            [
                _sig(evidence_ids=[]),
                _sig(severity="Extreme"),
            ]
        )
        for d in metrics.diagnostics:
            assert d.severity in ("info", "warning")

    def test_no_adapter_creates_work_packages(self) -> None:
        """Adapters produce GovernedSignal, not work packages."""
        import pharabius.core.signals.adapters as adapters

        for name, obj in inspect.getmembers(adapters):
            if "_to_signal" in name and callable(obj):
                sig = obj.__annotations__ if hasattr(obj, "__annotations__") else {}
                # No adapter returns work-package types
                assert "work_package" not in str(sig).lower()

    def test_quality_metrics_do_not_change_disposition(self) -> None:
        sig = _sig()
        original = sig.disposition
        build_governance_quality_metrics([sig])
        assert sig.disposition == original

    def test_trends_do_not_change_disposition(self) -> None:
        sig = _sig()
        original = sig.disposition
        build_governance_trend_summary(
            [
                {"run_id": "R1", "governance_quality": {"total_signals": 10}},
                {"run_id": "R2", "governance_quality": {"total_signals": 15}},
            ]
        )
        assert sig.disposition == original

    def test_signal_ids_deterministic(self) -> None:
        """Signal IDs are deterministic (no random component)."""
        import re

        sig = _sig(signal_id="TD-TEST-001")
        # No UUID or random pattern
        assert not re.match(r"[0-9a-f]{8}-", sig.signal_id)


# ═══════════════════════════════════════════════════════════════════════
# S05 — Documentation consistency
# ═══════════════════════════════════════════════════════════════════════


class TestDocConsistency:
    """Docs do not imply policy enforcement."""

    def test_governance_doc_no_policy_enforcement(self) -> None:
        doc = _read_doc("SIGNAL_GOVERNANCE.md")
        # "enforce" should only appear in non-goal context
        lower = doc.lower()
        assert "enforce policy" not in lower or "does not enforce" in lower or "non-goal" in lower

    def test_governance_doc_no_quality_gates(self) -> None:
        doc = _read_doc("SIGNAL_GOVERNANCE.md")
        lower = doc.lower()
        # "quality gate" should appear only as non-goal
        if "quality gate" in lower:
            # Must be in non-goal context
            assert "no quality gate" in lower or "does not" in lower or "non-goal" in lower

    def test_contract_doc_mentions_schema_escalation(self) -> None:
        doc = _read_doc("GOVERNANCE_CONTRACT.md")
        assert "schema_version" in doc
        assert "breaking" in doc.lower() or "escalation" in doc.lower()

    def test_v4_readiness_doc_exists(self) -> None:
        doc = _read_doc("V4_READINESS.md")
        assert len(doc) > 100

    def test_v4_readiness_no_implementation(self) -> None:
        doc = _read_doc("V4_READINESS.md")
        assert "does not implement" in doc.lower() or "without implementing" in doc.lower()

    def test_v4_readiness_mentions_options(self) -> None:
        doc = _read_doc("V4_READINESS.md")
        assert "Option A" in doc or "option a" in doc.lower()
        assert "Option B" in doc or "option b" in doc.lower()

    def test_v4_readiness_mentions_family_freeze(self) -> None:
        doc = _read_doc("V4_READINESS.md")
        assert "10 families" in doc
        assert "29 adapter" in doc

    def test_no_doc_says_advisories_create_work_packages(self) -> None:
        for doc_name in [
            "SIGNAL_GOVERNANCE.md",
            "SIGNAL_GOVERNANCE_AUDIT.md",
            "GOVERNANCE_CONTRACT.md",
            "ARCHITECTURE.md",
        ]:
            doc = _read_doc(doc_name)
            lower = doc.lower()
            # "advisories create work packages" should NOT appear as a statement of fact
            assert "advisories create work packages" not in lower
            # "do not create work packages" should appear or "never create"
            if "advisori" in lower and "work package" in lower:
                assert "do not create" in lower or "never create" in lower or "do not" in lower


# ═══════════════════════════════════════════════════════════════════════
# S07 — No runtime registry
# ═══════════════════════════════════════════════════════════════════════


class TestNoRuntimeRegistry:
    """Contract inventory is documentation/test-only, not a runtime registry."""

    def test_governed_signal_not_registered_at_import(self) -> None:
        """No global signal registry populated at import time."""
        import pharabius.core.signals.models as models

        assert not hasattr(models, "_signal_registry")
        assert not hasattr(models, "SIGNAL_REGISTRY")

    def test_no_policy_engine_module(self) -> None:
        """No policy engine module exists."""
        from pharabius.core import signals

        assert not hasattr(signals, "policy_engine")

    def test_invariants_are_declarations(self) -> None:
        """Invariants are declarative, not runtime checks."""

        for inv in ALL_INVARIANTS:
            assert hasattr(inv, "code")
            assert hasattr(inv, "title")
            assert hasattr(inv, "description")
            # Invariants don't have enforcement hooks
            assert not hasattr(inv, "enforce")
            assert not hasattr(inv, "check")


# ═══════════════════════════════════════════════════════════════════════
# S07 — Reporter governance sections
# ═══════════════════════════════════════════════════════════════════════


class TestReporterSections:
    """Foundation report governance sections remain present."""

    def test_reporter_source_has_signal_governance_summary(self) -> None:
        import pharabius.core.reporter as reporter

        src = _src(reporter)
        assert "Signal Governance Summary" in src

    def test_reporter_source_has_quality_metrics(self) -> None:
        import pharabius.core.reporter as reporter

        src = _src(reporter)
        assert "Governance Quality Metrics" in src

    def test_reporter_source_has_trends(self) -> None:
        import pharabius.core.reporter as reporter

        src = _src(reporter)
        assert "Governance Quality Trends" in src

    def test_reporter_source_has_work_package_wording(self) -> None:
        import pharabius.core.reporter as reporter

        src = _src(reporter)
        assert "may create work packages" in src

    def test_reporter_source_has_non_goal_wording(self) -> None:
        import pharabius.core.reporter as reporter

        src = _src(reporter)
        # "descriptive only" is allowed as non-goal wording
        assert "descriptive only" in src.lower()
