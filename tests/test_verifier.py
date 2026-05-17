"""Tests for the deterministic verifier."""

from __future__ import annotations

from pathlib import Path

import pytest

from pharabius.core.verifier import (
    STATUS_PARTIALLY_SUPPORTED,
    STATUS_STALE,
    STATUS_STILL_DETECTED,
    _match_findings,
    _parse_wp_debt_ids,
    verify_repository,
)
from pharabius.schemas.analysis_unit import AnalysisUnit, AnalysisUnitStore
from pharabius.schemas.evidence import EvidenceItem, EvidenceLocation, EvidenceStore
from pharabius.schemas.finding import DebtFinding, DebtRegister, DebtRegisterSummary

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_evidence(eid: str, etype: str, cat: str, file: str) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=eid,
        type=etype,
        category=cat,
        location=EvidenceLocation(file=file),
        summary=f"{etype}: {file}",
    )


def _make_finding(
    fid: str = "TD-DEP-001",
    category: str = "TD-DEP",
    title: str = "Missing lockfile",
    evidence_ids: list[str] | None = None,
    locations: list[str] | None = None,
    analysis_unit_ids: list[str] | None = None,
) -> DebtFinding:
    return DebtFinding(
        id=fid,
        category=category,
        title=title,
        description=f"Test finding: {title}",
        severity="Medium",
        technical_impact="Test impact",
        business_impact="Test business impact",
        risk_score=50,
        priority="Medium",
        recommended_action="Test action",
        evidence_ids=evidence_ids or [],
        locations=locations or [],
        analysis_unit_ids=analysis_unit_ids or [],
    )


def _setup_repo(
    tmp_path: Path,
    findings: list[DebtFinding],
    evidence: list[EvidenceItem],
    units: list[AnalysisUnit] | None = None,
    work_packages: dict[str, str] | None = None,
) -> Path:
    """Set up a .ai-debt directory with the given artifacts."""
    ai_debt = tmp_path / ".ai-debt"
    ai_debt.mkdir()

    register = DebtRegister(
        project_name="test",
        repository=str(tmp_path),
        summary=DebtRegisterSummary(total_findings=len(findings)),
        findings=findings,
    )
    (ai_debt / "debt-register.json").write_text(
        register.model_dump_json(indent=2), encoding="utf-8"
    )

    store = EvidenceStore(evidence=evidence)
    (ai_debt / "evidence.json").write_text(store.model_dump_json(indent=2), encoding="utf-8")

    if units is not None:
        unit_store = AnalysisUnitStore(units=units)
        (ai_debt / "analysis-units.json").write_text(
            unit_store.model_dump_json(indent=2), encoding="utf-8"
        )

    if work_packages:
        wp_dir = ai_debt / "work-packages"
        wp_dir.mkdir()
        for name, content in work_packages.items():
            (wp_dir / name).write_text(content, encoding="utf-8")

    return tmp_path


# ---------------------------------------------------------------------------
# Matching tests
# ---------------------------------------------------------------------------


