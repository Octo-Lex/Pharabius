"""Tests for portfolio repository aggregation (W45-S02)."""

from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.portfolio import (
    collect_portfolio_repository_entries,
    extract_repository_entry,
)


def _write_debt_register(
    repo: Path,
    project_name: str = "test-project",
    branch: str = "main",
    commit: str = "abc123",
    findings: list[dict] | None = None,
    summary: dict | None = None,
) -> None:
    ai_debt = repo / ".ai-debt"
    ai_debt.mkdir(parents=True, exist_ok=True)
    register = {
        "schema_version": "1.0",
        "project_name": project_name,
        "repository": project_name,
        "commit": commit,
        "branch": branch,
        "generated_at": "2026-05-24T00:00:00Z",
        "summary": summary
        or {"total_findings": len(findings or []), "high": 0, "medium": 0, "low": 0},
        "findings": findings or [],
    }
    (ai_debt / "debt-register.json").write_text(json.dumps(register), encoding="utf-8")


def _write_ticket_drafts(repo: Path) -> None:
    td = repo / ".ai-debt" / "ticket-drafts"
    td.mkdir(parents=True, exist_ok=True)
    (td / "ticket-drafts.json").write_text("[]", encoding="utf-8")


def _write_export_manifest(repo: Path) -> None:
    eb = repo / ".ai-debt" / "export-bundles"
    eb.mkdir(parents=True, exist_ok=True)
    (eb / "manifest.json").write_text("{}", encoding="utf-8")


class TestSingleRepository:
    def test_extracts_entry(self, tmp_path: Path) -> None:
        repo = tmp_path / "alpha"
        _write_debt_register(
            repo,
            "alpha",
            findings=[
                {"category": "TD-ARCH", "priority": "High"},
                {"category": "TD-DEP", "priority": "Low"},
            ],
        )
        entry = extract_repository_entry(repo)
        assert entry is not None
        assert entry.project_name == "alpha"
        assert entry.total_findings == 2
        assert "TD-ARCH" in entry.top_categories

    def test_empty_findings(self, tmp_path: Path) -> None:
        repo = tmp_path / "empty"
        _write_debt_register(repo, "empty")
        entry = extract_repository_entry(repo)
        assert entry is not None
        assert entry.total_findings == 0
        assert entry.validation_status == "complete"


class TestMissingArtifacts:
    def test_missing_ai_debt(self, tmp_path: Path) -> None:
        warnings: list[str] = []
        entry = extract_repository_entry(tmp_path / "nada", warnings)
        assert entry is None
        assert any("Missing .ai-debt/" in w for w in warnings)

    def test_missing_debt_register(self, tmp_path: Path) -> None:
        repo = tmp_path / "partial"
        (repo / ".ai-debt").mkdir(parents=True)
        warnings: list[str] = []
        entry = extract_repository_entry(repo, warnings)
        assert entry is not None
        assert entry.validation_status == "needs_review"
        assert any("Missing debt-register" in w for w in warnings)

    def test_malformed_debt_register(self, tmp_path: Path) -> None:
        repo = tmp_path / "bad"
        ai = repo / ".ai-debt"
        ai.mkdir(parents=True)
        (ai / "debt-register.json").write_text("{bad json", encoding="utf-8")
        warnings: list[str] = []
        entry = extract_repository_entry(repo, warnings)
        assert entry is not None
        assert entry.validation_status == "needs_review"
        assert any("Malformed" in w for w in warnings)


class TestTicketAndExportDetection:
    def test_detects_ticket_drafts(self, tmp_path: Path) -> None:
        repo = tmp_path / "tickets"
        _write_debt_register(repo, "tickets")
        _write_ticket_drafts(repo)
        entry = extract_repository_entry(repo)
        assert entry is not None
        assert entry.has_ticket_drafts is True

    def test_no_ticket_drafts(self, tmp_path: Path) -> None:
        repo = tmp_path / "notickets"
        _write_debt_register(repo, "notickets")
        entry = extract_repository_entry(repo)
        assert entry is not None
        assert entry.has_ticket_drafts is False

    def test_detects_export_bundles(self, tmp_path: Path) -> None:
        repo = tmp_path / "exports"
        _write_debt_register(repo, "exports")
        _write_export_manifest(repo)
        entry = extract_repository_entry(repo)
        assert entry is not None
        assert entry.has_export_bundles is True


class TestMultipleRepositories:
    def test_collects_multiple(self, tmp_path: Path) -> None:
        r1 = tmp_path / "alpha"
        r2 = tmp_path / "beta"
        _write_debt_register(
            r1,
            "alpha",
            findings=[
                {"category": "TD-ARCH", "priority": "High"},
            ],
        )
        _write_debt_register(
            r2,
            "beta",
            findings=[
                {"category": "TD-DEP", "priority": "Low"},
            ],
        )
        entries = collect_portfolio_repository_entries([r1, r2])
        assert len(entries) == 2
        assert entries[0].repository_id == "alpha"
        assert entries[1].repository_id == "beta"

    def test_deduplication_by_id(self, tmp_path: Path) -> None:
        repo = tmp_path / "dup"
        _write_debt_register(repo, "dup")
        warnings: list[str] = []
        entries = collect_portfolio_repository_entries([repo, repo], warnings)
        assert len(entries) == 1
        assert any("Duplicate" in w for w in warnings)

    def test_deterministic_ordering(self, tmp_path: Path) -> None:
        names = ["charlie", "alpha", "beta"]
        for n in names:
            _write_debt_register(tmp_path / n, n)
        entries = collect_portfolio_repository_entries([tmp_path / n for n in reversed(names)])
        ids = [e.repository_id for e in entries]
        assert ids == sorted(ids)


class TestPriorityExtraction:
    def test_highest_priority(self, tmp_path: Path) -> None:
        repo = tmp_path / "pri"
        _write_debt_register(
            repo,
            "pri",
            summary={
                "total_findings": 3,
                "high": 1,
                "medium": 1,
                "low": 1,
            },
        )
        entry = extract_repository_entry(repo)
        assert entry is not None
        assert entry.highest_priority == "High"

    def test_no_priority(self, tmp_path: Path) -> None:
        repo = tmp_path / "nopri"
        _write_debt_register(repo, "nopri")
        entry = extract_repository_entry(repo)
        assert entry is not None
        assert entry.highest_priority is None


class TestNoMutation:
    def test_does_not_modify_debt_register(self, tmp_path: Path) -> None:
        repo = tmp_path / "safe"
        _write_debt_register(
            repo,
            "safe",
            findings=[
                {"category": "TD-ARCH", "priority": "High"},
            ],
        )
        dr_path = repo / ".ai-debt" / "debt-register.json"
        before = dr_path.read_text(encoding="utf-8")
        extract_repository_entry(repo)
        assert dr_path.read_text(encoding="utf-8") == before
