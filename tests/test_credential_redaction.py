"""Credential redaction tests for v0.9.1.

Verifies that the sentinel API key never appears in any output channel.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from pharabius.cli import app

SENTINEL = "pharabius-test-key-DO-NOT-LEAK"


def _setup_repo(tmp_path: Path) -> Path:
    """Create a minimal .ai-debt repo with one finding."""
    ai = tmp_path / ".ai-debt"
    ai.mkdir()
    (ai / "evidence.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "evidence": [
                    {
                        "evidence_id": "EVD-001",
                        "type": "test",
                        "category": "test",
                        "summary": "test",
                        "location": {"file": "a.py"},
                        "raw_observation": "obs",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (ai / "debt-register.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "findings": [
                    {
                        "id": "TD-DEP-001",
                        "category": "TD-DEP",
                        "title": "Test finding",
                        "severity": "Medium",
                        "evidence_ids": ["EVD-001"],
                        "analysis_unit_ids": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


class TestCredentialRedaction:
    """Sentinel-based credential leak detection across all output channels."""

    def test_key_not_in_cli_stdout(self, tmp_path: Path) -> None:
        """Sentinel key must not appear in CLI stdout."""
        repo = _setup_repo(tmp_path)
        runner = CliRunner()
        with patch.dict(os.environ, {"PHARABIUS_OPENAI_API_KEY": SENTINEL}, clear=False):
            result = runner.invoke(app, ["enrich", "--provider", "mock", "-r", str(repo)])
        assert result.exit_code == 0
        assert SENTINEL not in result.output

    def test_key_not_in_sidecar_json(self, tmp_path: Path) -> None:
        """Sentinel key must not appear in sidecar JSON."""
        repo = _setup_repo(tmp_path)
        runner = CliRunner()
        with patch.dict(os.environ, {"PHARABIUS_OPENAI_API_KEY": SENTINEL}, clear=False):
            runner.invoke(app, ["enrich", "--provider", "mock", "-r", str(repo)])

        sidecar = repo / ".ai-debt" / "ai" / "enrichment-report.json"
        assert sidecar.exists()
        content = sidecar.read_text(encoding="utf-8")
        assert SENTINEL not in content

    def test_key_not_in_sidecar_markdown(self, tmp_path: Path) -> None:
        """Sentinel key must not appear in sidecar markdown."""
        repo = _setup_repo(tmp_path)
        runner = CliRunner()
        with patch.dict(os.environ, {"PHARABIUS_OPENAI_API_KEY": SENTINEL}, clear=False):
            runner.invoke(app, ["enrich", "--provider", "mock", "-r", str(repo)])

        md = repo / ".ai-debt" / "ai" / "enrichment-report.md"
        assert md.exists()
        content = md.read_text(encoding="utf-8")
        assert SENTINEL not in content

    def test_key_not_in_ai_status_text(self, tmp_path: Path) -> None:
        """Sentinel key must not appear in ai-status text output."""
        repo = _setup_repo(tmp_path)
        runner = CliRunner()
        with patch.dict(os.environ, {"PHARABIUS_OPENAI_API_KEY": SENTINEL}, clear=False):
            runner.invoke(app, ["enrich", "--provider", "mock", "-r", str(repo)])
            result = runner.invoke(app, ["ai-status", "-r", str(repo)])
        assert result.exit_code == 0
        assert SENTINEL not in result.output

    def test_key_not_in_ai_status_json(self, tmp_path: Path) -> None:
        """Sentinel key must not appear in ai-status JSON output."""
        repo = _setup_repo(tmp_path)
        runner = CliRunner()
        with patch.dict(os.environ, {"PHARABIUS_OPENAI_API_KEY": SENTINEL}, clear=False):
            runner.invoke(app, ["enrich", "--provider", "mock", "-r", str(repo)])
            result = runner.invoke(app, ["ai-status", "--json", "-r", str(repo)])
        assert result.exit_code == 0
        assert SENTINEL not in result.output
