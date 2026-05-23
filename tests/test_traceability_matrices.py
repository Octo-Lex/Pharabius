"""Tests for traceability matrices (W46-S05)."""

from __future__ import annotations

from pathlib import Path

from pharabius.core.traceability import (
    render_claim_workpackage_matrix,
    render_evidence_finding_matrix,
    render_finding_claim_matrix,
    write_traceability_matrices,
)
from pharabius.schemas.claims import OperationalClaim


def _finding(
    fid: str = "TD-001",
    evidence_ids: list[str] | None = None,
) -> dict:
    return {
        "id": fid,
        "category": "TD-ARCH",
        "title": f"Issue {fid}",
        "description": "Desc",
        "evidence_ids": evidence_ids or [],
        "related_findings": [],
    }


def _claim(
    claim_id: str = "CLM-000001",
    status: str = "confirmed",
    evidence_ids: list[str] | None = None,
    findings: list[str] | None = None,
    work_packages: list[str] | None = None,
    requires_hv: bool = False,
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
        requires_human_validation=requires_hv,
        validation_question="Why?" if status == "gap" else None,
        source="finding",
    )


class TestEvidenceFindingMatrix:
    def test_maps_evidence_to_findings(self) -> None:
        findings = [
            _finding(fid="TD-001", evidence_ids=["EVD-001", "EVD-002"]),
            _finding(fid="TD-002", evidence_ids=["EVD-002"]),
        ]
        md = render_evidence_finding_matrix(findings)
        assert "EVD-001" in md
        assert "TD-001" in md
        assert "TD-002" in md

    def test_empty_findings(self) -> None:
        md = render_evidence_finding_matrix([])
        assert "No findings" in md

    def test_no_evidence(self) -> None:
        findings = [_finding(evidence_ids=[])]
        md = render_evidence_finding_matrix(findings)
        assert "No evidence links" in md

    def test_deterministic(self) -> None:
        findings = [
            _finding(fid="TD-002", evidence_ids=["EVD-002"]),
            _finding(fid="TD-001", evidence_ids=["EVD-001"]),
        ]
        md1 = render_evidence_finding_matrix(findings)
        md2 = render_evidence_finding_matrix(findings)
        assert md1 == md2


class TestFindingClaimMatrix:
    def test_maps_findings_to_claims(self) -> None:
        findings = [_finding(fid="TD-001")]
        claims = [_claim(claim_id="CLM-000001", findings=["TD-001"])]
        md = render_finding_claim_matrix(findings, claims)
        assert "TD-001" in md
        assert "CLM-000001" in md

    def test_warning_for_finding_without_claim(self) -> None:
        findings = [_finding(fid="TD-UNLINKED")]
        claims = [_claim(claim_id="CLM-000001", findings=["TD-001"])]
        md = render_finding_claim_matrix(findings, claims)
        assert "TD-UNLINKED" in md
        assert "no generated claim" in md

    def test_gap_count(self) -> None:
        findings = [_finding(fid="TD-001")]
        claims = [
            _claim(
                claim_id="CLM-000001",
                status="gap",
                findings=["TD-001"],
            )
        ]
        md = render_finding_claim_matrix(findings, claims)
        assert "1" in md


class TestClaimWorkPackageMatrix:
    def test_maps_claims_to_work_packages(self) -> None:
        claims = [
            _claim(
                claim_id="CLM-000001",
                work_packages=["WP-001"],
            )
        ]
        md = render_claim_workpackage_matrix(claims)
        assert "WP-001" in md
        assert "CLM-000001" in md

    def test_warning_for_gap_with_work_package(self) -> None:
        claims = [
            _claim(
                claim_id="CLM-000001",
                status="gap",
                work_packages=["WP-001"],
            )
        ]
        md = render_claim_workpackage_matrix(claims)
        assert "blocking gap" in md

    def test_no_work_packages_shows_dash(self) -> None:
        claims = [_claim(claim_id="CLM-000001", work_packages=[])]
        md = render_claim_workpackage_matrix(claims)
        assert "\u2014" in md  # em dash

    def test_empty_claims(self) -> None:
        md = render_claim_workpackage_matrix([])
        assert "No claims" in md


class TestTraceabilityWriter:
    def test_writes_all_three(self, tmp_path: Path) -> None:
        findings = [_finding(fid="TD-001", evidence_ids=["EVD-001"])]
        claims = [_claim(claim_id="CLM-000001", findings=["TD-001"])]
        paths = write_traceability_matrices(tmp_path / "trace", findings, claims)
        assert len(paths) == 3
        for p in paths:
            assert p.exists()

    def test_creates_directory(self, tmp_path: Path) -> None:
        d = tmp_path / "trace"
        assert not d.exists()
        write_traceability_matrices(d, [], [])
        assert d.exists()
