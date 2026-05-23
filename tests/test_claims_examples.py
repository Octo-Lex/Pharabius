"""Tests for operational claims example files (W46-S06)."""

from __future__ import annotations

import json
from pathlib import Path

CLAIMS_EXAMPLES = Path("docs/examples/claims")
TRACE_EXAMPLES = Path("docs/examples/traceability")


class TestClaimsExamples:
    def test_json_parses(self) -> None:
        data = json.loads((CLAIMS_EXAMPLES / "operational-claims.example.json").read_text())
        assert data["schema_version"] == "1.0"
        assert len(data["claims"]) == 3

    def test_json_has_confirmed_inferred_gap(self) -> None:
        data = json.loads((CLAIMS_EXAMPLES / "operational-claims.example.json").read_text())
        statuses = {c["status"] for c in data["claims"]}
        assert statuses == {"confirmed", "inferred", "gap"}

    def test_confidence_report_exists(self) -> None:
        assert (CLAIMS_EXAMPLES / "confidence-report.example.md").exists()

    def test_gaps_exists(self) -> None:
        assert (CLAIMS_EXAMPLES / "gaps.example.md").exists()

    def test_questions_exists(self) -> None:
        assert (CLAIMS_EXAMPLES / "questions.example.md").exists()


class TestTraceabilityExamples:
    def test_evidence_finding_exists(self) -> None:
        assert (TRACE_EXAMPLES / "evidence-finding-matrix.example.md").exists()

    def test_finding_claim_exists(self) -> None:
        assert (TRACE_EXAMPLES / "finding-claim-matrix.example.md").exists()

    def test_claim_workpackage_exists(self) -> None:
        assert (TRACE_EXAMPLES / "claim-workpackage-matrix.example.md").exists()


class TestDocsSafety:
    def test_claims_docs_mention_human_validation(self) -> None:
        md = Path("docs/OPERATIONAL_CLAIMS.md").read_text().lower()
        assert "human validation" in md

    def test_claims_docs_mention_not_factual_precision(self) -> None:
        md = Path("docs/OPERATIONAL_CLAIMS.md").read_text().lower()
        assert "factual-precision" in md or "not a factual" in md
