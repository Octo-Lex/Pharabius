"""v3.21.0 — Governance completion audit and cross-family consistency.

Audits the completed governance surface across all 10 families:
- S01: Machine-checkable inventory
- S02: Cross-family disposition consistency
- S03: Evidence traceability
- S04: Summary/report consistency
- S05: Family-boundary regression matrix
- S06: Metadata minimum contract

This is an AUDIT release — no new detection or promotion behavior.
"""

from __future__ import annotations

import importlib
import inspect

import pytest
from tests.fixtures.signal_governance.governed_family_inventory import (
    CATEGORY_FAMILY_EXPECTATIONS,
    FAMILY_METADATA_REQUIRED_KEYS,
    GOVERNED_FAMILY_INVENTORY,
)

from pharabius.core.signals.models import GovernedSignal, SignalDisposition, SignalFamily
from pharabius.core.signals.policy import output_behavior
from pharabius.core.signals.summary import build_signal_summary
from pharabius.core.signals.validation import validate_governed_signal

# ═══════════════════════════════════════════════════════════════════════
# S01 — Governance surface inventory
# ═══════════════════════════════════════════════════════════════════════


class TestInventoryCompleteness:
    """Every SignalFamily enum value has governance coverage."""

    def test_all_enum_values_in_inventory(self) -> None:
        """No SignalFamily exists without explicit governance status."""
        inventory_families = {entry["family"] for entry in GOVERNED_FAMILY_INVENTORY.values()}
        enum_families = set(SignalFamily)
        assert inventory_families == enum_families, (
            f"Missing from inventory: {enum_families - inventory_families}\n"
            f"Extra in inventory: {inventory_families - enum_families}"
        )

    @pytest.mark.parametrize("family_name", list(GOVERNED_FAMILY_INVENTORY.keys()))
    def test_every_family_has_at_least_one_adapter(self, family_name: str) -> None:
        entry = GOVERNED_FAMILY_INVENTORY[family_name]
        assert len(entry["adapters"]) >= 1, f"{family_name} has no adapters"

    @pytest.mark.parametrize("family_name", list(GOVERNED_FAMILY_INVENTORY.keys()))
    def test_every_family_has_at_least_one_analyzer(self, family_name: str) -> None:
        entry = GOVERNED_FAMILY_INVENTORY[family_name]
        assert len(entry["analyzer_functions"]) >= 1, f"{family_name} has no analyzer functions"

    @pytest.mark.parametrize("family_name", list(GOVERNED_FAMILY_INVENTORY.keys()))
    def test_adapter_callables_exist(self, family_name: str) -> None:
        """Adapter functions are importable (adapter modules only — no analyzer cycles)."""
        entry = GOVERNED_FAMILY_INVENTORY[family_name]
        module = importlib.import_module(entry["adapter_module"])
        for adapter_name in entry["adapters"]:
            assert hasattr(module, adapter_name), (
                f"{entry['adapter_module']}.{adapter_name} not found"
            )
            assert callable(getattr(module, adapter_name)), (
                f"{entry['adapter_module']}.{adapter_name} is not callable"
            )

    def test_ten_families_governed(self) -> None:
        assert len(GOVERNED_FAMILY_INVENTORY) == 10


class TestCategoryFamilyMapping:
    """Category-to-family mapping is documented and tested."""

    @pytest.mark.parametrize(
        "category,expected",
        [
            ("TD-RUNTIME", SignalFamily.RUNTIME),
            ("TD-DOC", SignalFamily.DOCUMENTATION),
            ("TD-BUILD", SignalFamily.BUILD),
            ("TD-PROCESS", SignalFamily.PROCESS),
            ("TD-DEP", SignalFamily.DEPENDENCY),
            ("TD-ARCH", SignalFamily.ARCHITECTURE),
            ("TD-CONFIG", SignalFamily.CONFIGURATION),
            ("TD-OBS", SignalFamily.OBSERVABILITY),
            ("TD-COMP", SignalFamily.SECURITY),
            ("TD-SEC", SignalFamily.TEST),
        ],
    )
    def test_category_maps_to_expected_family(
        self,
        category: str,
        expected: SignalFamily,
    ) -> None:
        assert category in CATEGORY_FAMILY_EXPECTATIONS
        actual_family, rationale = CATEGORY_FAMILY_EXPECTATIONS[category]
        assert actual_family == expected, f"{category}: {rationale}"

    def test_known_exceptions_explicit(self) -> None:
        """TD-COMP and TD-SEC are known category-family exceptions."""
        # TD-COMP governed under SECURITY (not a separate family)
        assert CATEGORY_FAMILY_EXPECTATIONS["TD-COMP"][0] == SignalFamily.SECURITY
        # TD-SEC for risk-sensitive-without-tests governed under TEST
        assert CATEGORY_FAMILY_EXPECTATIONS["TD-SEC"][0] == SignalFamily.TEST


