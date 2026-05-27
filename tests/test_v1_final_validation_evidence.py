"""Tests for v1 final validation evidence pack (W51-S04)."""

from __future__ import annotations

from pathlib import Path

EVIDENCE = Path("docs/validation-results/v1-final-validation-evidence.md")


class TestEvidencePackExists:
    def test_file_exists(self) -> None:
        assert EVIDENCE.exists()


class TestEvidencePackContent:
    def test_includes_version(self) -> None:
        text = EVIDENCE.read_text()
        assert "v1.11.0" in text

    def test_includes_go_no_go(self) -> None:
        text = EVIDENCE.read_text()
        assert "Go/No-Go" in text or "Decision" in text

    def test_includes_known_limitations(self) -> None:
        text = EVIDENCE.read_text()
        assert "Known Limitations" in text

    def test_includes_command_matrix(self) -> None:
        text = EVIDENCE.read_text()
        assert "Command Matrix" in text

    def test_includes_safety_results(self) -> None:
        text = EVIDENCE.read_text()
        assert "Safety Boundary" in text

    def test_includes_artifact_contract(self) -> None:
        text = EVIDENCE.read_text()
        assert "Artifact Contract" in text

    def test_decision_is_ready(self) -> None:
        text = EVIDENCE.read_text()
        assert "ready" in text.lower()
