"""Tests for operational claim schemas and helpers (W46-S01)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pharabius.core.claims import (
    render_claims_markdown,
    render_gaps_markdown,
    write_claims_json,
    write_claims_markdown,
    write_gaps_markdown,
)
from pharabius.schemas.claims import (
    OperationalClaim,
    OperationalClaimsRegister,
    OperationalClaimsRegisterSummary,
)


def _confirmed_claim() -> OperationalClaim:
    return OperationalClaim(
        claim_id="CLM-0001",
        claim_type="architecture",
        statement="Auth logic is distributed across middleware and route handlers.",
        status="confirmed",
        confidence="High",
        evidence_ids=["EVD-000012", "EVD-000018"],
        linked_findings=["TD-ARCH-001"],
        linked_work_packages=["WP-001"],
        source="finding",
    )


def _inferred_claim() -> OperationalClaim:
    return OperationalClaim(
        claim_id="CLM-0002",
        claim_type="dependency",
        statement="Service depends on deprecated library version.",
        status="inferred",
        confidence="Medium",
        evidence_ids=["EVD-000020"],
        source="evidence",
        limitations=["Based on static analysis only"],
    )


def _gap_claim() -> OperationalClaim:
    return OperationalClaim(
        claim_id="CLM-0003",
        claim_type="security",
        statement="No evidence of input validation in payment endpoint.",
        status="gap",
        confidence="Low",
        source="derived",
        validation_question="Has input validation been reviewed for payment endpoints?",
        requires_human_validation=True,
    )


# --- Schema validation ---


class TestOperationalClaimValid:
    def test_confirmed_with_evidence(self) -> None:
        c = _confirmed_claim()
        assert c.status == "confirmed"
        assert len(c.evidence_ids) == 2

    def test_inferred_with_limitations(self) -> None:
        c = _inferred_claim()
        assert c.status == "inferred"
        assert c.limitations

    def test_gap_with_question(self) -> None:
        c = _gap_claim()
        assert c.status == "gap"
        assert c.validation_question is not None
        assert c.requires_human_validation is True

    def test_json_serializable(self) -> None:
        c = _confirmed_claim()
        data = json.loads(c.model_dump_json())
        assert data["claim_id"] == "CLM-0001"

    def test_all_claim_types_accepted(self) -> None:
        for ct in (
            "behavior",
            "architecture",
            "dependency",
            "test",
            "security",
            "compliance",
            "operational",
            "business_rule",
            "data",
            "documentation",
        ):
            c = OperationalClaim(
                claim_id=f"CLM-TYPE-{ct}",
                claim_type=ct,  # type: ignore[arg-type]
                statement=f"Test claim for {ct}",
                status="inferred",
                confidence="Medium",
                source="derived",
            )
            assert c.claim_type == ct


class TestOperationalClaimInvalid:
    def test_confirmed_without_evidence_rejected(self) -> None:
        with pytest.raises(ValidationError, match="evidence ID"):
            OperationalClaim(
                claim_id="CLM-BAD",
                claim_type="architecture",
                statement="No evidence",
                status="confirmed",
                confidence="High",
                source="derived",
            )

    def test_gap_without_question_rejected(self) -> None:
        with pytest.raises(ValidationError, match="validation_question"):
            OperationalClaim(
                claim_id="CLM-GAP",
                claim_type="security",
                statement="Missing evidence",
                status="gap",
                confidence="Low",
                source="derived",
            )

    def test_human_validation_without_question_rejected(self) -> None:
        with pytest.raises(ValidationError, match="validation_question"):
            OperationalClaim(
                claim_id="CLM-HV",
                claim_type="behavior",
                statement="Needs review",
                status="inferred",
                confidence="Medium",
                source="finding",
                requires_human_validation=True,
            )

    def test_empty_statement_rejected(self) -> None:
        with pytest.raises(ValidationError, match="empty"):
            OperationalClaim(
                claim_id="CLM-EMPTY",
                claim_type="behavior",
                statement="  ",
                status="inferred",
                confidence="Medium",
                source="derived",
            )

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            OperationalClaim(
                claim_id="CLM-X",
                claim_type="behavior",
                statement="Test",
                status="inferred",
                confidence="Medium",
                source="derived",
                unexpected="field",  # type: ignore[call-arg]
            )


# --- Register ---


class TestOperationalClaimsRegister:
    def test_valid_register(self) -> None:
        r = OperationalClaimsRegister(
            claims=[_confirmed_claim(), _inferred_claim()],
        )
        assert len(r.claims) == 2
        assert r.schema_version == "1.0"

    def test_duplicate_claim_ids_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Duplicate"):
            OperationalClaimsRegister(
                claims=[_confirmed_claim(), _confirmed_claim()],
            )

    def test_summary_defaults(self) -> None:
        s = OperationalClaimsRegisterSummary()
        assert s.total_claims == 0

    def test_warnings_default_empty(self) -> None:
        r = OperationalClaimsRegister()
        assert r.warnings == []


# --- Markdown rendering ---


class TestClaimsMarkdown:
    def test_deterministic_output(self) -> None:
        r = OperationalClaimsRegister(
            project_name="test",
            claims=[_confirmed_claim()],
        )
        md1 = render_claims_markdown(r)
        md2 = render_claims_markdown(r)
        assert md1 == md2

    def test_contains_claims_table(self) -> None:
        r = OperationalClaimsRegister(claims=[_confirmed_claim()])
        md = render_claims_markdown(r)
        assert "## Claims" in md
        assert "CLM-0001" in md

    def test_empty_register(self) -> None:
        r = OperationalClaimsRegister()
        md = render_claims_markdown(r)
        assert "# Operational Claims Register" in md


class TestGapsMarkdown:
    def test_shows_gaps(self) -> None:
        r = OperationalClaimsRegister(claims=[_gap_claim()])
        md = render_gaps_markdown(r)
        assert "## CLM-0003" in md
        assert "Validation Question" in md

    def test_no_gaps_message(self) -> None:
        r = OperationalClaimsRegister(claims=[_confirmed_claim()])
        md = render_gaps_markdown(r)
        assert "No gaps identified" in md


# --- Writers ---


class TestClaimsWriters:
    def test_write_json(self, tmp_path: Path) -> None:
        d = tmp_path / "claims"
        r = OperationalClaimsRegister(claims=[_confirmed_claim()])
        path = write_claims_json(d, r)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["schema_version"] == "1.0"

    def test_write_markdown(self, tmp_path: Path) -> None:
        d = tmp_path / "claims"
        r = OperationalClaimsRegister(claims=[_confirmed_claim()])
        path = write_claims_markdown(d, r)
        assert path.exists()

    def test_write_gaps(self, tmp_path: Path) -> None:
        d = tmp_path / "claims"
        r = OperationalClaimsRegister(claims=[_gap_claim()])
        path = write_gaps_markdown(d, r)
        assert path.exists()
