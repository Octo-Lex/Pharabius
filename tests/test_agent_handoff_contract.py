"""Tests for agent-handoff contract artifact (W47-S04)."""

from __future__ import annotations

from pathlib import Path

from pharabius.core.agent_handoff import (
    render_agent_handoff_contract,
    write_agent_handoff_contract,
)
from pharabius.schemas.claims import GapItem, OperationalClaim


def _claim(
    claim_id: str = "CLM-000001",
    status: str = "confirmed",
    evidence_ids: list[str] | None = None,
    requires_hv: bool = False,
    question: str | None = None,
) -> OperationalClaim:
    return OperationalClaim(
        claim_id=claim_id,
        claim_type="architecture",
        statement="Test claim",
        status=status,  # type: ignore[arg-type]
        confidence="High" if status == "confirmed" else "Low",
        evidence_ids=evidence_ids or (["EVD-001"] if status == "confirmed" else []),
        linked_findings=["TD-001"],
        source="finding",
        requires_human_validation=requires_hv,
        validation_question=question,
    )


class TestContractStructure:
    def test_contains_safety_boundary(self) -> None:
        md = render_agent_handoff_contract([_claim()])
        assert "## Safety Boundary" in md
        assert "does not authorize" in md.lower()

    def test_contains_confirmed_claims(self) -> None:
        md = render_agent_handoff_contract([_claim(evidence_ids=["EVD-001"])])
        assert "## Reliable Context: Confirmed Claims" in md
        assert "CLM-000001" in md

    def test_contains_inferred_claims(self) -> None:
        md = render_agent_handoff_contract([_claim(status="inferred", evidence_ids=["EVD-001"])])
        assert "## Caution Context: Inferred Claims" in md
        assert "hypothesis" in md.lower()

    def test_contains_blocking_gaps(self) -> None:
        gaps = [
            GapItem(
                gap_id="GAP-0001", severity="blocking", question="Check?", reason="Missing evidence"
            )
        ]
        md = render_agent_handoff_contract([], gaps=gaps)
        assert "## Blocking Gaps" in md
        assert "GAP-0001" in md

    def test_contains_human_validation(self) -> None:
        claims = [_claim(requires_hv=True, question="Why?")]
        md = render_agent_handoff_contract(claims)
        assert "## Human Validation Required" in md

    def test_contains_forbidden_actions(self) -> None:
        md = render_agent_handoff_contract([_claim()])
        assert "## Forbidden Actions" in md
        assert "Do not modify production code" in md

    def test_contains_allowed_uses(self) -> None:
        md = render_agent_handoff_contract([_claim()])
        assert "## Allowed Uses" in md

    def test_contains_linked_artifacts(self) -> None:
        md = render_agent_handoff_contract([_claim()])
        assert "## Linked Artifacts" in md
        assert "operational-claims.json" in md


class TestContractSafety:
    def test_no_code_authorization_language(self) -> None:
        md = render_agent_handoff_contract([_claim()])
        assert "auto-fix" not in md.lower()
        assert "automatically modify" not in md.lower()

    def test_no_empty_sections(self) -> None:
        md = render_agent_handoff_contract([])
        assert "No confirmed claims." in md
        assert "No blocking gaps." in md


class TestContractWriter:
    def test_writes_file(self, tmp_path: Path) -> None:
        path = write_agent_handoff_contract(tmp_path / ".ai-debt", [_claim()])
        assert path.exists()
        assert path.name == "agent-handoff-contract.md"

    def test_creates_directory(self, tmp_path: Path) -> None:
        d = tmp_path / ".ai-debt"
        assert not d.exists()
        write_agent_handoff_contract(d, [_claim()])
        assert d.exists()


class TestContractDeterminism:
    def test_deterministic(self) -> None:
        claims = [
            _claim(claim_id="CLM-001"),
            _claim(claim_id="CLM-002", status="gap", question="Q?"),
        ]
        md1 = render_agent_handoff_contract(claims)
        md2 = render_agent_handoff_contract(claims)
        assert md1 == md2
