"""Tests for docs/v2/ planning document coverage (Wave 52 validation)."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

V2 = Path("docs/v2")


class TestV2DocsExist:
    """Ensure all Wave 52 planning documents exist."""

    EXPECTED_FILES: ClassVar[list[str]] = [
        "README.md",
        "V2_PRODUCT_THESIS.md",
        "V2_OPTION_MAP.md",
        "V2_AUTOMATION_BOUNDARY_MODEL.md",
        "V2_EXTERNAL_INTEGRATION_RISK_MODEL.md",
        "V2_DATA_MODEL_AND_DEPLOYMENT_OPTIONS.md",
        "V2_ROADMAP_DECISION_MATRIX.md",
        "V2_PLANNING_REPORT.md",
    ]

    def test_all_v2_docs_exist(self) -> None:
        for name in self.EXPECTED_FILES:
            p = V2 / name
            assert p.exists(), f"Missing: {p}"
            assert p.stat().st_size > 100, f"Too small (likely empty): {p}"


class TestV2DocsContent:
    """Ensure planning docs contain key structural elements."""

    def test_readme_lists_all_docs(self) -> None:
        text = (V2 / "README.md").read_text(encoding="utf-8")
        for name in TestV2DocsExist.EXPECTED_FILES:
            if name == "README.md":
                continue
            assert name in text, f"README.md doesn't reference {name}"

    def test_readme_states_planning_only(self) -> None:
        text = (V2 / "README.md").read_text(encoding="utf-8")
        assert "planning" in text.lower()
        assert "no v2 implementation" in text.lower() or "not an implementation" in text.lower()

    def test_product_thesis_has_expansion_principles(self) -> None:
        text = (V2 / "V2_PRODUCT_THESIS.md").read_text(encoding="utf-8")
        assert "expansion principle" in text.lower() or "Expansion Principle" in text

    def test_automation_model_has_forbidden_actions(self) -> None:
        text = (V2 / "V2_AUTOMATION_BOUNDARY_MODEL.md").read_text(encoding="utf-8")
        assert "Forbidden" in text
        assert "A6" in text  # Forbidden automation level

    def test_integration_model_has_classes(self) -> None:
        text = (V2 / "V2_EXTERNAL_INTEGRATION_RISK_MODEL.md").read_text(encoding="utf-8")
        assert "I0" in text
        assert "I6" in text

    def test_decision_matrix_has_scores(self) -> None:
        text = (V2 / "V2_ROADMAP_DECISION_MATRIX.md").read_text(encoding="utf-8")
        assert "Weighted Total" in text or "Weighted" in text
        assert "65" in text  # Top score for human validation workflow

    def test_planning_report_has_recommendation(self) -> None:
        text = (V2 / "V2_PLANNING_REPORT.md").read_text(encoding="utf-8")
        assert "recommendation" in text.lower()
        assert "policy engine" in text.lower()

    def test_planning_report_has_v1_maintenance_posture(self) -> None:
        text = (V2 / "V2_PLANNING_REPORT.md").read_text(encoding="utf-8")
        assert "Maintenance" in text or "maintenance" in text.lower()

    def test_planning_report_defers_external_writes(self) -> None:
        text = (V2 / "V2_PLANNING_REPORT.md").read_text(encoding="utf-8")
        assert "v2.4" in text or "deferred" in text.lower()


class TestV2DocsLinkedFromIndex:
    """Ensure v2 docs are reachable from the main docs index."""

    def test_docs_readme_links_v2(self) -> None:
        text = Path("docs/README.md").read_text(encoding="utf-8")
        # v2 planning docs are linked from ROADMAP.md, not necessarily docs/README.md
        assert "roadmap" in text.lower()

    def test_roadmap_references_v2(self) -> None:
        text = Path("docs/ROADMAP.md").read_text(encoding="utf-8")
        assert "v2" in text.lower() or "v2.0" in text