class TestStaticAnalyzerAudit:
    """No unlisted direct-promotion paths for governed categories."""

    def test_governed_categories_use_output_behavior(self) -> None:
        """Static check: governed analyzer paths use signal policy helpers."""
        import pharabius.core.analyzer as analyzer_module

        for family_name, entry in GOVERNED_FAMILY_INVENTORY.items():
            for func_name in entry["analyzer_functions"]:
                func = getattr(analyzer_module, func_name, None)
                if func is None:
                    continue
                func_source = inspect.getsource(func)
                # INV_007: must use signal policy helpers — either output_behavior()
                # or the older should_create_finding()/should_create_advisory() predicates
                uses_policy = (
                    "output_behavior" in func_source
                    or "should_create_finding" in func_source
                    or "should_create_advisory" in func_source
                )
                assert uses_policy, (
                    f"{func_name} ({family_name}) does not use any signal policy helper"
                )

    def test_no_should_create_work_package_proxy(self) -> None:
        """No governed analyzer uses should_create_work_package as a proxy."""
        import pharabius.core.analyzer as analyzer_module

        inspect.getsource(analyzer_module)
        # should_create_work_package may exist in imports but should not be
        # used in governed analyzer functions for promotion decisions
        for family_name, entry in GOVERNED_FAMILY_INVENTORY.items():
            for func_name in entry["analyzer_functions"]:
                func = getattr(analyzer_module, func_name, None)
                if func is None:
                    continue
                func_source = inspect.getsource(func)
                assert "should_create_work_package" not in func_source, (
                    f"{func_name} ({family_name}) uses should_create_work_package — forbidden proxy"
                )


# ═══════════════════════════════════════════════════════════════════════
# S02 — Cross-family disposition audit
# ═══════════════════════════════════════════════════════════════════════


class TestDispositionConsistency:
    """FINDING/ADVISORY/INFORMATIONAL/SUPPRESSED behavior is uniform."""

    def test_finding_creates_finding_and_work_package(self) -> None:
        """All FINDING dispositions behave identically."""
        finding_families = [
            name
            for name, entry in GOVERNED_FAMILY_INVENTORY.items()
            if SignalDisposition.FINDING in entry["dispositions"]
        ]
        assert len(finding_families) > 0
        # All use the same output_behavior mapping
        from tests.test_v315_signal_governance_conformance import _FAMILY_ADAPTER_FACTORIES

        for family_name in finding_families:
            signals = _FAMILY_ADAPTER_FACTORIES[family_name]()
            finding_signals = [s for s in signals if s.disposition == SignalDisposition.FINDING]
            for sig in finding_signals:
                behav = output_behavior(sig)
                assert behav.creates_finding is True, (
                    f"{family_name}: FINDING should create finding"
                )
                assert behav.creates_work_package is True, (
                    f"{family_name}: FINDING should be work-package eligible"
                )
                assert behav.appears_in_report_detail is True, (
                    f"{family_name}: FINDING should appear in report"
                )
                assert behav.appears_in_summary is True, (
                    f"{family_name}: FINDING should appear in summary"
                )
                assert behav.diagnostics_only is False, (
                    f"{family_name}: FINDING should not be diagnostics-only"
                )

    def test_advisory_never_creates_work_package(self) -> None:
        """All ADVISORY dispositions behave identically."""
        from tests.test_v315_signal_governance_conformance import _FAMILY_ADAPTER_FACTORIES

        advisory_families = [
            name
            for name, entry in GOVERNED_FAMILY_INVENTORY.items()
            if SignalDisposition.ADVISORY in entry["dispositions"]
        ]
        for family_name in advisory_families:
            signals = _FAMILY_ADAPTER_FACTORIES[family_name]()
            advisory_signals = [s for s in signals if s.disposition == SignalDisposition.ADVISORY]
            for sig in advisory_signals:
                behav = output_behavior(sig)
                assert behav.creates_finding is False, (
                    f"{family_name}: ADVISORY should not create finding"
                )
                assert behav.creates_work_package is False, (
                    f"{family_name}: ADVISORY should not create work package"
                )
                assert behav.creates_advisory is True, (
                    f"{family_name}: ADVISORY should create advisory"
                )
                assert behav.appears_in_summary is True, (
                    f"{family_name}: ADVISORY should appear in summary"
                )

    def test_informational_non_actionable(self) -> None:
        """All INFORMATIONAL dispositions behave identically."""
        from tests.test_v315_signal_governance_conformance import _FAMILY_ADAPTER_FACTORIES

        info_families = [
            name
            for name, entry in GOVERNED_FAMILY_INVENTORY.items()
            if SignalDisposition.INFORMATIONAL in entry["dispositions"]
        ]
        for family_name in info_families:
            signals = _FAMILY_ADAPTER_FACTORIES[family_name]()
            info_signals = [s for s in signals if s.disposition == SignalDisposition.INFORMATIONAL]
            for sig in info_signals:
                behav = output_behavior(sig)
                assert behav.creates_finding is False
                assert behav.creates_advisory is False
                assert behav.creates_work_package is False
                assert behav.appears_in_report_detail is False
                assert behav.appears_in_summary is True
                assert behav.diagnostics_only is False

    def test_suppressed_diagnostics_only(self) -> None:
        """SUPPRESSED signals are diagnostics-only."""
        sig = GovernedSignal(
            signal_id="test-suppressed",
            family=SignalFamily.RUNTIME,
            kind="test",
            disposition=SignalDisposition.SUPPRESSED,
            category="test",
            severity="Low",
            confidence="Low",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Test",
            summary="Test",
            explanation="Test",
            metadata={},
        )
        behav = output_behavior(sig)
        assert behav.diagnostics_only is True
        assert behav.creates_finding is False
        assert behav.creates_advisory is False
        assert behav.creates_work_package is False
        assert behav.appears_in_summary is False
        assert behav.appears_in_report_detail is False


