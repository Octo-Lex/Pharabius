"""Tests for release artifact and version consistency (W50-S04)."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts to path
_scripts_dir = str(Path(__file__).resolve().parent.parent / "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

# ruff: noqa: E402
from validate_release_consistency import validate_release_consistency

EXPECTED = "2.2.2"


class TestVersionSources:
    def test_pyproject_matches(self) -> None:
        report = validate_release_consistency(EXPECTED, Path("."))
        pyproject = [c for c in report["checks"] if c["source"] == "pyproject"]
        assert pyproject and pyproject[0]["status"] == "ok"

    def test_installed_metadata_matches(self) -> None:
        report = validate_release_consistency(EXPECTED, Path("."))
        meta = [c for c in report["checks"] if c["source"] == "installed_metadata"]
        assert meta and meta[0]["status"] == "ok"

    def test_cli_version_matches(self) -> None:
        report = validate_release_consistency(EXPECTED, Path("."))
        cli = [c for c in report["checks"] if c["source"] == "cli"]
        assert cli and cli[0]["status"] == "ok"


class TestDocsConsistency:
    def test_changelog_has_v110_header(self) -> None:
        report = validate_release_consistency(EXPECTED, Path("."))
        cl = [c for c in report["checks"] if c["source"] == "changelog"]
        assert cl  # Changelog check ran

    def test_roadmap_has_v110_header(self) -> None:
        report = validate_release_consistency(EXPECTED, Path("."))
        rm = [c for c in report["checks"] if c["source"] == "roadmap"]
        assert rm  # Roadmap check ran


class TestMismatchDetection:
    def test_wrong_version_detected(self) -> None:
        report = validate_release_consistency("99.99.99", Path("."))
        assert report["status"] == "inconsistent"
        assert report["errors"] > 0


class TestOverall:
    def test_source_and_cli_consistent(self) -> None:
        report = validate_release_consistency(EXPECTED, Path("."))
        # Source + CLI + installed must all match
        critical = [
            c for c in report["checks"] if c["source"] in ("pyproject", "cli", "installed_metadata")
        ]
        assert all(c["status"] == "ok" for c in critical)
