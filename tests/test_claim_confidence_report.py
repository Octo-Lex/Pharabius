"""Tests for confidence report and claim metrics (W46-S04)."""

from __future__ import annotations

from pathlib import Path

from pharabius.core.claims import (
    compute_confidence_metrics,
    extract_gaps_from_claims,
    generate_claims_from_findings,
    render_confidence_report,
    write_confidence_report,
)


def _finding(
    fid: str = "TD-001",
    category: str = "TD-ARCH",
    evidence_ids: list[str] | None = None,
    priority: str = "Medium",
    bib: str | None = None,
) -> dict:
    return {
        "id": fid,
        "category": category,
        "title": f"Issue {fid}",
        "description": "Desc",
        "evidence_ids": evidence_ids or [],
        "priority": priority,
        "business_impact_basis": bib,
        "related_findings": [],
    }


class TestConfidenceMetrics:
    def test_status_counts(self) -> None:
        findings = [
            _finding(fid="TD-001", evidence_ids=["EVD-001"]),
            _finding(fid="TD-002", evidence_ids=["EVD-002"], bib="Inferred."),
            _finding(fid="TD-003", evidence_ids=[]),
        ]
        claims = generate_claims_from_findings(findings)
        metrics = compute_confidence_metrics(claims)
        assert metrics["total_claims"] == 3
        assert metrics["confirmed_claims"] == 1
        assert metrics["inferred_claims"] == 1
        assert metrics["gap_claims"] == 1

    def test_confidence_counts(self) -> None:
        findings = [
            _finding(fid="TD-001", evidence_ids=["EVD-001"]),
            _finding(fid="TD-002", evidence_ids=["EVD-002"], bib="Inferred."),
            _finding(fid="TD-003", evidence_ids=[]),
        ]
        claims = generate_claims_from_findings(findings)
        metrics = compute_confidence_metrics(claims)
        assert metrics["high_confidence"] == 1
        assert metrics["medium_confidence"] == 1
        assert metrics["low_confidence"] == 1

    def test_human_validation_count(self) -> None:
        findings = [
            _finding(fid="TD-001", evidence_ids=["EVD-001"], bib="Inferred."),
            _finding(fid="TD-002", evidence_ids=[]),
        ]
        claims = generate_claims_from_findings(findings)
        metrics = compute_confidence_metrics(claims)
        assert metrics["claims_requiring_human_validation"] == 2

    def test_gap_counts(self) -> None:
        findings = [
            _finding(fid="TD-001", evidence_ids=[], priority="High"),
            _finding(fid="TD-002", evidence_ids=[], priority="Low"),
        ]
        claims = generate_claims_from_findings(findings)
        gaps = extract_gaps_from_claims(claims, findings)
        metrics = compute_confidence_metrics(claims, gaps)
        assert metrics["blocking_gaps"] == 1
        assert metrics["non_blocking_gaps"] == 1

    def test_evidence_linked_counts(self) -> None:
        findings = [
            _finding(evidence_ids=["EVD-001", "EVD-002"]),
            _finding(evidence_ids=[]),
        ]
        claims = generate_claims_from_findings(findings)
        metrics = compute_confidence_metrics(claims)
        assert metrics["evidence_linked_claims"] == 1
        assert metrics["evidence_missing_claims"] == 1
        assert metrics["average_evidence_per_claim"] == 1.0

    def test_empty_claims(self) -> None:
        metrics = compute_confidence_metrics([])
        assert metrics["total_claims"] == 0
        assert metrics["average_evidence_per_claim"] == 0.0


class TestConfidenceReport:
    def test_contains_interpretation_note(self) -> None:
        claims = generate_claims_from_findings([_finding(evidence_ids=["EVD-001"])])
        md = render_confidence_report(claims)
        assert "not a factual-precision measurement" in md

    def test_contains_summary_table(self) -> None:
        claims = generate_claims_from_findings([_finding(evidence_ids=["EVD-001"])])
        md = render_confidence_report(claims)
        assert "## Summary" in md

    def test_contains_confidence_table(self) -> None:
        claims = generate_claims_from_findings([_finding(evidence_ids=["EVD-001"])])
        md = render_confidence_report(claims)
        assert "## Claims by Confidence" in md

    def test_deterministic(self) -> None:
        findings = [_finding(evidence_ids=["EVD-001"]), _finding(evidence_ids=[])]
        claims = generate_claims_from_findings(findings)
        md1 = render_confidence_report(claims)
        md2 = render_confidence_report(claims)
        assert md1 == md2


class TestConfidenceReportWriter:
    def test_writes_file(self, tmp_path: Path) -> None:
        claims = generate_claims_from_findings([_finding(evidence_ids=["EVD-001"])])
        path = write_confidence_report(tmp_path / "claims", claims)
        assert path.exists()
        assert path.name == "confidence-report.md"
