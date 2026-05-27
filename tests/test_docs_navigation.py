"""Tests for documentation navigation (W48-S04)."""

from __future__ import annotations

from pathlib import Path

DOCS = Path("docs")
REQUIRED_DOCS = [
    "QUICKSTART.md",
    "CLI.md",
    "ARTIFACT_CONTRACT.md",
    "SCHEMA_MAP.md",
    "ADOPTION_GUIDE.md",
    "GOVERNANCE.md",
    "TICKET_DRAFTS.md",
    "EXPORT_BUNDLES.md",
    "PORTFOLIO.md",
    "OPERATIONAL_CLAIMS.md",
    "OPERATIONAL_CLAIMS_ADOPTION.md",
    "KNOWN_LIMITATIONS.md",
    "ROADMAP.md",
    "ARCHITECTURE.md",
]


class TestDocsExist:
    def test_all_required_docs_exist(self) -> None:
        for name in REQUIRED_DOCS:
            p = DOCS / name
            assert p.exists(), f"Missing doc: {name}"

    def test_all_required_docs_nonempty(self) -> None:
        for name in REQUIRED_DOCS:
            p = DOCS / name
            assert len(p.read_text().strip()) > 0, f"Empty doc: {name}"


class TestDocsIndex:
    def test_index_links_to_required_docs(self) -> None:
        index = (DOCS / "README.md").read_text()
        for name in REQUIRED_DOCS:
            # Check the filename appears (without path prefix)
            assert name in index, f"Docs index missing link: {name}"


class TestQuickstart:
    def test_has_command_sequence(self) -> None:
        qs = (DOCS / "QUICKSTART.md").read_text()
        assert "ai-debt init" in qs
        assert "ai-debt run" in qs

    def test_has_boundary_section(self) -> None:
        qs = (DOCS / "QUICKSTART.md").read_text()
        assert "Does not" in qs or "does not" in qs


class TestReadmeLinks:
    def test_readme_links_to_docs_index(self) -> None:
        readme = Path("README.md").read_text()
        assert "docs/README.md" in readme
        assert "QUICKSTART" in readme
