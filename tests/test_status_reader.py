"""Tests for the read-only status reader."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pharabius.core.status_reader import read_status
from pharabius.schemas.evidence import EvidenceItem, EvidenceLocation, EvidenceStore
from pharabius.schemas.finding import DebtFinding, DebtRegister, DebtRegisterSummary


def _setup_empty_ai_debt(tmp_path: Path) -> Path:
    ai_debt = tmp_path / ".ai-debt"
    ai_debt.mkdir()
    return tmp_path


def _setup_full_ai_debt(tmp_path: Path) -> Path:
    ai_debt = tmp_path / ".ai-debt"
    ai_debt.mkdir()
    reports = ai_debt / "reports"
    reports.mkdir()
    runs = ai_debt / "runs"
    runs.mkdir()
    wp = ai_debt / "work-packages"
    wp.mkdir()

    # Profile
    (ai_debt / "project-profile.json").write_text(
        '{"detected_languages": ["Python"]}', encoding="utf-8"
    )
    # Evidence
    store = EvidenceStore(
        evidence=[
            EvidenceItem(
                evidence_id="EVD-001",
                type="manifest_detected",
                category="deps",
                location=EvidenceLocation(file="pyproject.toml"),
                summary="test",
            )
        ]
    )
    (ai_debt / "evidence.json").write_text(store.model_dump_json(), encoding="utf-8")
    # Units
    (ai_debt / "analysis-units.json").write_text(
        '{"units": [{"analysis_unit_id": "AU-1"}]}', encoding="utf-8"
    )
    # Register
    register = DebtRegister(
        project_name="test",
        summary=DebtRegisterSummary(total_findings=1, medium=1),
        findings=[
            DebtFinding(
                id="TD-DEP-001",
                category="TD-DEP",
                title="Test",
                description="Test",
                technical_impact="Test",
                business_impact="Test",
                risk_score=50,
                priority="Medium",
                recommended_action="Test",
            )
        ],
    )
    (ai_debt / "debt-register.json").write_text(register.model_dump_json(), encoding="utf-8")
    # Work package
    (wp / "WP-001-test.md").write_text("# WP\n", encoding="utf-8")
    # Verification
    (ai_debt / "verification-report.json").write_text(
        '{"total_findings_checked": 1, "still_detected_count": 1, "generated_at": "2026-05-17"}',
        encoding="utf-8",
    )
    # Reports
    (reports / "architecture-map.md").write_text("# Arch\n", encoding="utf-8")
    (reports / "dependency-health.md").write_text("# Deps\n", encoding="utf-8")
    (reports / "test-health.md").write_text("# Tests\n", encoding="utf-8")
    (reports / "security-exposure.md").write_text("# Sec\n", encoding="utf-8")
    (reports / "business-risk-proxy.md").write_text("# Biz\n", encoding="utf-8")
    (reports / "foundation-audit-report.md").write_text("# Audit\n", encoding="utf-8")
    # Run
    (runs / "RUN-20260517-120000.json").write_text("{}", encoding="utf-8")
    return tmp_path


class TestStatusFullWorkspace:
    def test_all_sections_populated(self, tmp_path: Path) -> None:
        repo = _setup_full_ai_debt(tmp_path)
        output = read_status(repo)
        assert "present" in output
        assert "1 items" in output
        assert "Findings:     1" in output
        assert "0 critical, 0 high, 1 medium, 0 low" in output
        assert "Work packages: 1" in output
        assert "still_detected" in output
        assert "6/6 present" in output
        assert "RUN-20260517-120000" in output


class TestStatusMissingAiDebt:
    def test_missing_dir_shows_absent(self, tmp_path: Path) -> None:
        # No .ai-debt directory at all
        output = read_status(tmp_path)
        assert "absent" in output
        # Should not crash


class TestStatusMissingVerification:
    def test_missing_verification_shows_absent(self, tmp_path: Path) -> None:
        repo = _setup_full_ai_debt(tmp_path)
        (repo / ".ai-debt" / "verification-report.json").unlink()
        output = read_status(repo)
        assert "Verification: absent" in output


class TestStatusLatestRun:
    def test_latest_run_detected(self, tmp_path: Path) -> None:
        repo = _setup_full_ai_debt(tmp_path)
        output = read_status(repo)
        assert "RUN-20260517-120000" in output


class TestStatusNoModifications:
    def test_does_not_modify_files(self, tmp_path: Path) -> None:
        repo = _setup_full_ai_debt(tmp_path)
        ai_debt = repo / ".ai-debt"
        # Hash all files before
        before_hashes = {}
        for f in ai_debt.rglob("*"):
            if f.is_file():
                before_hashes[str(f)] = hashlib.sha256(f.read_bytes()).hexdigest()

        read_status(repo)

        # Hash all files after
        for f in ai_debt.rglob("*"):
            if f.is_file():
                key = str(f)
                assert key in before_hashes, f"New file created: {f}"
                assert hashlib.sha256(f.read_bytes()).hexdigest() == before_hashes[key], (
                    f"File modified: {f}"
                )


class TestStatusCorruptedJson:
    def test_corrupted_json_handled_gracefully(self, tmp_path: Path) -> None:
        repo = _setup_full_ai_debt(tmp_path)
        (repo / ".ai-debt" / "evidence.json").write_text("not json{{{", encoding="utf-8")
        output = read_status(repo)
        assert "unreadable" in output

    def test_corrupted_json_warning_appears(self, tmp_path: Path) -> None:
        repo = _setup_full_ai_debt(tmp_path)
        (repo / ".ai-debt" / "evidence.json").write_text("not json{{{", encoding="utf-8")
        output = read_status(repo)
        assert "Warning:" in output
