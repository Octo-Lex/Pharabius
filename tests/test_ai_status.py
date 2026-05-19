"""Tests for AI sidecar status reader and ai-status CLI command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pharabius.ai.status_reader import SidecarStatus, read_ai_status
from pharabius.cli import app


def _make_sidecar(
    tmp: Path,
    *,
    provider: str = "mock",
    model: str = "mock-v0.7.0",
    enrichments: int = 2,
    rejections: int = 0,
    evidence_per_finding: int = 1,
    omitted: int = 0,
) -> Path:
    """Create a minimal sidecar enrichment-report.json in tmp/.ai-debt/ai/."""
    ai_dir = tmp / ".ai-debt" / "ai"
    ai_dir.mkdir(parents=True, exist_ok=True)

    enc_list = []
    for i in range(enrichments):
        enc_list.append(
            {
                "finding_id": f"TD-DEP-{i:03d}",
                "evidence_ids": [f"EVD-{i:03d}-{j:03d}" for j in range(evidence_per_finding)],
                "confidence": "Medium",
                "limitations": ["AI-generated enrichment"],
            }
        )

    rej_list = []
    for i in range(rejections):
        rej_list.append(
            {
                "finding_id": f"TD-BAD-{i:03d}",
                "reason": "Invalid evidence IDs",
                "invalid_fields": ["evidence_ids"],
                "raw_output_hash": "a1b2c3d4e5f6g7h8",
            }
        )

    report = {
        "schema_version": "1.0",
        "provider": provider,
        "model": model,
        "generated_at": "2026-05-19T00:00:00+00:00",
        "repository": str(tmp),
        "commit": "abc1234",
        "context_summary": {
            "evidence_items_included": enrichments * evidence_per_finding,
            "evidence_items_omitted": omitted,
            "analysis_units_included": 0,
            "analysis_units_omitted": 0,
            "graph_records_included": 0,
            "graph_records_omitted": 0,
        },
        "usage": {
            "provider": provider,
            "model": model,
            "prompt_chars": 100,
            "response_chars": 200,
            "items_processed": enrichments + rejections,
            "items_accepted": enrichments,
            "items_rejected": rejections,
        },
        "enrichments": enc_list,
        "rejections": rej_list,
        "is_ai_enriched": True,
    }

    (ai_dir / "enrichment-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return ai_dir


# ── Status reader unit tests ─────────────────────────────────────────────


class TestReadAIStatus:
    """Tests for read_ai_status()."""

    def test_no_sidecar_dir_exits_0(self, tmp_path: Path) -> None:
        status, code = read_ai_status(tmp_path)
        assert code == 0
        assert not status.sidecar_present
        assert "No AI sidecar found" in status.error_message

    def test_missing_report_exits_1(self, tmp_path: Path) -> None:
        ai_dir = tmp_path / ".ai-debt" / "ai"
        ai_dir.mkdir(parents=True)
        status, code = read_ai_status(tmp_path)
        assert code == 1
        assert "enrichment-report.json is missing" in status.error_message

    def test_malformed_json_exits_1(self, tmp_path: Path) -> None:
        ai_dir = tmp_path / ".ai-debt" / "ai"
        ai_dir.mkdir(parents=True)
        (ai_dir / "enrichment-report.json").write_text("not json {{{", encoding="utf-8")
        status, code = read_ai_status(tmp_path)
        assert code == 1
        assert "corrupted or unreadable" in status.error_message

    def test_valid_sidecar(self, tmp_path: Path) -> None:
        _make_sidecar(tmp_path, enrichments=3, evidence_per_finding=2, omitted=5)
        status, code = read_ai_status(tmp_path)
        assert code == 0
        assert status.sidecar_present
        assert status.provider == "mock"
        assert status.enrichments_accepted == 3
        assert status.enrichments_rejected == 0
        assert status.evidence_referenced == 6  # 3 findings x 2 evidence IDs
        assert status.evidence_omitted == 5

    def test_valid_sidecar_with_rejections(self, tmp_path: Path) -> None:
        _make_sidecar(tmp_path, enrichments=2, rejections=1)
        status, code = read_ai_status(tmp_path)
        assert code == 0
        assert status.enrichments_accepted == 2
        assert status.enrichments_rejected == 1

    def test_empty_enrichments_all_rejected(self, tmp_path: Path) -> None:
        _make_sidecar(tmp_path, enrichments=0, rejections=3)
        status, code = read_ai_status(tmp_path)
        assert code == 0
        assert status.enrichments_accepted == 0
        assert status.enrichments_rejected == 3
        assert status.evidence_referenced == 0

    def test_empty_rejections_all_accepted(self, tmp_path: Path) -> None:
        _make_sidecar(tmp_path, enrichments=5, rejections=0)
        status, _code = read_ai_status(tmp_path)
        assert status.enrichments_accepted == 5
        assert status.enrichments_rejected == 0

    def test_does_not_require_evidence_json(self, tmp_path: Path) -> None:
        _make_sidecar(tmp_path)
        # No evidence.json exists
        assert not (tmp_path / ".ai-debt" / "evidence.json").exists()
        status, code = read_ai_status(tmp_path)
        assert code == 0
        assert status.sidecar_present

    def test_does_not_require_debt_register(self, tmp_path: Path) -> None:
        _make_sidecar(tmp_path)
        assert not (tmp_path / ".ai-debt" / "debt-register.json").exists()
        status, code = read_ai_status(tmp_path)
        assert code == 0
        assert status.sidecar_present

    def test_canonical_artifacts_modified_always_false(self, tmp_path: Path) -> None:
        _make_sidecar(tmp_path)
        status, _code = read_ai_status(tmp_path)
        assert not status.canonical_artifacts_modified

    def test_to_dict(self, tmp_path: Path) -> None:
        _make_sidecar(tmp_path, enrichments=2, omitted=3)
        status, _code = read_ai_status(tmp_path)
        d = status.to_dict()
        assert d["sidecar_present"] is True
        assert d["provider"] == "mock"
        assert d["enrichments_accepted"] == 2
        assert d["evidence_omitted"] == 3
        assert d["canonical_artifacts_modified"] is False
        assert d["status"] == "review_recommended"

    def test_to_dict_no_sidecar(self) -> None:
        status = SidecarStatus(sidecar_present=False)
        d = status.to_dict()
        assert d["status"] == "no_sidecar"

    def test_to_human(self, tmp_path: Path) -> None:
        _make_sidecar(tmp_path, enrichments=2)
        status, _code = read_ai_status(tmp_path)
        text = status.to_human()
        assert "AI Sidecar Status" in text
        assert "mock" in text
        assert "not modified (by design)" in text

    def test_status_findings_selected(self, tmp_path: Path) -> None:
        _make_sidecar(tmp_path, enrichments=3, rejections=1)
        status, _code = read_ai_status(tmp_path)
        assert status.findings_selected == 4  # 3 accepted + 1 rejected


# ── SidecarStatus unit tests ─────────────────────────────────────────────


class TestSidecarStatus:
    """Tests for SidecarStatus data class."""

    def test_default_values(self) -> None:
        s = SidecarStatus()
        assert not s.sidecar_present
        assert s.provider == ""
        assert s.enrichments_accepted == 0

    def test_to_human_format(self) -> None:
        s = SidecarStatus(
            sidecar_present=True,
            provider="mock",
            model="mock-v0.7.0",
            generated_at="2026-05-19T00:00:00+00:00",
            enrichments_accepted=5,
            enrichments_rejected=1,
            evidence_referenced=12,
            evidence_omitted=3,
            findings_selected=6,
        )
        text = s.to_human()
        assert "mock" in text
        assert "5" in text  # accepted
        assert "1" in text  # rejected
        assert "12" in text  # evidence


# ── CLI ai-status tests ──────────────────────────────────────────────────


runner = CliRunner()


class TestAIStatusCLI:
    """Tests for 'ai-debt ai-status' CLI command."""

    def test_no_sidecar_exits_0(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["ai-status", "-r", str(tmp_path)])
        assert result.exit_code == 0
        assert "No AI sidecar found" in result.output

    def test_valid_sidecar_summary(self, tmp_path: Path) -> None:
        _make_sidecar(tmp_path, enrichments=3)
        result = runner.invoke(app, ["ai-status", "-r", str(tmp_path)])
        assert result.exit_code == 0
        assert "mock" in result.output
        assert "3" in result.output  # accepted

    def test_json_output_valid(self, tmp_path: Path) -> None:
        _make_sidecar(tmp_path, enrichments=2, omitted=4)
        result = runner.invoke(app, ["ai-status", "--json", "-r", str(tmp_path)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["sidecar_present"] is True
        assert data["enrichments_accepted"] == 2
        assert data["evidence_omitted"] == 4
        assert data["canonical_artifacts_modified"] is False
        assert data["status"] == "review_recommended"

    def test_malformed_sidecar_exits_1(self, tmp_path: Path) -> None:
        ai_dir = tmp_path / ".ai-debt" / "ai"
        ai_dir.mkdir(parents=True)
        (ai_dir / "enrichment-report.json").write_text("{{{bad", encoding="utf-8")
        result = runner.invoke(app, ["ai-status", "-r", str(tmp_path)])
        assert result.exit_code == 1
        assert "corrupted" in result.output.lower()

    def test_missing_report_exits_1(self, tmp_path: Path) -> None:
        ai_dir = tmp_path / ".ai-debt" / "ai"
        ai_dir.mkdir(parents=True)
        result = runner.invoke(app, ["ai-status", "-r", str(tmp_path)])
        assert result.exit_code == 1
        assert "missing" in result.output.lower()

    def test_read_only_does_not_create_files(self, tmp_path: Path) -> None:
        _make_sidecar(tmp_path)
        files_before = set((tmp_path / ".ai-debt").rglob("*"))
        runner.invoke(app, ["ai-status", "-r", str(tmp_path)])
        files_after = set((tmp_path / ".ai-debt").rglob("*"))
        assert files_before == files_after

    def test_json_no_sidecar(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["ai-status", "--json", "-r", str(tmp_path)])
        assert result.exit_code == 0
        assert "No AI sidecar found" in result.output

    def test_with_rejections_shown(self, tmp_path: Path) -> None:
        _make_sidecar(tmp_path, enrichments=1, rejections=2)
        result = runner.invoke(app, ["ai-status", "-r", str(tmp_path)])
        assert result.exit_code == 0
        assert "2" in result.output  # rejected count

    def test_default_repo_root_is_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["ai-status"])
        assert result.exit_code == 0
        # Should work with cwd as default