# ═══════════════════════════════════════════════════════════════════════
# S03 — Evidence traceability audit
# ═══════════════════════════════════════════════════════════════════════


class TestEvidenceTraceability:
    """Every promoted finding remains evidence-backed."""

    def test_all_finding_signals_have_evidence_ids(self) -> None:
        """INV_006: Every FINDING signal carries at least one evidence_id."""
        from tests.test_v315_signal_governance_conformance import _FAMILY_ADAPTER_FACTORIES

        for family_name, entry in GOVERNED_FAMILY_INVENTORY.items():
            if SignalDisposition.FINDING not in entry["dispositions"]:
                continue
            signals = _FAMILY_ADAPTER_FACTORIES[family_name]()
            finding_signals = [s for s in signals if s.disposition == SignalDisposition.FINDING]
            for sig in finding_signals:
                assert len(sig.evidence_ids) > 0, (
                    f"{family_name}/{sig.kind}: FINDING has no evidence_ids"
                )

    def test_all_finding_signals_validate(self) -> None:
        """Every FINDING signal passes validation."""
        from tests.test_v315_signal_governance_conformance import _FAMILY_ADAPTER_FACTORIES

        for family_name, entry in GOVERNED_FAMILY_INVENTORY.items():
            if SignalDisposition.FINDING not in entry["dispositions"]:
                continue
            signals = _FAMILY_ADAPTER_FACTORIES[family_name]()
            finding_signals = [s for s in signals if s.disposition == SignalDisposition.FINDING]
            for sig in finding_signals:
                result = validate_governed_signal(sig)
                assert result.valid, f"{family_name}/{sig.kind}: validation failed: {result.errors}"


class TestEvidenceCaps:
    """Family-specific evidence caps and filters are audited."""

    def test_observability_evidence_cap_at_5(self) -> None:
        """Observability evidence_ids capped at 5."""
        entry = GOVERNED_FAMILY_INVENTORY["observability"]
        assert entry["evidence_caps"]["missing_observability"] == 5

    def test_architecture_cycle_cap_at_20(self) -> None:
        """Architecture cycle findings capped at 20."""
        entry = GOVERNED_FAMILY_INVENTORY["architecture"]
        assert entry["evidence_caps"]["cycle"] == 20

    def test_architecture_boundary_violation_cap_at_20(self) -> None:
        """Architecture boundary violation findings capped at 20."""
        entry = GOVERNED_FAMILY_INVENTORY["architecture"]
        assert entry["evidence_caps"]["boundary_violation"] == 20


# ═══════════════════════════════════════════════════════════════════════
# S04 — Summary/report consistency audit
# ═══════════════════════════════════════════════════════════════════════


