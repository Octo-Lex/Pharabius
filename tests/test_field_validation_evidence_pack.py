"""Tests for field validation evidence pack (W49-S05)."""

from __future__ import annotations

from pathlib import Path

EVIDENCE_PACK = Path("docs/validation-results/field-validation-v1.10.1.md")


class TestEvidencePackExists:
    def test_evidence_pack_exists(self) -> None:
        assert EVIDENCE_PACK.exists()

    def test_evidence_pack_nonempty(self) -> None:
        assert len(EVIDENCE_PACK.read_text().strip()) > 0


class TestEvidencePackContent:
    def test_has_summary(self) -> None:
        text = EVIDENCE_PACK.read_text()
        assert "## Summary" in text

    def test_has_repository_matrix(self) -> None:
        text = EVIDENCE_PACK.read_text()
        assert "## Repository Matrix" in text
        assert "Pharabius" in text

    def test_has_command_matrix(self) -> None:
        text = EVIDENCE_PACK.read_text()
        assert "## Command Matrix" in text
        assert "ai-debt init" in text

    def test_has_artifact_contract_results(self) -> None:
        text = EVIDENCE_PACK.read_text()
        assert "## Artifact Contract Results" in text

    def test_has_readiness_results(self) -> None:
        text = EVIDENCE_PACK.read_text()
        assert "## Readiness Results" in text

    def test_has_known_limitations(self) -> None:
        text = EVIDENCE_PACK.read_text()
        assert "## Known Limitations" in text

    def test_has_release_confidence(self) -> None:
        text = EVIDENCE_PACK.read_text()
        assert "## Release Confidence Assessment" in text

    def test_no_external_api_claims(self) -> None:
        text = EVIDENCE_PACK.read_text().lower()
        assert "external api" not in text or "no external api" in text

    def test_verdict_present(self) -> None:
        text = EVIDENCE_PACK.read_text()
        assert "PASS" in text or "FAIL" in text
