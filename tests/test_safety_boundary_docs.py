"""Tests for safety boundary documentation audit (W51-S03)."""

from __future__ import annotations

from pathlib import Path

DOCS = Path("docs")
SAFETY = DOCS / "SAFETY_BOUNDARIES.md"


class TestSafetyDocExists:
    def test_safety_boundaries_exists(self) -> None:
        assert SAFETY.exists()


class TestSafetyBoundaryPhrases:
    def test_no_code_modification(self) -> None:
        text = SAFETY.read_text()
        assert "code modification" in text.lower()

    def test_no_autonomous_remediation(self) -> None:
        text = SAFETY.read_text()
        assert "autonomous remediation" in text.lower()

    def test_no_external_writes(self) -> None:
        text = SAFETY.read_text()
        assert "external" in text.lower() and "writes" in text.lower()

    def test_no_issue_creation(self) -> None:
        text = SAFETY.read_text()
        assert "issue creation" in text.lower() or "does not create issues" in text.lower()

    def test_no_remote_crawling(self) -> None:
        text = SAFETY.read_text()
        assert "remote" in text.lower() and "crawling" in text.lower()

    def test_human_ownership(self) -> None:
        text = SAFETY.read_text()
        assert "human" in text.lower()


class TestCommandClassifications:
    def test_all_commands_classified(self) -> None:
        text = SAFETY.read_text()
        commands = [
            "init", "profile", "scan", "map-units", "analyze", "report",
            "plan", "verify", "status", "graph", "export", "enrich",
            "ai-status", "run", "review", "tickets", "portfolio", "doctor",
        ]
        for cmd in commands:
            assert cmd in text, f"Command '{cmd}' not classified in safety doc"


class TestLinkedDocsBoundaries:
    def test_export_docs_no_api_writes(self) -> None:
        text = (DOCS / "EXPORT_BUNDLES.md").read_text()
        assert "no api" in text.lower() or "does not" in text.lower() or "local" in text.lower()

    def test_portfolio_docs_no_remote(self) -> None:
        text = (DOCS / "PORTFOLIO.md").read_text()
        assert "remote" in text.lower() or "local" in text.lower()

    def test_ticket_docs_local_only(self) -> None:
        text = (DOCS / "TICKET_DRAFTS.md").read_text()
        assert "local" in text.lower()
