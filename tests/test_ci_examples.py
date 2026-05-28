"""Tests for CI example validation (v2.0.1 S01)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CI_DIR = REPO_ROOT / "docs" / "ci"


class TestCIExamplesExist:
    def test_github_actions_exists(self) -> None:
        assert (CI_DIR / "github-actions.md").exists()

    def test_gitlab_ci_exists(self) -> None:
        assert (CI_DIR / "gitlab-ci.md").exists()

    def test_azure_pipelines_exists(self) -> None:
        assert (CI_DIR / "azure-pipelines.md").exists()

    def test_jenkins_exists(self) -> None:
        assert (CI_DIR / "jenkins.md").exists()

    def test_portable_shell_exists(self) -> None:
        assert (CI_DIR / "portable-shell.md").exists()


class TestCIExamplesIncludeGate:
    def test_github_actions_includes_gate(self) -> None:
        content = (CI_DIR / "github-actions.md").read_text(encoding="utf-8")
        assert "ai-debt gate" in content

    def test_gitlab_ci_includes_gate(self) -> None:
        content = (CI_DIR / "gitlab-ci.md").read_text(encoding="utf-8")
        assert "ai-debt gate" in content

    def test_azure_pipelines_includes_gate(self) -> None:
        content = (CI_DIR / "azure-pipelines.md").read_text(encoding="utf-8")
        assert "ai-debt gate" in content

    def test_jenkins_includes_gate(self) -> None:
        content = (CI_DIR / "jenkins.md").read_text(encoding="utf-8")
        assert "ai-debt gate" in content

    def test_portable_shell_includes_gate(self) -> None:
        content = (CI_DIR / "portable-shell.md").read_text(encoding="utf-8")
        assert "ai-debt gate" in content


class TestCIExamplesNoDefaultExternalUpload:
    def test_github_actions_no_default_upload(self) -> None:
        """SARIF upload must be commented out or clearly opt-in."""
        content = (CI_DIR / "github-actions.md").read_text(encoding="utf-8")
        lines = content.splitlines()
        for line in lines:
            if "upload-sarif" in line and "codeql" in line:
                assert line.strip().startswith("#"), f"upload-sarif must be commented out: {line}"

    def test_gitlab_ci_no_external_write(self) -> None:
        content = (CI_DIR / "gitlab-ci.md").read_text(encoding="utf-8")
        assert "curl" not in content
        assert "wget" not in content

    def test_azure_pipelines_no_external_write(self) -> None:
        content = (CI_DIR / "azure-pipelines.md").read_text(encoding="utf-8")
        assert "curl" not in content
        assert "wget" not in content

    def test_jenkins_no_external_write(self) -> None:
        content = (CI_DIR / "jenkins.md").read_text(encoding="utf-8")
        assert "curl" not in content
        assert "wget" not in content


class TestCIExamplesNoCredentials:
    def test_github_actions_no_secrets(self) -> None:
        content = (CI_DIR / "github-actions.md").read_text(encoding="utf-8")
        for pattern in ["password", "secret", "token", "api_key"]:
            assert pattern not in content.lower() or "no tokens" in content.lower(), (
                f"Found potential credential reference: {pattern}"
            )

    def test_gitlab_ci_no_secrets(self) -> None:
        content = (CI_DIR / "gitlab-ci.md").read_text(encoding="utf-8")
        for pattern in ["password", "secret", "api_key"]:
            assert pattern not in content.lower() or "no tokens" in content.lower()

    def test_azure_pipelines_no_secrets(self) -> None:
        content = (CI_DIR / "azure-pipelines.md").read_text(encoding="utf-8")
        for pattern in ["password", "secret", "api_key"]:
            assert pattern not in content.lower() or "no tokens" in content.lower()

    def test_jenkins_no_secrets(self) -> None:
        content = (CI_DIR / "jenkins.md").read_text(encoding="utf-8")
        for pattern in ["password", "secret", "api_key"]:
            assert pattern not in content.lower() or "no tokens" in content.lower()

    def test_portable_shell_no_secrets(self) -> None:
        content = (CI_DIR / "portable-shell.md").read_text(encoding="utf-8")
        for pattern in ["password", "secret", "api_key"]:
            assert pattern not in content.lower() or "no tokens" in content.lower()


class TestCIExamplesArchiveReports:
    def test_gitlab_ci_archives_reports(self) -> None:
        content = (CI_DIR / "gitlab-ci.md").read_text(encoding="utf-8")
        assert "artifacts" in content
        assert ".ai-debt" in content

    def test_azure_pipelines_publishes_artifacts(self) -> None:
        content = (CI_DIR / "azure-pipelines.md").read_text(encoding="utf-8")
        assert "PublishBuildArtifacts" in content or "publish" in content.lower()

    def test_jenkins_archives_artifacts(self) -> None:
        content = (CI_DIR / "jenkins.md").read_text(encoding="utf-8")
        assert "archiveArtifacts" in content

    def test_github_actions_uploads_artifact(self) -> None:
        content = (CI_DIR / "github-actions.md").read_text(encoding="utf-8")
        assert "upload-artifact" in content


class TestPortableShellSyntax:
    def test_uses_strict_mode(self) -> None:
        content = (CI_DIR / "portable-shell.md").read_text(encoding="utf-8")
        assert "set -euo pipefail" in content

    def test_uses_env_var_defaults(self) -> None:
        content = (CI_DIR / "portable-shell.md").read_text(encoding="utf-8")
        assert "${MAX_CRITICAL:-" in content or "MAX_CRITICAL" in content
