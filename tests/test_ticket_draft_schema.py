"""Tests for ticket draft schema and ID helpers (W41-S01)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pharabius.core.tickets import (
    ticket_filename,
    ticket_id_for_finding,
    ticket_id_for_work_package,
)
from pharabius.schemas.tickets import (
    TicketDraft,
    TicketDraftIndex,
    TicketDraftSourceArtifacts,
    TicketDraftSummary,
)

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "docs" / "examples"


# ── Schema validation tests ───────────────────────────────────────────


class TestTicketDraftSchema:
    def test_minimal_valid_draft(self) -> None:
        draft = TicketDraft(
            ticket_id="TICKET-WP-001",
            title="Test ticket",
            source_type="work_package",
            source_id="WP-001",
            artifact_path=".ai-debt/ticket-drafts/TICKET-WP-001.md",
        )
        assert draft.ticket_id == "TICKET-WP-001"
        assert draft.status == "draft"
        assert draft.review_decision == "not_reviewed"
        assert draft.external_system is None
        assert draft.external_id is None
        assert draft.linked_debt_items == []
        assert draft.labels == []

    def test_minimal_valid_index(self) -> None:
        idx = TicketDraftIndex(
            tool_version="1.6.0-dev",
            generated_at="2026-05-22T00:00:00Z",
            source_artifacts=TicketDraftSourceArtifacts(
                debt_register=".ai-debt/debt-register.json",
                work_packages_dir=".ai-debt/work-packages",
            ),
        )
        assert idx.schema_version == "1.0"
        assert idx.summary.total_drafts == 0
        assert idx.drafts == []

    def test_status_accepts_draft_and_excluded(self) -> None:
        d1 = TicketDraft(
            ticket_id="T-1",
            title="t",
            source_type="work_package",
            source_id="WP-001",
            artifact_path="a.md",
            status="draft",
        )
        d2 = TicketDraft(
            ticket_id="T-2",
            title="t",
            source_type="work_package",
            source_id="WP-002",
            artifact_path="b.md",
            status="excluded",
        )
        assert d1.status == "draft"
        assert d2.status == "excluded"

    def test_status_rejects_invalid(self) -> None:
        with pytest.raises(ValueError):
            TicketDraft(
                ticket_id="T-1",
                title="t",
                source_type="work_package",
                source_id="WP-001",
                artifact_path="a.md",
                status="invalid",
            )

    def test_source_type_accepts_work_package_and_finding(self) -> None:
        d1 = TicketDraft(
            ticket_id="T-1",
            title="t",
            source_type="work_package",
            source_id="WP-001",
            artifact_path="a.md",
        )
        d2 = TicketDraft(
            ticket_id="T-2",
            title="t",
            source_type="finding",
            source_id="TD-ARCH-001",
            artifact_path="b.md",
        )
        assert d1.source_type == "work_package"
        assert d2.source_type == "finding"

    def test_source_type_rejects_invalid(self) -> None:
        with pytest.raises(ValueError):
            TicketDraft(
                ticket_id="T-1",
                title="t",
                source_type="invalid",
                source_id="WP-001",
                artifact_path="a.md",
            )

    def test_external_system_always_none(self) -> None:
        draft = TicketDraft(
            ticket_id="T-1",
            title="t",
            source_type="work_package",
            source_id="WP-001",
            artifact_path="a.md",
        )
        assert draft.external_system is None
        assert draft.external_id is None

    def test_review_decision_default(self) -> None:
        draft = TicketDraft(
            ticket_id="T-1",
            title="t",
            source_type="work_package",
            source_id="WP-001",
            artifact_path="a.md",
        )
        assert draft.review_decision == "not_reviewed"

    def test_summary_defaults(self) -> None:
        s = TicketDraftSummary()
        assert s.total_drafts == 0
        assert s.included_drafts == 0
        assert s.excluded_by_review == 0
        assert s.unreviewed == 0

    def test_index_with_drafts(self) -> None:
        draft = TicketDraft(
            ticket_id="TICKET-WP-001",
            title="Test",
            source_type="work_package",
            source_id="WP-001",
            artifact_path="a.md",
            priority="High",
            risk_score=24,
        )
        idx = TicketDraftIndex(
            tool_version="1.6.0-dev",
            generated_at="2026-05-22T00:00:00Z",
            source_artifacts=TicketDraftSourceArtifacts(
                debt_register=".ai-debt/debt-register.json",
                work_packages_dir=".ai-debt/work-packages",
            ),
            summary=TicketDraftSummary(total_drafts=1, included_drafts=1),
            drafts=[draft],
        )
        assert len(idx.drafts) == 1
        assert idx.drafts[0].priority == "High"


# ── Deterministic ID tests ─────────────────────────────────────────────


class TestTicketIdHelpers:
    def test_wp_001_maps_to_ticket_wp_001(self) -> None:
        assert ticket_id_for_work_package("WP-001") == "TICKET-WP-001"

    def test_wp_002_maps_to_ticket_wp_002(self) -> None:
        assert ticket_id_for_work_package("WP-002") == "TICKET-WP-002"

    def test_finding_maps_to_ticket_finding(self) -> None:
        assert ticket_id_for_finding("TD-ARCH-001") == "TICKET-TD-ARCH-001"

    def test_ticket_filename(self) -> None:
        assert ticket_filename("TICKET-WP-001") == "TICKET-WP-001.md"

    def test_ids_are_deterministic(self) -> None:
        for _ in range(10):
            assert ticket_id_for_work_package("WP-001") == "TICKET-WP-001"
            assert ticket_filename("TICKET-WP-001") == "TICKET-WP-001.md"


# ── Example JSON validation ────────────────────────────────────────────


class TestExampleJSON:
    def test_example_json_is_valid(self) -> None:
        path = EXAMPLES_DIR / "ticket-drafts.example.json"
        if not path.exists():
            pytest.skip("Example JSON not found")
        data = json.loads(path.read_text(encoding="utf-8"))
        idx = TicketDraftIndex.model_validate(data)
        assert idx.schema_version == "1.0"
        assert len(idx.drafts) >= 1
        assert idx.drafts[0].ticket_id.startswith("TICKET-")
        assert idx.drafts[0].external_system is None

    def test_example_markdown_exists(self) -> None:
        path = EXAMPLES_DIR / "ticket-draft.example.md"
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "repository-local" in content.lower()
