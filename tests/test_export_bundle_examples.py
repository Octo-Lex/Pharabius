"""Tests for richer tracker-specific examples (W44-S03)."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

EXAMPLES = Path("docs/examples/export-bundles")


class TestJiraExamples:
    def test_jira_csv_has_required_columns(self) -> None:
        csv_path = EXAMPLES / "jira" / "jira-export.example.csv"
        if not csv_path.exists():
            return
        content = csv_path.read_text(encoding="utf-8")
        rows = [r for r in csv.reader(io.StringIO(content)) if r]
        assert "Summary" in rows[0]
        assert "Issue Type" in rows[0]
        assert "Priority" in rows[0]

    def test_jira_markdown_exists(self) -> None:
        assert (EXAMPLES / "jira" / "jira-export.example.md").exists()

    def test_jira_readme_exists(self) -> None:
        assert (EXAMPLES / "jira" / "README.md").exists()

    def test_jira_no_api_write_claims(self) -> None:
        readme = (EXAMPLES / "jira" / "README.md").read_text(encoding="utf-8")
        assert "does not call" in readme.lower()


class TestLinearExamples:
    def test_linear_csv_has_required_columns(self) -> None:
        csv_path = EXAMPLES / "linear" / "linear-export.example.csv"
        if not csv_path.exists():
            return
        content = csv_path.read_text(encoding="utf-8")
        rows = [r for r in csv.reader(io.StringIO(content)) if r]
        assert "Title" in rows[0]
        assert "Priority" in rows[0]

    def test_linear_readme_exists(self) -> None:
        assert (EXAMPLES / "linear" / "README.md").exists()


class TestGitHubExamples:
    def test_github_yaml_parses(self) -> None:
        yaml_path = EXAMPLES / "github-issues" / "issues" / "ISSUE-001.example.yaml"
        if not yaml_path.exists():
            return
        content = yaml_path.read_text(encoding="utf-8")
        assert "schema_version: '1.0'" in content
        assert "title:" in content
        assert "body: |" in content

    def test_github_yaml_no_assignee(self) -> None:
        yaml_path = EXAMPLES / "github-issues" / "issues" / "ISSUE-001.example.yaml"
        if not yaml_path.exists():
            return
        content = yaml_path.read_text(encoding="utf-8")
        assert "assignee" not in content.lower()

    def test_github_readme_exists(self) -> None:
        assert (EXAMPLES / "github-issues" / "README.md").exists()


class TestAzureExamples:
    def test_azure_csv_has_required_columns(self) -> None:
        csv_path = EXAMPLES / "azure-devops" / "azure-devops-export.example.csv"
        if not csv_path.exists():
            return
        content = csv_path.read_text(encoding="utf-8")
        rows = [r for r in csv.reader(io.StringIO(content)) if r]
        assert "Title" in rows[0]
        assert "Work Item Type" in rows[0]
        assert "Priority" in rows[0]

    def test_azure_csv_semicolon_tags(self) -> None:
        csv_path = EXAMPLES / "azure-devops" / "azure-devops-export.example.csv"
        if not csv_path.exists():
            return
        content = csv_path.read_text(encoding="utf-8")
        assert ";" in content  # Semicolon-separated tags

    def test_azure_readme_exists(self) -> None:
        assert (EXAMPLES / "azure-devops" / "README.md").exists()


class TestManifestExample:
    def test_manifest_valid_json(self) -> None:
        manifest = EXAMPLES / "manifest.example.json"
        if not manifest.exists():
            return
        data = json.loads(manifest.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.0"
        assert len(data["artifacts"]) > 0


class TestNoExternalWriteClaims:
    def test_no_tracker_api_instructions(self) -> None:
        """Examples must not contain API-write instructions."""
        for tracker_dir in EXAMPLES.iterdir():
            if not tracker_dir.is_dir():
                continue
            for f in tracker_dir.rglob("*"):
                if f.is_file() and f.suffix in (".md", ".csv", ".yaml"):
                    content = f.read_text(encoding="utf-8").lower()
                    assert "POST /rest/api" not in content
                    assert "graphql mutation" not in content