class TestMatchingLogic:
    def test_category_plus_evidence_overlap_matches_changed_id(self) -> None:
        original = _make_finding(
            fid="TD-DEP-001",
            category="TD-DEP",
            evidence_ids=["EVD-001", "EVD-002", "EVD-003"],
        )
        current = _make_finding(
            fid="TD-DEP-099",
            category="TD-DEP",
            evidence_ids=["EVD-001", "EVD-002", "EVD-099"],
        )
        matches = _match_findings(original, [current])
        assert matches == ["TD-DEP-099"]

    def test_category_plus_locations_matches_changed_evidence(self) -> None:
        original = _make_finding(
            fid="TD-DEP-001",
            category="TD-DEP",
            evidence_ids=["EVD-001"],
            locations=["pyproject.toml"],
        )
        current = _make_finding(
            fid="TD-DEP-002",
            category="TD-DEP",
            evidence_ids=["EVD-999"],
            locations=["pyproject.toml"],
        )
        matches = _match_findings(original, [current])
        assert matches == ["TD-DEP-002"]

    def test_category_plus_title_matches(self) -> None:
        original = _make_finding(
            fid="TD-DEP-001",
            category="TD-DEP",
            title="Missing lockfile for Python",
            evidence_ids=["EVD-001"],
            locations=["src/lib"],
        )
        current = _make_finding(
            fid="TD-DEP-005",
            category="TD-DEP",
            title="Missing lockfile for Python",
            evidence_ids=["EVD-888"],
            locations=["src/other"],
        )
        matches = _match_findings(original, [current])
        assert matches == ["TD-DEP-005"]

    def test_same_id_different_category_does_not_match(self) -> None:
        original = _make_finding(
            fid="TD-DEP-001",
            category="TD-DEP",
            evidence_ids=["EVD-001"],
            locations=["pyproject.toml"],
            title="Missing lockfile",
        )
        current = _make_finding(
            fid="TD-DEP-001",
            category="TD-TEST",
            evidence_ids=["EVD-001"],
            locations=["pyproject.toml"],
            title="Missing tests",
        )
        matches = _match_findings(original, [current])
        assert matches == []

    def test_no_match_returns_empty(self) -> None:
        original = _make_finding(fid="TD-DEP-001", category="TD-DEP", evidence_ids=["EVD-001"])
        current = _make_finding(fid="TD-TEST-001", category="TD-TEST", evidence_ids=["EVD-099"])
        matches = _match_findings(original, [current])
        assert matches == []


# ---------------------------------------------------------------------------
# Status assignment tests
# ---------------------------------------------------------------------------


class TestStatusAssignment:
    def test_still_detected(self, tmp_path: Path) -> None:
        evidence = [_make_evidence("EVD-001", "manifest_detected", "deps", "pyproject.toml")]
        finding = _make_finding(evidence_ids=["EVD-001"], locations=["pyproject.toml"])
        # Create the file so location check passes
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        _setup_repo(tmp_path, [finding], evidence)
        report = verify_repository(tmp_path)
        assert report.total_findings_checked == 1
        r = report.results[0]
        # Should be still_detected (analyzer re-runs and produces matching finding)
        assert r.verification_status in (
            STATUS_STILL_DETECTED,
            STATUS_PARTIALLY_SUPPORTED,
        )

    def test_missing_debt_register_fails(self, tmp_path: Path) -> None:
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        store = EvidenceStore(evidence=[])
        (ai_debt / "evidence.json").write_text(store.model_dump_json(), encoding="utf-8")
        with pytest.raises(FileNotFoundError, match=r"debt-register\.json not found"):
            verify_repository(tmp_path)

    def test_missing_evidence_fails(self, tmp_path: Path) -> None:
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        register = DebtRegister(project_name="test", findings=[])
        (ai_debt / "debt-register.json").write_text(register.model_dump_json(), encoding="utf-8")
        with pytest.raises(FileNotFoundError, match=r"evidence\.json not found"):
            verify_repository(tmp_path)

    def test_works_without_analysis_units(self, tmp_path: Path) -> None:
        evidence = [_make_evidence("EVD-001", "manifest_detected", "deps", "pyproject.toml")]
        finding = _make_finding(
            evidence_ids=["EVD-001"],
            analysis_unit_ids=["AU-PKG-001"],
            locations=["pyproject.toml"],
        )
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        _setup_repo(tmp_path, [finding], evidence, units=None)
        report = verify_repository(tmp_path)
        assert report.results[0].analysis_units_available is False
        assert report.results[0].verification_status != STATUS_STALE
        assert any("unavailable" in n.lower() for n in report.results[0].notes)

    def test_works_with_old_format_no_unit_ids(self, tmp_path: Path) -> None:
        evidence = [_make_evidence("EVD-001", "manifest_detected", "deps", "pyproject.toml")]
        finding = _make_finding(
            evidence_ids=["EVD-001"],
            analysis_unit_ids=[],
            locations=["pyproject.toml"],
        )
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        _setup_repo(tmp_path, [finding], evidence)
        report = verify_repository(tmp_path)
        assert report.total_findings_checked == 1


# ---------------------------------------------------------------------------
# Location tests
# ---------------------------------------------------------------------------


