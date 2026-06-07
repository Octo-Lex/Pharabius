"""Tests for v3.10.0 — Candidate Promotion Execution.

First mutation wave: promotes eligible candidates to accepted findings.
Requires gate pass, preserves lineage, append-only audit, duplicate guard.

Key invariants:
- Promotion must be explicit
- Promotion must require gate pass
- Promotion must preserve candidate lineage
- Promotion must not delete candidate-findings.json
- Promotion must not auto-generate work packages or tickets
- One promotion per candidate
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pharabius.core.connectors.candidate import write_candidate_artifact
from pharabius.core.connectors.candidate_promotion import (
    PromotionError,
    promote_candidate,
)
from pharabius.core.connectors.candidate_review import review_candidate
from pharabius.schemas.candidate import (
    CandidateFinding,
    CandidateFindingsArtifact,
    CandidateFindingsSummary,
    CandidateProvenance,
)
from pharabius.schemas.review import DecisionStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_candidate(
    candidate_id: str = "CAND-0001",
    connector_name: str = "trivy",
    category: str = "TD-VULN",
) -> CandidateFinding:
    return CandidateFinding(
        id=candidate_id,
        category=category,
        title=f"Test vulnerability {candidate_id}",
        description="A real security issue that needs addressing.",
        severity="High",
        confidence="Medium",
        locations=["src/main.py:42"],
        evidence_ids=["EXT-001"],
        provenance=CandidateProvenance(
            connector_name=connector_name,
            source_format=connector_name,
            evidence_count=1,
            evidence_ids=["EXT-001"],
            source_types=["external_scanner_result"],
        ),
    )


def _setup_workspace(
    tmp_path: Path,
    *candidates: CandidateFinding,
) -> Path:
    from collections import Counter

    by_connector = dict(Counter(c.provenance.connector_name for c in candidates))
    by_category = dict(Counter(c.category for c in candidates))
    summary = CandidateFindingsSummary(
        total_candidates=len(candidates),
        by_connector=by_connector,
        by_category=by_category,
    )
    artifact = CandidateFindingsArtifact(candidates=list(candidates), summary=summary)
    write_candidate_artifact(artifact, tmp_path)
    return tmp_path


def _fully_review(
    tmp_path: Path,
    candidate_id: str = "CAND-0001",
    reviewer: str = "alice",
    rationale: str = "Confirmed real vulnerability",
) -> None:
    review_candidate(
        tmp_path,
        candidate_id,
        DecisionStatus.ACCEPTED,
        reviewer=reviewer,
        rationale=rationale,
    )


# ---------------------------------------------------------------------------
# S01: Successful promotion
# ---------------------------------------------------------------------------


class TestSuccessfulPromotion:
    """Eligible candidate can be promoted to accepted finding."""

    def test_promotion_returns_debt_finding(self, tmp_path: Path) -> None:
        from pharabius.schemas.finding import DebtFinding

        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        _fully_review(tmp_path, "CAND-0001")

        result = promote_candidate(tmp_path, "CAND-0001")
        assert isinstance(result, DebtFinding)
        assert result.status == "Detected"
        assert result.issue_type == "technical_debt"

    def test_promotion_writes_to_debt_register(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        _fully_review(tmp_path, "CAND-0001")

        promote_candidate(tmp_path, "CAND-0001")

        reg_path = tmp_path / ".ai-debt" / "debt-register.json"
        assert reg_path.exists()
        reg = json.loads(reg_path.read_text())
        assert reg["summary"]["total_findings"] == 1

    def test_promotion_generates_finding_id(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001", category="TD-VULN"))
        _fully_review(tmp_path, "CAND-0001")

        result = promote_candidate(tmp_path, "CAND-0001")
        assert result.id.startswith("TD-VULN-")
        assert result.id != "CAND-0001"

    def test_promotion_preserves_title_and_description(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        _fully_review(tmp_path, "CAND-0001")

        result = promote_candidate(tmp_path, "CAND-0001")
        assert "Test vulnerability" in result.title

    def test_promotion_preserves_category(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001", category="TD-DEP"))
        _fully_review(tmp_path, "CAND-0001")

        result = promote_candidate(tmp_path, "CAND-0001")
        assert result.category == "TD-DEP"

    def test_promotion_preserves_evidence_ids(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        _fully_review(tmp_path, "CAND-0001")

        result = promote_candidate(tmp_path, "CAND-0001")
        assert "EXT-001" in result.evidence_ids


# ---------------------------------------------------------------------------
# S03: Gate requirement
# ---------------------------------------------------------------------------


class TestGateRequirement:
    """Promotion requires passing all gate checks."""

    def test_no_review_decision_fails(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        with pytest.raises(PromotionError, match="gate failed"):
            promote_candidate(tmp_path, "CAND-0001")

    def test_rejected_decision_fails(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(tmp_path, "CAND-0001", DecisionStatus.REJECTED, reviewer="bob")
        with pytest.raises(PromotionError, match="gate failed"):
            promote_candidate(tmp_path, "CAND-0001")

    def test_no_reviewer_fails(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        review_candidate(
            tmp_path, "CAND-0001", DecisionStatus.ACCEPTED, reviewer="", rationale="Good"
        )
        with pytest.raises(PromotionError, match="gate failed"):
            promote_candidate(tmp_path, "CAND-0001")


# ---------------------------------------------------------------------------
# S04: Lineage metadata
# ---------------------------------------------------------------------------


class TestLineageMetadata:
    """Promoted finding carries candidate lineage."""

    def test_lineage_in_risk_breakdown(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        _fully_review(tmp_path, "CAND-0001")

        result = promote_candidate(tmp_path, "CAND-0001")
        assert "_promotion_lineage" in result.risk_breakdown
        lineage = result.risk_breakdown["_promotion_lineage"]
        assert lineage["candidate_id"] == "CAND-0001"
        assert lineage["source"] == "candidate_promotion"

    def test_lineage_preserves_connector(self, tmp_path: Path) -> None:
        _setup_workspace(
            tmp_path,
            _make_candidate("CAND-0001", connector_name="semgrep"),
        )
        _fully_review(tmp_path, "CAND-0001")

        result = promote_candidate(tmp_path, "CAND-0001")
        lineage = result.risk_breakdown["_promotion_lineage"]
        assert lineage["connector_name"] == "semgrep"

    def test_lineage_preserves_reviewer(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        _fully_review(tmp_path, "CAND-0001", reviewer="bob")

        result = promote_candidate(tmp_path, "CAND-0001")
        lineage = result.risk_breakdown["_promotion_lineage"]
        assert lineage["reviewer"] == "bob"

    def test_lineage_preserves_promoted_at(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        _fully_review(tmp_path, "CAND-0001")

        result = promote_candidate(tmp_path, "CAND-0001")
        lineage = result.risk_breakdown["_promotion_lineage"]
        assert "promoted_at" in lineage


# ---------------------------------------------------------------------------
# S05: Lifecycle history appended
# ---------------------------------------------------------------------------


class TestLifecycleHistory:
    """Promotion appends lifecycle entry."""

    def test_lifecycle_entry_created(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        _fully_review(tmp_path, "CAND-0001")

        promote_candidate(tmp_path, "CAND-0001")

        lh_path = tmp_path / ".ai-debt" / "lifecycle-history.json"
        assert lh_path.exists()
        history = json.loads(lh_path.read_text())
        # Should have review entry + promotion entry
        assert len(history["entries"]) >= 1
        promotion_entries = [
            e for e in history["entries"] if e["artifact_type"] == "candidate_promotion"
        ]
        assert len(promotion_entries) == 1
        assert promotion_entries[0]["from_status"] == "CandidateAccepted"
        assert promotion_entries[0]["to_status"] == "Detected"


# ---------------------------------------------------------------------------
# S06: Duplicate promotion guard
# ---------------------------------------------------------------------------


class TestDuplicatePromotionGuard:
    """Each candidate can only be promoted once."""

    def test_second_promotion_fails(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        _fully_review(tmp_path, "CAND-0001")

        promote_candidate(tmp_path, "CAND-0001")

        with pytest.raises(PromotionError, match="already promoted"):
            promote_candidate(tmp_path, "CAND-0001")

    def test_register_not_duplicated(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        _fully_review(tmp_path, "CAND-0001")

        promote_candidate(tmp_path, "CAND-0001")

        reg = json.loads((tmp_path / ".ai-debt" / "debt-register.json").read_text())
        assert reg["summary"]["total_findings"] == 1


# ---------------------------------------------------------------------------
# Non-mutation guarantees
# ---------------------------------------------------------------------------


class TestCandidateArtifactPreserved:
    """Promotion does not delete or rewrite candidate-findings.json."""

    def test_candidate_artifact_unchanged(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        _fully_review(tmp_path, "CAND-0001")

        cand_path = tmp_path / ".ai-debt" / "candidate-findings.json"
        orig = cand_path.read_text()

        promote_candidate(tmp_path, "CAND-0001")

        assert cand_path.exists()
        assert cand_path.read_text() == orig

    def test_candidate_still_listed(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        _fully_review(tmp_path, "CAND-0001")

        promote_candidate(tmp_path, "CAND-0001")

        cand = json.loads((tmp_path / ".ai-debt" / "candidate-findings.json").read_text())
        assert len(cand["candidates"]) == 1


class TestNoWorkPackagesOrTickets:
    """Promotion does not auto-generate work packages or tickets."""

    def test_no_work_packages(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        _fully_review(tmp_path, "CAND-0001")

        promote_candidate(tmp_path, "CAND-0001")

        assert not (tmp_path / ".ai-debt" / "work-packages").exists()


class TestReviewDecisionsPreserved:
    """Promotion does not rewrite review decisions."""

    def test_review_sidecar_unchanged(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        _fully_review(tmp_path, "CAND-0001")

        sidecar = tmp_path / ".ai-debt" / "review" / "decisions.json"
        orig = sidecar.read_text()

        promote_candidate(tmp_path, "CAND-0001")

        assert sidecar.read_text() == orig


# ---------------------------------------------------------------------------
# Summary recalculation
# ---------------------------------------------------------------------------


class TestSummaryRecalculation:
    """Register summary recalculated after promotion."""

    def test_summary_reflects_promoted_finding(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        _fully_review(tmp_path, "CAND-0001")

        promote_candidate(tmp_path, "CAND-0001")

        reg = json.loads((tmp_path / ".ai-debt" / "debt-register.json").read_text())
        assert reg["summary"]["total_findings"] == 1
        assert reg["summary"]["technical_debt_count"] == 1

    def test_multiple_promotions(self, tmp_path: Path) -> None:
        _setup_workspace(
            tmp_path,
            _make_candidate("CAND-0001"),
            _make_candidate("CAND-0002"),
        )
        _fully_review(tmp_path, "CAND-0001")
        _fully_review(tmp_path, "CAND-0002")

        promote_candidate(tmp_path, "CAND-0001")
        promote_candidate(tmp_path, "CAND-0002")

        reg = json.loads((tmp_path / ".ai-debt" / "debt-register.json").read_text())
        assert reg["summary"]["total_findings"] == 2


# ---------------------------------------------------------------------------
# Finding ID generation
# ---------------------------------------------------------------------------


class TestFindingIDGeneration:
    """Finding IDs are unique and sequential."""

    def test_first_id_is_001(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001", category="TD-VULN"))
        _fully_review(tmp_path, "CAND-0001")

        result = promote_candidate(tmp_path, "CAND-0001")
        assert result.id == "TD-VULN-001"

    def test_second_id_is_002(self, tmp_path: Path) -> None:
        _setup_workspace(
            tmp_path,
            _make_candidate("CAND-0001", category="TD-VULN"),
            _make_candidate("CAND-0002", category="TD-VULN"),
        )
        _fully_review(tmp_path, "CAND-0001")
        _fully_review(tmp_path, "CAND-0002")

        promote_candidate(tmp_path, "CAND-0001")
        result = promote_candidate(tmp_path, "CAND-0002")
        assert result.id == "TD-VULN-002"


# ---------------------------------------------------------------------------
# Existing register preserved
# ---------------------------------------------------------------------------


class TestExistingRegisterPreserved:
    """Promotion appends to existing register, doesn't overwrite."""

    def test_existing_findings_preserved(self, tmp_path: Path) -> None:
        _setup_workspace(tmp_path, _make_candidate("CAND-0001"))
        _fully_review(tmp_path, "CAND-0001")

        # Pre-populate debt-register with existing finding
        ai_debt = tmp_path / ".ai-debt"
        existing = {
            "schema_version": "1.0",
            "project_name": "test",
            "summary": {"total_findings": 1, "critical": 0, "high": 1, "medium": 0, "low": 0},
            "findings": [
                {
                    "id": "TD-ARCH-001",
                    "category": "TD-ARCH",
                    "title": "Existing",
                    "description": "Pre-existing finding",
                    "technical_impact": "Test",
                    "business_impact": "Test",
                    "risk_score": 25,
                    "priority": "High",
                    "recommended_action": "Test",
                }
            ],
        }
        (ai_debt / "debt-register.json").write_text(json.dumps(existing))

        promote_candidate(tmp_path, "CAND-0001")

        reg = json.loads((ai_debt / "debt-register.json").read_text())
        assert reg["summary"]["total_findings"] == 2
        ids = [f["id"] for f in reg["findings"]]
        assert "TD-ARCH-001" in ids
