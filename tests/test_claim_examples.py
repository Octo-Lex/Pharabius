"""Tests for richer claims/gaps/traceability examples (W47-S03)."""

from __future__ import annotations

import json
from pathlib import Path

CLAIMS = Path("docs/examples/claims")
TRACE = Path("docs/examples/traceability")


class TestClaimsExamples:
    def test_json_parses(self) -> None:
        data = json.loads((CLAIMS / "operational-claims.example.json").read_text())
        assert data["schema_version"] == "1.0"
        assert len(data["claims"]) == 5

    def test_has_all_three_statuses(self) -> None:
        data = json.loads((CLAIMS / "operational-claims.example.json").read_text())
        statuses = {c["status"] for c in data["claims"]}
        assert statuses == {"confirmed", "inferred", "gap"}

    def test_has_all_three_confidences(self) -> None:
        data = json.loads((CLAIMS / "operational-claims.example.json").read_text())
        confidences = {c["confidence"] for c in data["claims"]}
        assert "High" in confidences
        assert "Medium" in confidences
        assert "Low" in confidences

    def test_validation_json_parses(self) -> None:
        data = json.loads((CLAIMS / "claim-validation.example.json").read_text())
        assert "errors" in data
        assert "warnings" in data

    def test_completeness_json_parses(self) -> None:
        data = json.loads((CLAIMS / "claim-completeness.example.json").read_text())
        assert data["total_claims"] == 5
        assert data["complete"] == 2
        assert data["needs_review"] == 2


class TestGapsExamples:
    def test_has_blocking_and_non_blocking(self) -> None:
        md = (CLAIMS / "gaps.example.md").read_text()
        assert "Blocking" in md
        assert "Non-blocking" in md

    def test_gaps_link_to_claims(self) -> None:
        md = (CLAIMS / "gaps.example.md").read_text()
        assert "CLM-000004" in md
        assert "CLM-000005" in md


class TestQuestionsExample:
    def test_has_multiple_categories(self) -> None:
        md = (CLAIMS / "questions.example.md").read_text()
        assert "## Architecture" in md
        assert "## Security Compliance" in md
        assert "## Testing Verification" in md


class TestConfidenceReportExample:
    def test_has_interpretation_note(self) -> None:
        md = (CLAIMS / "confidence-report.example.md").read_text()
        assert "factual-precision" in md

    def test_has_gap_summary(self) -> None:
        md = (CLAIMS / "confidence-report.example.md").read_text()
        assert "Blocking gaps" in md


class TestTraceabilityExamples:
    def test_evidence_finding_matrix(self) -> None:
        md = (TRACE / "evidence-finding-matrix.example.md").read_text()
        assert "EVD-000012" in md
        assert "TD-ARCH-001" in md

    def test_finding_claim_matrix(self) -> None:
        md = (TRACE / "finding-claim-matrix.example.md").read_text()
        assert "TD-SEC-001" in md
        assert "gap" in md

    def test_claim_workpackage_matrix(self) -> None:
        md = (TRACE / "claim-workpackage-matrix.example.md").read_text()
        assert "WP-003" in md
        assert "blocking gap" in md


class TestSafetyChecks:
    def test_no_api_write_language(self) -> None:
        for f in CLAIMS.rglob("*"):
            if f.is_file() and f.suffix in (".md", ".json"):
                content = f.read_text().lower()
                assert "post /rest/api" not in content
                assert "create issue" not in content

    def test_no_autonomous_remediation(self) -> None:
        for f in CLAIMS.rglob("*"):
            if f.is_file():
                content = f.read_text().lower()
                assert "auto-fix" not in content
                assert "automatically modify" not in content
