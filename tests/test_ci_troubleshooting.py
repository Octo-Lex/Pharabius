"""Tests for CI troubleshooting documentation (v2.0.1 S05)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestCITroubleshootingDoc:
    def test_doc_exists(self) -> None:
        assert (REPO_ROOT / "docs" / "CI_TROUBLESHOOTING.md").exists()

    def test_covers_exit_codes(self) -> None:
        content = (REPO_ROOT / "docs" / "CI_TROUBLESHOOTING.md").read_text(encoding="utf-8")
        assert "exit code" in content.lower()
        assert "exit 1" in content or "code 1" in content

    def test_covers_no_external_writes(self) -> None:
        content = (REPO_ROOT / "docs" / "CI_TROUBLESHOOTING.md").read_text(encoding="utf-8")
        assert "does not" in content.lower()
        assert "upload" in content.lower() or "SARIF" in content

    def test_covers_sarif_local_only(self) -> None:
        content = (REPO_ROOT / "docs" / "CI_TROUBLESHOOTING.md").read_text(encoding="utf-8")
        assert "does not upload SARIF by default" in content

    def test_mentions_doctor(self) -> None:
        content = (REPO_ROOT / "docs" / "CI_TROUBLESHOOTING.md").read_text(encoding="utf-8")
        assert "ai-debt doctor" in content

    def test_has_safe_recovery_commands(self) -> None:
        content = (REPO_ROOT / "docs" / "CI_TROUBLESHOOTING.md").read_text(encoding="utf-8")
        assert "ai-debt run" in content
        assert "ai-debt gate" in content

    def test_no_bypass_recommendations(self) -> None:
        content = (REPO_ROOT / "docs" / "CI_TROUBLESHOOTING.md").read_text(encoding="utf-8")
        # Should not recommend disabling safety
        assert "--no-gate" not in content
        assert "skip analysis" not in content.lower() or "Do not" in content

    def test_covers_quality_gate_failure(self) -> None:
        content = (REPO_ROOT / "docs" / "CI_TROUBLESHOOTING.md").read_text(encoding="utf-8")
        assert "Quality Gate Failed" in content or "gate failed" in content.lower()

    def test_covers_missing_artifacts(self) -> None:
        content = (REPO_ROOT / "docs" / "CI_TROUBLESHOOTING.md").read_text(encoding="utf-8")
        assert "Missing" in content
        assert "debt-register" in content or "artifact" in content.lower()