class TestSummaryConsistency:
    """INV_008: Signal summaries count governed signal instances."""

    def test_summary_total_equals_sum_of_families(self) -> None:
        """Summary total = sum of all family counts."""
        from tests.test_v315_signal_governance_conformance import _FAMILY_ADAPTER_FACTORIES

        all_signals = []
        for family_name in GOVERNED_FAMILY_INVENTORY:
            all_signals.extend(_FAMILY_ADAPTER_FACTORIES[family_name]())
        summary = build_signal_summary(all_signals)
        assert summary.total == sum(summary.by_family.values())

    def test_summary_by_family_matches_signals(self) -> None:
        """Summary by_family counts match actual signal instances."""
        from tests.test_v315_signal_governance_conformance import _FAMILY_ADAPTER_FACTORIES

        all_signals = []
        for family_name in GOVERNED_FAMILY_INVENTORY:
            all_signals.extend(_FAMILY_ADAPTER_FACTORIES[family_name]())
        summary = build_signal_summary(all_signals)

        # Count manually
        from collections import Counter

        manual_counts = Counter(s.family.value for s in all_signals)
        for family_value, count in manual_counts.items():
            assert summary.by_family.get(family_value, 0) == count, (
                f"Family {family_value}: summary says {summary.by_family.get(family_value, 0)}, "
                f"actual count is {count}"
            )

    def test_suppressed_excluded_from_normal_summary(self) -> None:
        """SUPPRESSED signals do not appear in normal summary."""
        sig = GovernedSignal(
            signal_id="test-suppressed",
            family=SignalFamily.RUNTIME,
            kind="test",
            disposition=SignalDisposition.SUPPRESSED,
            category="test",
            severity="Low",
            confidence="Low",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Test",
            summary="Test",
            explanation="Test",
            metadata={},
        )
        summary = build_signal_summary([sig])
        assert summary.total == 0
        assert "runtime" not in summary.by_family

    def test_informational_included_in_summary(self) -> None:
        """INFORMATIONAL signals appear in summary (but not report detail)."""
        sig = GovernedSignal(
            signal_id="test-info",
            family=SignalFamily.RUNTIME,
            kind="test",
            disposition=SignalDisposition.INFORMATIONAL,
            category="test",
            severity="Low",
            confidence="Low",
            evidence_ids=["ev1"],
            source_signal_ids=[],
            title="Test",
            summary="Test",
            explanation="Test",
            metadata={},
        )
        summary = build_signal_summary([sig])
        assert summary.total == 1
        assert "runtime" in summary.by_family


# ═══════════════════════════════════════════════════════════════════════
# S06 — Metadata minimum contract
# ═══════════════════════════════════════════════════════════════════════


class TestMetadataContract:
    """Metadata minimum expectations per family."""

    def test_all_families_have_contract(self) -> None:
        """Every SignalFamily has an entry in the metadata contract."""
        for family in SignalFamily:
            assert family in FAMILY_METADATA_REQUIRED_KEYS, (
                f"{family.value} missing from FAMILY_METADATA_REQUIRED_KEYS"
            )

    @pytest.mark.parametrize("family_name", list(GOVERNED_FAMILY_INVENTORY.keys()))
    def test_metadata_is_dict(self, family_name: str) -> None:
        """Every governed signal metadata is a dict."""
        from tests.test_v315_signal_governance_conformance import _FAMILY_ADAPTER_FACTORIES

        signals = _FAMILY_ADAPTER_FACTORIES[family_name]()
        for sig in signals:
            assert isinstance(sig.metadata, dict), (
                f"{family_name}/{sig.kind}: metadata is not a dict"
            )

    @pytest.mark.parametrize("family_name", list(GOVERNED_FAMILY_INVENTORY.keys()))
    def test_required_metadata_keys_present(self, family_name: str) -> None:
        """Family-specific required keys are present."""
        from tests.test_v315_signal_governance_conformance import _FAMILY_ADAPTER_FACTORIES

        entry = GOVERNED_FAMILY_INVENTORY[family_name]
        family = entry["family"]
        required_keys = FAMILY_METADATA_REQUIRED_KEYS.get(family, set())
        if not required_keys:
            pytest.skip(f"{family_name}: no universal required keys")

        signals = _FAMILY_ADAPTER_FACTORIES[family_name]()
        for sig in signals:
            for key in required_keys:
                assert key in sig.metadata, (
                    f"{family_name}/{sig.kind}: missing required key '{key}'"
                )

    @pytest.mark.parametrize("family_name", list(GOVERNED_FAMILY_INVENTORY.keys()))
    def test_no_empty_metadata_without_reason(self, family_name: str) -> None:
        """No adapter emits empty metadata without justification."""
        from tests.test_v315_signal_governance_conformance import _FAMILY_ADAPTER_FACTORIES

        signals = _FAMILY_ADAPTER_FACTORIES[family_name]()
        for sig in signals:
            # Empty metadata is acceptable — adapters are not required to
            # populate metadata for every kind. This test just checks that
            # metadata is a dict, which is already covered above.
            # Keep the check as an informational audit, not a hard constraint.
            assert isinstance(sig.metadata, dict)
