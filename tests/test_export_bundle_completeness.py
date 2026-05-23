"""Tests for tracker bundle completeness checks (W44-S02)."""

from __future__ import annotations

from pathlib import Path

from pharabius.core.export_bundle_validation import (
    check_all_tracker_bundles,
    check_tracker_bundle_completeness,
)


def _make_tracker_dir(
    tmp_path: Path,
    tracker: str,
    files: dict[str, str] | None = None,
    csv_content: str | None = None,
    yaml_files: dict[str, str] | None = None,
) -> Path:
    d = tmp_path / ".ai-debt" / "export-bundles"
    td = d / tracker
    td.mkdir(parents=True, exist_ok=True)
    if files:
        for name, content in files.items():
            (td / name).write_text(content, encoding="utf-8")
    if csv_content is not None and files:
        for name in files:
            if name.endswith(".csv"):
                (td / name).write_text(csv_content, encoding="utf-8")
    if yaml_files:
        issues_dir = td / "issues"
        issues_dir.mkdir(exist_ok=True)
        for name, content in yaml_files.items():
            (issues_dir / name).write_text(content, encoding="utf-8")
    return d


JIRA_FILES = {
    "README.md": "# Jira Export Bundle\n",
    "jira-ticket-drafts.md": "# Jira Ticket Draft Export\n",
    "jira-ticket-drafts.csv": (
        "Summary,Issue Type,Description,Priority,Labels,"
        "Linked Findings,Work Package,Source Ticket Draft,"
        "Review Decision,Completeness\n"
        "Fix auth,Task,Fix the boundary,High,TD-ARCH,"
        "TD-ARCH-001,WP-001,.md,accepted,complete\n"
    ),
}

LINEAR_FILES = {
    "README.md": "# Linear Export Bundle\n",
    "linear-ticket-drafts.md": "# Linear Ticket Draft Export\n",
    "linear-ticket-drafts.csv": (
        "Title,Description,Priority,Labels,"
        "Linked Findings,Work Package,Source Ticket Draft,"
        "Review Decision,Completeness\n"
        "Fix auth,Fix the boundary.,High,TD-ARCH,"
        "TD-ARCH-001,WP-001,.md,accepted,complete\n"
    ),
}

AZURE_FILES = {
    "README.md": "# Azure DevOps Export Bundle\n",
    "azure-devops-ticket-drafts.md": "# Azure DevOps Ticket Draft Export\n",
    "azure-devops-ticket-drafts.csv": (
        "Title,Work Item Type,Description,Priority,Tags,"
        "Linked Findings,Work Package,Source Ticket Draft,"
        "Review Decision,Completeness\n"
        "Fix auth,User Story,Fix the boundary.,High,TD-ARCH,"
        "TD-ARCH-001,WP-001,.md,accepted,complete\n"
    ),
}

GITHUB_FILES = {
    "README.md": "# GitHub Issues Export Bundle\n",
    "github-issues-ticket-drafts.md": "# GitHub Issues Ticket Draft Export\n",
}

GITHUB_YAML = {
    "TICKET-WP-001.yaml": (
        "schema_version: '1.0'\ntitle: 'Fix auth'\nlabels:\n  - 'TD-ARCH'\n"
        "body: |\n  Fix the boundary.\n"
    ),
}


class TestJiraCompleteness:
    def test_complete_jira(self, tmp_path: Path) -> None:
        d = _make_tracker_dir(tmp_path, "jira", JIRA_FILES)
        result = check_tracker_bundle_completeness(d, "jira")
        assert result.status == "complete"
        assert not result.missing_artifacts

    def test_missing_readme(self, tmp_path: Path) -> None:
        files = {k: v for k, v in JIRA_FILES.items() if k != "README.md"}
        d = _make_tracker_dir(tmp_path, "jira", files)
        result = check_tracker_bundle_completeness(d, "jira")
        assert result.status == "needs_review"
        assert "README.md" in result.missing_artifacts

    def test_missing_csv(self, tmp_path: Path) -> None:
        files = {k: v for k, v in JIRA_FILES.items() if not k.endswith(".csv")}
        d = _make_tracker_dir(tmp_path, "jira", files)
        result = check_tracker_bundle_completeness(d, "jira")
        assert result.status == "needs_review"


class TestLinearCompleteness:
    def test_complete_linear(self, tmp_path: Path) -> None:
        d = _make_tracker_dir(tmp_path, "linear", LINEAR_FILES)
        result = check_tracker_bundle_completeness(d, "linear")
        assert result.status == "complete"


class TestGitHubCompleteness:
    def test_complete_github(self, tmp_path: Path) -> None:
        d = _make_tracker_dir(tmp_path, "github-issues", GITHUB_FILES, yaml_files=GITHUB_YAML)
        result = check_tracker_bundle_completeness(d, "github-issues")
        assert result.status == "complete"

    def test_empty_yaml_dir(self, tmp_path: Path) -> None:
        d = _make_tracker_dir(tmp_path, "github-issues", GITHUB_FILES)
        # Manually create empty issues dir
        (d / "github-issues" / "issues").mkdir(exist_ok=True)
        result = check_tracker_bundle_completeness(d, "github-issues")
        assert result.status == "partial"
        assert any("empty" in w.lower() for w in result.warnings)

    def test_yaml_missing_field(self, tmp_path: Path) -> None:
        bad_yaml = {"TICKET-WP-001.yaml": "schema_version: '1.0'\ntitle: 'Fix'\n"}
        d = _make_tracker_dir(tmp_path, "github-issues", GITHUB_FILES, yaml_files=bad_yaml)
        result = check_tracker_bundle_completeness(d, "github-issues")
        assert result.status == "partial"


class TestAzureCompleteness:
    def test_complete_azure(self, tmp_path: Path) -> None:
        d = _make_tracker_dir(tmp_path, "azure-devops", AZURE_FILES)
        result = check_tracker_bundle_completeness(d, "azure-devops")
        assert result.status == "complete"


class TestCheckAllTrackerBundles:
    def test_checks_all_present(self, tmp_path: Path) -> None:
        d = _make_tracker_dir(tmp_path, "jira", JIRA_FILES)
        _make_tracker_dir(tmp_path, "linear", LINEAR_FILES)
        _make_tracker_dir(tmp_path, "github-issues", GITHUB_FILES, yaml_files=GITHUB_YAML)
        _make_tracker_dir(tmp_path, "azure-devops", AZURE_FILES)
        results = check_all_tracker_bundles(d)
        assert len(results) == 4
        assert all(r.status == "complete" for r in results)

    def test_skips_missing_dirs(self, tmp_path: Path) -> None:
        d = _make_tracker_dir(tmp_path, "jira", JIRA_FILES)
        results = check_all_tracker_bundles(d)
        assert len(results) == 1
        assert results[0].tracker == "jira"


class TestDeterminism:
    def test_deterministic_status(self, tmp_path: Path) -> None:
        d = _make_tracker_dir(tmp_path, "jira", JIRA_FILES)
        r1 = check_tracker_bundle_completeness(d, "jira")
        r2 = check_tracker_bundle_completeness(d, "jira")
        assert r1.status == r2.status
        assert r1.missing_artifacts == r2.missing_artifacts
