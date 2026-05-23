"""Tests for operational claim generation (W46-S02)."""

from __future__ import annotations

from pharabius.core.claims import (
    build_claims_register,
    generate_claims_from_findings,
)


def _finding(
    fid: str = "TD-ARCH-001",
    category: str = "TD-ARCH",
    title: str = "Architecture issue",
    evidence_ids: list[str] | None = None,
    description: str = "Description text",
    bib: str | None = None,
) -> dict:
    return {
        "id": fid,
        "category": category,
        "title": title,
        "description": description,
        "evidence_ids": evidence_ids or [],
        "business_impact_basis": bib,
        "related_findings": [],
    }


class TestClaimStatusDetermination:
    def test_finding_with_evidence_is_confirmed(self) -> None:
        claims = generate_claims_from_findings(
            [
                _finding(evidence_ids=["EVD-001"]),
            ]
        )
        assert len(claims) == 1
        assert claims[0].status == "confirmed"
        assert claims[0].confidence == "High"

    def test_finding_with_inferred_bib_is_inferred(self) -> None:
        claims = generate_claims_from_findings(
            [
                _finding(
                    evidence_ids=["EVD-001"],
                    bib="Inferred from repository evidence.",
                ),
            ]
        )
        assert len(claims) == 1
        assert claims[0].status == "inferred"
        assert claims[0].confidence == "Medium"
        assert claims[0].requires_human_validation is True

    def test_finding_without_evidence_is_gap(self) -> None:
        claims = generate_claims_from_findings(
            [
                _finding(evidence_ids=[]),
            ]
        )
        assert len(claims) == 1
        assert claims[0].status == "gap"
        assert claims[0].confidence == "Low"
        assert claims[0].validation_question is not None


class TestClaimTypeMapping:
    def test_td_arch_maps_to_architecture(self) -> None:
        claims = generate_claims_from_findings(
            [
                _finding(category="TD-ARCH", evidence_ids=["EVD-001"]),
            ]
        )
        assert claims[0].claim_type == "architecture"

    def test_td_dep_maps_to_dependency(self) -> None:
        claims = generate_claims_from_findings(
            [
                _finding(category="TD-DEP", evidence_ids=["EVD-001"]),
            ]
        )
        assert claims[0].claim_type == "dependency"

    def test_td_test_maps_to_test(self) -> None:
        claims = generate_claims_from_findings(
            [
                _finding(category="TD-TEST", evidence_ids=["EVD-001"]),
            ]
        )
        assert claims[0].claim_type == "test"

    def test_unknown_category_maps_to_behavior(self) -> None:
        claims = generate_claims_from_findings(
            [
                _finding(category="TD-UNKNOWN", evidence_ids=["EVD-001"]),
            ]
        )
        assert claims[0].claim_type == "behavior"


class TestClaimTraceability:
    def test_preserves_evidence_ids(self) -> None:
        claims = generate_claims_from_findings(
            [
                _finding(evidence_ids=["EVD-001", "EVD-002"]),
            ]
        )
        assert claims[0].evidence_ids == ["EVD-001", "EVD-002"]

    def test_preserves_finding_id(self) -> None:
        claims = generate_claims_from_findings(
            [
                _finding(fid="TD-ARCH-001", evidence_ids=["EVD-001"]),
            ]
        )
        assert "TD-ARCH-001" in claims[0].linked_findings

    def test_work_packages_linked(self) -> None:
        f = _finding(evidence_ids=["EVD-001"])
        f["related_findings"] = ["WP-001"]
        claims = generate_claims_from_findings([f])
        assert "WP-001" in claims[0].linked_work_packages


class TestClaimOrdering:
    def test_confirmed_before_gap(self) -> None:
        claims = generate_claims_from_findings(
            [
                _finding(fid="TD-GAP", evidence_ids=[]),
                _finding(fid="TD-CONF", evidence_ids=["EVD-001"]),
            ]
        )
        assert claims[0].status == "confirmed"
        assert claims[1].status == "gap"

    def test_deterministic(self) -> None:
        findings = [_finding(fid=f"TD-{i:03d}", evidence_ids=["EVD-001"]) for i in range(5)]
        c1 = generate_claims_from_findings(findings)
        c2 = generate_claims_from_findings(findings)
        assert [c.claim_id for c in c1] == [c.claim_id for c in c2]

    def test_stable_claim_ids(self) -> None:
        claims = generate_claims_from_findings(
            [
                _finding(evidence_ids=["EVD-001"]),
            ]
        )
        assert claims[0].claim_id.startswith("CLM-")


class TestBuildRegister:
    def test_builds_complete_register(self) -> None:
        findings = [
            _finding(fid="TD-001", evidence_ids=["EVD-001"]),
            _finding(fid="TD-002", evidence_ids=[]),
        ]
        reg = build_claims_register(
            findings,
            project_name="test",
            repository="test-repo",
            branch="main",
            commit="abc",
            generated_at="2026-05-24T00:00:00Z",
        )
        assert reg.schema_version == "1.0"
        assert reg.summary.total_claims == 2
        assert reg.summary.confirmed == 1
        assert reg.summary.gap == 1

    def test_empty_findings(self) -> None:
        reg = build_claims_register([])
        assert reg.summary.total_claims == 0