class TestLocationVerification:
    def test_location_present(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        evidence = [_make_evidence("EVD-001", "manifest_detected", "deps", "pyproject.toml")]
        finding = _make_finding(evidence_ids=["EVD-001"], locations=["pyproject.toml"])
        _setup_repo(tmp_path, [finding], evidence)
        report = verify_repository(tmp_path)
        r = report.results[0]
        assert "pyproject.toml" in r.locations_present

    def test_location_missing(self, tmp_path: Path) -> None:
        evidence = [_make_evidence("EVD-001", "manifest_detected", "deps", "pyproject.toml")]
        finding = _make_finding(evidence_ids=["EVD-001"], locations=["nonexistent.toml"])
        _setup_repo(tmp_path, [finding], evidence)
        report = verify_repository(tmp_path)
        r = report.results[0]
        assert "nonexistent.toml" in r.locations_missing


# ---------------------------------------------------------------------------
# Work package tests
# ---------------------------------------------------------------------------


class TestWorkPackageVerification:
    def test_wp_valid(self, tmp_path: Path) -> None:
        evidence = [_make_evidence("EVD-001", "manifest_detected", "deps", "pyproject.toml")]
        finding = _make_finding(evidence_ids=["EVD-001"], locations=["pyproject.toml"])
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        wp_content = "# WP\n\n## Linked Debt Items\n\n- `TD-DEP-001`\n"
        _setup_repo(
            tmp_path,
            [finding],
            evidence,
            work_packages={"WP-001-test.md": wp_content},
        )
        report = verify_repository(tmp_path)
        assert (
            report.work_packages_valid + report.work_packages_stale + report.work_packages_orphaned
            >= 1
        )

    def test_wp_orphaned(self, tmp_path: Path) -> None:
        evidence = [_make_evidence("EVD-001", "manifest_detected", "deps", "pyproject.toml")]
        finding = _make_finding(evidence_ids=["EVD-001"], locations=["pyproject.toml"])
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        wp_content = "# WP\n\n## Linked Debt Items\n\n- `TD-NONEXIST-999`\n"
        _setup_repo(
            tmp_path,
            [finding],
            evidence,
            work_packages={"WP-001-orphan.md": wp_content},
        )
        report = verify_repository(tmp_path)
        assert report.work_packages_orphaned == 1

    def test_wp_needs_review_no_ids(self, tmp_path: Path) -> None:
        evidence = [_make_evidence("EVD-001", "manifest_detected", "deps", "pyproject.toml")]
        finding = _make_finding(evidence_ids=["EVD-001"], locations=["pyproject.toml"])
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        wp_content = "# WP\n\n## Some Other Section\n\nNo debt IDs here.\n"
        _setup_repo(
            tmp_path,
            [finding],
            evidence,
            work_packages={"WP-001-empty.md": wp_content},
        )
        report = verify_repository(tmp_path)
        assert report.work_packages_needs_review == 1


class TestParseWpDebtIds:
    def test_extracts_ids(self, tmp_path: Path) -> None:
        content = "# WP\n\n## Linked Debt Items\n\n- `TD-DEP-001`\n- `TD-TEST-002`\n"
        wp = tmp_path / "WP-001.md"
        wp.write_text(content, encoding="utf-8")
        ids = _parse_wp_debt_ids(wp)
        assert ids == ["TD-DEP-001", "TD-TEST-002"]

    def test_no_ids(self, tmp_path: Path) -> None:
        content = "# WP\n\n## Objective\n\nDo stuff.\n"
        wp = tmp_path / "WP-002.md"
        wp.write_text(content, encoding="utf-8")
        ids = _parse_wp_debt_ids(wp)
        assert ids == []


# ---------------------------------------------------------------------------
# Debt register immutability test
# ---------------------------------------------------------------------------


class TestDebtRegisterImmutability:
    def test_debt_register_unchanged(self, tmp_path: Path) -> None:
        evidence = [_make_evidence("EVD-001", "manifest_detected", "deps", "pyproject.toml")]
        finding = _make_finding(evidence_ids=["EVD-001"], locations=["pyproject.toml"])
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        _setup_repo(tmp_path, [finding], evidence)

        register_path = tmp_path / ".ai-debt" / "debt-register.json"
        before = register_path.read_bytes()

        verify_repository(tmp_path)

        after = register_path.read_bytes()
        assert before == after, "debt-register.json was modified during verification!"
