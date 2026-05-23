"""Tests for gap and question registry artifacts (W46-S03)."""

from __future__ import annotations

from pathlib import Path

from pharabius.core.claims import (
    extract_gaps_from_claims,
    extract_questions_from_claims,
    generate_claims_from_findings,
    render_questions_markdown,
    write_questions_markdown,
)
from pharabius.schemas.claims import QuestionItem


def _finding(
    fid: str = "TD-ARCH-001",
    category: str = "TD-ARCH",
    evidence_ids: list[str] | None = None,
    priority: str = "High",
    bib: str | None = None,
) -> dict:
    return {
        "id": fid,
        "category": category,
        "title": f"Issue {fid}",
        "description": "Description",
        "evidence_ids": evidence_ids or [],
        "priority": priority,
        "business_impact_basis": bib,
        "related_findings": [],
    }


class TestGapExtraction:
    def test_gap_claim_produces_gap(self) -> None:
        findings = [_finding(evidence_ids=[])]
        claims = generate_claims_from_findings(findings)
        gaps = extract_gaps_from_claims(claims, findings)
        assert len(gaps) == 1
        assert gaps[0].severity == "blocking"

    def test_high_priority_missing_evidence_blocking(self) -> None:
        findings = [_finding(evidence_ids=[], priority="High")]
        claims = generate_claims_from_findings(findings)
        gaps = extract_gaps_from_claims(claims, findings)
        assert gaps[0].severity == "blocking"

    def test_low_priority_missing_evidence_non_blocking(self) -> None:
        findings = [_finding(evidence_ids=[], priority="Low")]
        claims = generate_claims_from_findings(findings)
        gaps = extract_gaps_from_claims(claims, findings)
        assert gaps[0].severity == "non_blocking"

    def test_confirmed_claim_no_gap(self) -> None:
        findings = [_finding(evidence_ids=["EVD-001"])]
        claims = generate_claims_from_findings(findings)
        gaps = extract_gaps_from_claims(claims, findings)
        assert len(gaps) == 0

    def test_gaps_link_to_claim(self) -> None:
        findings = [_finding(evidence_ids=[])]
        claims = generate_claims_from_findings(findings)
        gaps = extract_gaps_from_claims(claims, findings)
        assert gaps[0].claim_id is not None

    def test_gaps_link_to_finding(self) -> None:
        findings = [_finding(fid="TD-SEC-001", evidence_ids=[])]
        claims = generate_claims_from_findings(findings)
        gaps = extract_gaps_from_claims(claims, findings)
        assert "TD-SEC-001" in gaps[0].linked_findings


class TestQuestionExtraction:
    def test_human_validation_produces_question(self) -> None:
        findings = [_finding(evidence_ids=[], bib="Inferred from evidence.")]
        claims = generate_claims_from_findings(findings)
        questions = extract_questions_from_claims(claims)
        assert len(questions) >= 1

    def test_confirmed_no_validation_no_question(self) -> None:
        findings = [_finding(evidence_ids=["EVD-001"])]
        claims = generate_claims_from_findings(findings)
        questions = extract_questions_from_claims(claims)
        assert len(questions) == 0

    def test_question_category_mapping(self) -> None:
        findings = [_finding(category="TD-ARCH", evidence_ids=[])]
        claims = generate_claims_from_findings(findings)
        questions = extract_questions_from_claims(claims)
        assert questions[0].category == "architecture"

    def test_security_maps_to_compliance(self) -> None:
        findings = [_finding(category="TD-SEC", evidence_ids=[])]
        claims = generate_claims_from_findings(findings)
        questions = extract_questions_from_claims(claims)
        assert questions[0].category == "security_compliance"


class TestQuestionMarkdown:
    def test_renders_with_categories(self) -> None:
        questions = [
            QuestionItem(
                question_id="Q-0001",
                claim_id="CLM-000001",
                question="Has input validation been reviewed?",
                category="security_compliance",
            ),
        ]
        md = render_questions_markdown(questions)
        assert "## Security Compliance" in md
        assert "Q-0001" in md

    def test_empty_questions(self) -> None:
        md = render_questions_markdown([])
        assert "No questions identified" in md

    def test_deterministic(self) -> None:
        questions = [
            QuestionItem(
                question_id=f"Q-{i:04d}",
                question=f"Question {i}",
                category="general",
            )
            for i in range(3)
        ]
        md1 = render_questions_markdown(questions)
        md2 = render_questions_markdown(questions)
        assert md1 == md2


class TestQuestionWriter:
    def test_writes_file(self, tmp_path: Path) -> None:
        questions = [
            QuestionItem(
                question_id="Q-0001",
                question="Test?",
                category="general",
            )
        ]
        path = write_questions_markdown(tmp_path / "claims", questions)
        assert path.exists()
        assert path.name == "questions.md"
