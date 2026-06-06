"""v3.22.0 — Reporter UX and documentation regression tests.

Locks reviewer-facing wording and docs without testing exact paragraphs.
Tests for stable key phrases only.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ═══════════════════════════════════════════════════════════════════════
# Governance/family doc fixture
# ═══════════════════════════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).resolve().parents[1]

GOVERNANCE_DOC_FILES = [
    "docs/SIGNAL_GOVERNANCE.md",
    "docs/SIGNAL_GOVERNANCE_AUDIT.md",
    "docs/DEPENDENCY_SIGNALS.md",
    "docs/SECURITY_EXPOSURE.md",
    "docs/ARCHITECTURE_SIGNALS.md",
    "docs/CONFIGURATION_SIGNALS.md",
    "docs/OBSERVABILITY_SIGNALS.md",
]


def _read_doc(doc_path: str) -> str:
    path = PROJECT_ROOT / doc_path
    if not path.exists():
        pytest.skip(f"{doc_path} not found")
    return path.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════
# S06 — Reporter wording regression tests
# ═══════════════════════════════════════════════════════════════════════


class TestReporterGovernanceWording:
    """Reporter governance section uses correct key phrases."""

    @pytest.fixture()
    def reporter_source(self) -> str:
        import inspect

        import pharabius.core.reporter as reporter

        return inspect.getsource(reporter)

    def test_report_has_signal_governance_summary(self, reporter_source: str) -> None:
        assert "Signal Governance Summary" in reporter_source

    def test_report_states_findings_may_create_work_packages(self, reporter_source: str) -> None:
        assert "may create work packages" in reporter_source

    def test_report_states_advisories_do_not_create_work_packages(
        self, reporter_source: str
    ) -> None:
        assert "do not create work packages" in reporter_source

    def test_report_mentions_informational_coverage_visibility(self, reporter_source: str) -> None:
        assert "coverage visibility" in reporter_source

    def test_report_mentions_suppressed_diagnostics_only(self, reporter_source: str) -> None:
        assert "diagnostics-only" in reporter_source

    def test_report_mentions_category_taxonomy(self, reporter_source: str) -> None:
        assert "Category describes the finding taxonomy" in reporter_source

    def test_report_mentions_family_governance_owner(self, reporter_source: str) -> None:
        assert "Family describes the governance owner" in reporter_source

    def test_report_states_category_family_not_always_identical(self, reporter_source: str) -> None:
        assert "not always identical" in reporter_source


# ═══════════════════════════════════════════════════════════════════════
# S06 — Documentation content tests
# ═══════════════════════════════════════════════════════════════════════


class TestDocsContent:
    """Docs contain key reviewer-facing information."""

    def test_category_family_distinction_in_docs(self) -> None:
        doc = _read_doc("docs/SIGNAL_GOVERNANCE.md")
        assert "Category describes the finding taxonomy" in doc
        assert "Family describes the governance owner" in doc

    def test_td_comp_security_exception_documented(self) -> None:
        doc = _read_doc("docs/SIGNAL_GOVERNANCE.md")
        assert "TD-COMP" in doc
        assert "SECURITY" in doc

    def test_td_sec_test_exception_documented(self) -> None:
        doc = _read_doc("docs/SIGNAL_GOVERNANCE.md")
        assert "TD-SEC" in doc
        assert "TEST" in doc

    def test_signal_examples_in_docs(self) -> None:
        doc = _read_doc("docs/SIGNAL_GOVERNANCE.md")
        assert "Signal examples" in doc or "signal examples" in doc.lower()

    def test_work_package_rules_in_docs(self) -> None:
        doc = _read_doc("docs/SIGNAL_GOVERNANCE.md")
        assert (
            "FINDING disposition creates work packages" in doc
            or "Only `FINDING` disposition creates work packages" in doc
        )

    def test_runtime_uses_td_dep_not_td_runtime(self) -> None:
        """Runtime category is TD-DEP; no TD-RUNTIME taxonomy exists."""
        doc = _read_doc("docs/SIGNAL_GOVERNANCE.md")
        assert "TD-DEP" in doc
        # TD-RUNTIME should not appear as a taxonomy category
        assert "TD-RUNTIME" not in doc

    def test_missing_tests_is_td_test(self) -> None:
        """Missing tests are TD-TEST; risk-sensitive-without-tests is TD-SEC."""
        doc = _read_doc("docs/SIGNAL_GOVERNANCE.md")
        assert "TD-TEST" in doc


class TestDocsNoFalseCapabilityClaims:
    """No doc implies capabilities that don't exist."""

    @pytest.mark.parametrize("doc_path", GOVERNANCE_DOC_FILES)
    def test_no_vulnerability_scanning_claims(self, doc_path: str) -> None:
        content = _read_doc(doc_path).lower()
        if "vulnerability scanning" in content:
            assert "no vulnerability scanning" in content or "non-goal" in content

    @pytest.mark.parametrize("doc_path", GOVERNANCE_DOC_FILES)
    def test_no_telemetry_collection_claims(self, doc_path: str) -> None:
        content = _read_doc(doc_path).lower()
        if "runtime telemetry collection" in content:
            assert "not" in content or "no " in content or "non-goal" in content


# ═══════════════════════════════════════════════════════════════════════
# S07 — No-behavior-change audit
# ═══════════════════════════════════════════════════════════════════════


class TestNoBehaviorChange:
    """v3.22.0 changes wording only — no behavioral changes."""

    def test_no_new_signal_adapters(self) -> None:
        import importlib
        import sys
        from pathlib import Path

        _fixtures_dir = str(Path(__file__).parent / "fixtures" / "signal_governance")
        if _fixtures_dir not in sys.path:
            sys.path.insert(0, _fixtures_dir)
        _gfi = importlib.import_module("governed_family_inventory")

        total_adapters = sum(len(e["adapters"]) for e in _gfi.GOVERNED_FAMILY_INVENTORY.values())
        assert total_adapters == 29

    def test_no_new_signal_families(self) -> None:
        from pharabius.core.signals.models import SignalFamily

        assert len(SignalFamily) == 10

    def test_disposition_count_unchanged(self) -> None:
        from pharabius.core.signals.models import SignalDisposition

        assert len(SignalDisposition) == 4
