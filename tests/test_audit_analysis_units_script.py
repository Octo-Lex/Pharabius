"""Tests for scripts/audit_analysis_units.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "audit_analysis_units.py"


def _run(repo_path: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), repo_path],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
    )


def _write_units(tmp_path: Path, units: list[dict]) -> Path:
    """Write analysis-units.json and return the repo path."""
    ai_debt = tmp_path / ".ai-debt"
    ai_debt.mkdir()
    (ai_debt / "analysis-units.json").write_text(json.dumps({"units": units}), encoding="utf-8")
    return tmp_path


def _sample_units() -> list[dict]:
    return [
        {
            "analysis_unit_id": "AU-PKG-001",
            "unit_type": "package",
            "name": "root package",
            "root_path": ".",
            "primary_files": ["pyproject.toml"],
            "files": ["pyproject.toml"],
            "evidence_ids": ["EVD-001", "EVD-002"],
            "trust_boundary_tags": [],
        },
        {
            "analysis_unit_id": "AU-SEC-001",
            "unit_type": "security_sensitive_area",
            "name": "src security",
            "root_path": "src/auth",
            "primary_files": ["src/auth/login.py"],
            "files": ["src/auth/login.py", "src/auth/session.py"],
            "evidence_ids": ["EVD-010", "EVD-011"],
            "trust_boundary_tags": ["auth", "token"],
        },
    ]


class TestAuditSummary:
    def test_valid_json_prints_summary_and_exits_0(self, tmp_path: Path) -> None:
        repo = _write_units(tmp_path, _sample_units())
        result = _run(str(repo))
        assert result.returncode == 0
        assert "Total units: 2" in result.stdout
        assert "package" in result.stdout
        assert "security_sensitive_area" in result.stdout

    def test_unit_types_counted_correctly(self, tmp_path: Path) -> None:
        units = _sample_units()
        units.append(
            {
                "analysis_unit_id": "AU-TEST-001",
                "unit_type": "test_suite",
                "name": "tests",
                "root_path": "tests",
                "primary_files": ["tests/test_foo.py"],
                "files": ["tests/test_foo.py"],
                "evidence_ids": ["EVD-020"],
                "trust_boundary_tags": [],
            }
        )
        repo = _write_units(tmp_path, units)
        result = _run(str(repo))
        assert result.returncode == 0
        # Should list all 3 types
        assert "test_suite" in result.stdout
        assert "Total units: 3" in result.stdout


class TestMissingFile:
    def test_missing_file_exits_1(self, tmp_path: Path) -> None:
        result = _run(str(tmp_path))
        assert result.returncode == 1
        assert "not found" in result.stderr


class TestInvalidJson:
    def test_invalid_json_exits_2(self, tmp_path: Path) -> None:
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        (ai_debt / "analysis-units.json").write_text("not json{{{", encoding="utf-8")
        result = _run(str(tmp_path))
        assert result.returncode == 2

    def test_missing_units_key_exits_2(self, tmp_path: Path) -> None:
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        (ai_debt / "analysis-units.json").write_text(json.dumps({"wrong": []}), encoding="utf-8")
        result = _run(str(tmp_path))
        assert result.returncode == 2


class TestZeroEvidence:
    def test_zero_evidence_unit_reported(self, tmp_path: Path) -> None:
        units = _sample_units()
        units.append(
            {
                "analysis_unit_id": "AU-CFG-EMPTY",
                "unit_type": "config_surface",
                "name": "empty config",
                "root_path": ".",
                "primary_files": [],
                "files": [],
                "evidence_ids": [],
                "trust_boundary_tags": [],
            }
        )
        repo = _write_units(tmp_path, units)
        result = _run(str(repo))
        assert result.returncode == 0
        assert "AU-CFG-EMPTY" in result.stdout
        assert "Zero-evidence" in result.stdout


class TestTrustBoundaryTags:
    def test_top_tags_reported(self, tmp_path: Path) -> None:
        units = _sample_units()
        units.append(
            {
                "analysis_unit_id": "AU-SEC-002",
                "unit_type": "security_sensitive_area",
                "name": "billing security",
                "root_path": "src/billing",
                "primary_files": ["src/billing/charge.py"],
                "files": ["src/billing/charge.py"],
                "evidence_ids": ["EVD-030"],
                "trust_boundary_tags": ["auth", "crypto"],
            }
        )
        repo = _write_units(tmp_path, units)
        result = _run(str(repo))
        assert result.returncode == 0
        assert "auth" in result.stdout
        assert "crypto" in result.stdout
        assert "token" in result.stdout
