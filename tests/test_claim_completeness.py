"""Tests for claim quality/completeness checks (W47-S02)."""

from __future__ import annotations

from pharabius.core.claim_validation import (
    assess_claim_completeness,
    assess_register_completeness,
)
from pharabius.schemas.claims import (
    OperationalClaim,
    OperationalClaimsRegister,
)


def _claim(
    claim_id: str = "CLM-000001",
    status: str = "confirmed",
    evidence_ids: list[str] | None = None,
    findings: list[str] | None = None,
    work_packages: list[str] | None = None,
    limitations: list[str] | None = None,
) -> OperationalClaim:
    return OperationalClaim(
        claim_id=claim_id,
        claim_type="architecture",
        statement="Test claim",
        status=status,  # type: ignore[arg-type]
        confidence="High" if status == "confirmed" else "Low",
        evidence_ids=evidence_ids or (["EVD-001"] if status == "confirmed" else []),
        linked_findings=findings or ["TD-001"],
        linked_work_packages=work_packages or [],
        requires_human_validation=status != "confirmed",
        validation_question="Validate?" if status != "confirmed" else None,
        source="finding",
        limitations=limitations or [],
    )


class TestClaimCompleteness:
    def test_confirmed_with_evidence_is_complete(self) -> None:
        c = _claim(evidence_ids=["EVD-001"], findings=["TD-001"])
        result = assess_claim_completeness(c)
        assert result.status == "complete"
        assert result.evidence_linked is True

    def test_inferred_with_evidence_is_partial(self) -> None:
        c = _claim(status="inferred", evidence_ids=["EVD-001"], limitations=["basis"])
        result = assess_claim_completeness(c)
        assert result.status == "partial"

    def test_inferred_without_limitations_is_partial_with_warning(self) -> None:
        c = _claim(status="inferred", evidence_ids=["EVD-001"])
        result = assess_claim_completeness(c)
        assert result.status == "partial"
        assert any("limitations" in w for w in result.warnings)

    def test_gap_is_needs_review(self) -> None:
        c = _claim(status="gap")
        result = assess_claim_completeness(c)
        assert result.status == "needs_review"
        assert result.blocking_gap is True

    def test_gap_with_work_package_warns(self) -> None:
        c = _claim(status="gap", work_packages=["WP-001"])
        result = assess_claim_completeness(c)
        assert any("not proceed" in w for w in result.warnings)

    def test_no_evidence_is_needs_review(self) -> None:
        c = _claim(status="inferred", evidence_ids=[])
        result = assess_claim_completeness(c)
        assert result.status == "needs_review"


class TestRegisterCompleteness:
    def test_counts(self) -> None:
        reg = OperationalClaimsRegister(
            claims=[
                _claim(claim_id="CLM-001", evidence_ids=["EVD-001"]),
                _claim(claim_id="CLM-002", status="inferred", evidence_ids=["EVD-001"]),
                _claim(claim_id="CLM-003", status="gap"),
            ]
        )
        result = assess_register_completeness(reg)
        assert result.total_claims == 3
        assert result.complete == 1
        assert result.partial == 1
        assert result.needs_review == 1

    def test_empty_register(self) -> None:
        reg = OperationalClaimsRegister()
        result = assess_register_completeness(reg)
        assert result.total_claims == 0

    def test_needs_review_produces_warning(self) -> None:
        reg = OperationalClaimsRegister(
            claims=[_claim(claim_id="CLM-001", status="gap")],
        )
        result = assess_register_completeness(reg)
        assert result.warnings
        assert "human review" in result.warnings[0].lower()

    def test_all_complete_no_warning(self) -> None:
        reg = OperationalClaimsRegister(
            claims=[_claim(claim_id="CLM-001", evidence_ids=["EVD-001"])],
        )
        result = assess_register_completeness(reg)
        assert not result.warnings


class TestDeterminism:
    def test_deterministic(self) -> None:
        reg = OperationalClaimsRegister(
            claims=[
                _claim(claim_id="CLM-001", evidence_ids=["EVD-001"]),
                _claim(claim_id="CLM-002", status="gap"),
            ]
        )
        r1 = assess_register_completeness(reg)
        r2 = assess_register_completeness(reg)
        assert r1.model_dump_json() == r2.model_dump_json()


class TestNoRiskScoreModification:
    def test_completeness_does_not_change_claim(self) -> None:
        c = _claim(evidence_ids=["EVD-001"])
        before = c.model_dump_json()
        assess_claim_completeness(c)
        assert c.model_dump_json() == before
