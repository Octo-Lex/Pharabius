"""v3.10.0 S03 — PHP runtime evidence tests."""

from __future__ import annotations

from pathlib import Path

from pharabius.core.runtime.models import RuntimeConstraintKind
from pharabius.core.runtime.php import detect_php_sources


class TestPhpSources:
    def test_composer_exact_version(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text('{"require": {"php": "8.2.12"}}\n')
        evidence = detect_php_sources(tmp_path)
        assert len(evidence) == 1
        assert evidence[0].constraint.kind == RuntimeConstraintKind.EXACT
        assert evidence[0].raw_version == "8.2.12"

    def test_composer_range_caret(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text('{"require": {"php": "^8.2"}}\n')
        evidence = detect_php_sources(tmp_path)
        assert len(evidence) == 1
        assert evidence[0].constraint.kind == RuntimeConstraintKind.RANGE

    def test_composer_range_tilde(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text('{"require": {"php": "~8.2"}}\n')
        evidence = detect_php_sources(tmp_path)
        assert len(evidence) == 1
        assert evidence[0].constraint.kind == RuntimeConstraintKind.RANGE

    def test_composer_wildcard(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text('{"require": {"php": "8.2.*"}}\n')
        evidence = detect_php_sources(tmp_path)
        assert len(evidence) == 1
        assert evidence[0].constraint.kind == RuntimeConstraintKind.RANGE

    def test_composer_gte(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text('{"require": {"php": ">=8.2"}}\n')
        evidence = detect_php_sources(tmp_path)
        assert len(evidence) == 1
        assert evidence[0].constraint.kind == RuntimeConstraintKind.RANGE

    def test_no_composer_returns_empty(self, tmp_path: Path) -> None:
        evidence = detect_php_sources(tmp_path)
        assert evidence == []
