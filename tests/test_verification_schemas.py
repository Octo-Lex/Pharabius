"""Tests for verification schemas."""

from __future__ import annotations

from pharabius.schemas.verification import (
    VerificationReport,
    VerificationResult,
    WorkPackageVerificationResult,
)


class TestVerificationResult:
    def test_validates_with_defaults(self) -> None:
        result = VerificationResult(finding_id="TD-DEP-001")
        assert result.finding_id == "TD-DEP-001"
        assert result.verification_status == "uncertain"
        assert result.evidence_ids_checked == []
        assert result.evidence_ids_present == []
        assert result.evidence_ids_missing == []
        assert result.locations_checked == []
        assert result.locations_present == []
        assert result.locations_missing == []
        assert result.analysis_units_available is True
        assert result.still_detected_by_current_analyzer is False

    def test_default_list_fields_are_independent(self) -> None:
        r1 = VerificationResult(finding_id="A")
        r2 = VerificationResult(finding_id="B")
        r1.evidence_ids_present.append("EVD-001")
        assert r2.evidence_ids_present == []


class TestWorkPackageVerificationResult:
    def test_validates_with_defaults(self) -> None:
        wp = WorkPackageVerificationResult(work_package_path="work-packages/WP-001.md")
        assert wp.status == "needs_review"
        assert wp.linked_debt_ids == []
        assert wp.notes == []

    def test_default_list_fields_are_independent(self) -> None:
        wp1 = WorkPackageVerificationResult(work_package_path="WP-1.md")
        wp2 = WorkPackageVerificationResult(work_package_path="WP-2.md")
        wp1.linked_debt_ids.append("TD-DEP-001")
        assert wp2.linked_debt_ids == []


class TestVerificationReport:
    def test_validates_with_defaults(self) -> None:
        report = VerificationReport(repository="/tmp/repo")
        assert report.schema_version == "1.0"
        assert report.total_findings_checked == 0
        assert report.results == []
        assert report.work_package_results == []
        assert report.current_analyzer_mode == "deterministic-no-ai"

    def test_default_list_fields_are_independent(self) -> None:
        r1 = VerificationReport(repository="a")
        r2 = VerificationReport(repository="b")
        r1.results.append(VerificationResult(finding_id="X"))
        assert r2.results == []

    def test_with_nested_results(self) -> None:
        result = VerificationResult(
            finding_id="TD-DEP-001",
            verification_status="still_detected",
            evidence_ids_present=["EVD-001"],
        )
        report = VerificationReport(
            repository="/tmp/repo",
            total_findings_checked=1,
            still_detected_count=1,
            results=[result],
        )
        assert len(report.results) == 1
        assert report.results[0].verification_status == "still_detected"
