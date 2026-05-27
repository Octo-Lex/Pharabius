"""Tests for packaging metadata verification (W50-S01)."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts to path
_scripts_dir = str(Path(__file__).resolve().parent.parent / "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

# ruff: noqa: E402
from validate_packaging import validate_packaging


class TestPackageVersion:
    def test_version_is_readable(self) -> None:
        report = validate_packaging()
        assert report["version"] is not None
        assert isinstance(report["version"], str)

    def test_version_matches_pattern(self) -> None:
        report = validate_packaging()
        v = report["version"]
        parts = v.split(".")
        assert len(parts) >= 2
        assert all(p.isdigit() for p in parts[:2])


class TestChecksStructure:
    def test_checks_is_list(self) -> None:
        report = validate_packaging()
        assert isinstance(report["checks"], list)
        assert len(report["checks"]) >= 5

    def test_all_checks_have_required_fields(self) -> None:
        report = validate_packaging()
        for check in report["checks"]:
            assert "name" in check
            assert "status" in check
            assert "message" in check
            assert check["status"] in ("pass", "fail", "warning")


class TestModuleImports:
    def test_key_modules_importable(self) -> None:
        report = validate_packaging()
        import_checks = [c for c in report["checks"] if c["name"].startswith("import:")]
        assert len(import_checks) >= 5
        for c in import_checks:
            assert c["status"] == "pass", f"Import failed: {c['name']}"


class TestSummary:
    def test_summary_has_counts(self) -> None:
        report = validate_packaging()
        summary = report["summary"]
        assert "total" in summary
        assert "pass" in summary
        assert "fail" in summary
        assert "warning" in summary

    def test_summary_counts_match_checks(self) -> None:
        report = validate_packaging()
        summary = report["summary"]
        assert summary["total"] == len(report["checks"])
        assert summary["pass"] + summary["fail"] + summary["warning"] == summary["total"]
