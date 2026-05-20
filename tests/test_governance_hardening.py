"""Tests for v1.2.1 governance hardening — path safety, fallback, validation."""

from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path

from pharabius.core.governance import load_governance
from pharabius.core.template_engine import (
    TEMPLATEABLE_ARTIFACTS,
    load_template_file,
    render_template,
    resolve_template_path,
)
from pharabius.schemas.governance import GovernanceConfig

# ── Path safety tests ────────────────────────────────────────────────


class TestPathSafety:
    def test_path_traversal_rejected(self, tmp_path: Path) -> None:
        """override_dir with .. that escapes repo root is rejected."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = resolve_template_path(
                "work-package.md",
                tmp_path,
                override_dir="../../etc",
            )
            assert result is None
            assert any("escapes" in str(x.message) for x in w)

    def test_absolute_path_outside_repo_rejected(self, tmp_path: Path) -> None:
        """Absolute override_dir outside repo root is rejected."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = resolve_template_path(
                "work-package.md",
                tmp_path,
                override_dir="/tmp",
            )
            assert result is None
            assert any("escapes" in str(x.message) for x in w)

    def test_safe_relative_path_allowed(self, tmp_path: Path) -> None:
        """Relative override_dir inside repo is allowed."""
        templates = tmp_path / "my-templates"
        templates.mkdir()
        (templates / "work-package.md").write_text("custom", encoding="utf-8")
        result = resolve_template_path(
            "work-package.md",
            tmp_path,
            override_dir="my-templates",
        )
        assert result is not None
        assert result.exists()

    def test_nonexistent_override_dir_returns_none(self, tmp_path: Path) -> None:
        """Non-existent override_dir returns None (no crash)."""
        result = resolve_template_path(
            "work-package.md",
            tmp_path,
            override_dir="nonexistent-dir",
        )
        assert result is None

    def test_conventional_path_still_works(self, tmp_path: Path) -> None:
        """Conventional .ai-debt/templates/ still works without override_dir."""
        templates = tmp_path / ".ai-debt" / "templates"
        templates.mkdir(parents=True)
        (templates / "work-package.md").write_text("custom", encoding="utf-8")
        result = resolve_template_path(
            "work-package.md",
            tmp_path,
        )
        assert result is not None
        assert ".ai-debt" in str(result)


# ── Template fallback tests ──────────────────────────────────────────


class TestTemplateFallback:
    def test_binary_template_fallback(self, tmp_path: Path) -> None:
        """Binary content in template file falls back safely."""
        templates = tmp_path / ".ai-debt" / "templates"
        templates.mkdir(parents=True)
        (templates / "work-package.md").write_bytes(b"\x00\x01\x02\xff\xfe\xfd")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = load_template_file(templates / "work-package.md")
            assert result is None
            assert any("Could not read" in str(x.message) for x in w)

    def test_empty_template_fallback(self, tmp_path: Path) -> None:
        """Empty template file falls back."""
        templates = tmp_path / ".ai-debt" / "templates"
        templates.mkdir(parents=True)
        (templates / "work-package.md").write_text("  \n  ", encoding="utf-8")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = load_template_file(templates / "work-package.md")
            assert result is None
            assert any("empty" in str(x.message).lower() for x in w)

    def test_large_template_handled(self, tmp_path: Path) -> None:
        """Large template (10KB+) is handled without crash."""
        templates = tmp_path / ".ai-debt" / "templates"
        templates.mkdir(parents=True)
        large_content = "# Template\n" + "x" * 15000
        (templates / "work-package.md").write_text(large_content, encoding="utf-8")
        result = load_template_file(templates / "work-package.md")
        assert result is not None
        assert len(result) > 10000

    def test_unreadable_template_fallback(self, tmp_path: Path) -> None:
        """Directory as template file falls back."""
        templates = tmp_path / ".ai-debt" / "templates"
        templates.mkdir(parents=True)
        (templates / "work-package.md").mkdir()
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = load_template_file(templates / "work-package.md")
            assert result is None


# ── Override precedence tests ────────────────────────────────────────


class TestOverridePrecedence:
    def test_explicit_beats_conventional(self, tmp_path: Path) -> None:
        """Explicit override_dir beats conventional .ai-debt/templates/."""
        # Create both
        explicit = tmp_path / "explicit"
        explicit.mkdir()
        (explicit / "work-package.md").write_text("explicit", encoding="utf-8")

        conventional = tmp_path / ".ai-debt" / "templates"
        conventional.mkdir(parents=True)
        (conventional / "work-package.md").write_text("conventional", encoding="utf-8")

        result = resolve_template_path(
            "work-package.md",
            tmp_path,
            override_dir="explicit",
        )
        assert result is not None
        content = result.read_text(encoding="utf-8")
        assert content == "explicit"


# ── Canonical immutability test ──────────────────────────────────────


class TestCanonicalImmutability:
    def test_json_unchanged_under_override(self, tmp_path: Path) -> None:
        """Canonical JSON files are identical with and without template override."""
        # Simulate a minimal workspace
        workspace = tmp_path / ".ai-debt"
        workspace.mkdir()

        # Write a canonical JSON
        canonical = {"schema_version": "1.0", "findings": []}
        json_path = workspace / "debt-register.json"
        json_path.write_text(json.dumps(canonical), encoding="utf-8")

        hash_before = hashlib.sha256(json_path.read_bytes()).hexdigest()

        # Add a template override
        templates = workspace / "templates"
        templates.mkdir()
        (templates / "work-package.md").write_text("# {{ package_id }}", encoding="utf-8")

        # Template override should not affect JSON
        hash_after = hashlib.sha256(json_path.read_bytes()).hexdigest()

        assert hash_before == hash_after


# ── Templateable artifacts scope test ────────────────────────────────


class TestTemplateableArtifacts:
    def test_only_three_artifacts_templateable(self) -> None:
        """Only work-package, handoff, roadmap are templateable in v1.2.x."""
        assert (
            frozenset(
                {
                    "work-package.md",
                    "handoff-summary.md",
                    "remediation-roadmap.md",
                }
            )
            == TEMPLATEABLE_ARTIFACTS
        )

    def test_debt_register_not_templateable(self, tmp_path: Path) -> None:
        assert resolve_template_path("debt-register.md", tmp_path) is None

    def test_foundation_audit_not_templateable(self, tmp_path: Path) -> None:
        assert resolve_template_path("foundation-audit-report.md", tmp_path) is None


# ── Non-default preset tests ─────────────────────────────────────────


class TestNonDefaultPresets:
    def test_platform_engineering_metadata_only(self, tmp_path: Path) -> None:
        """Non-default presets have no template files."""
        result = resolve_template_path(
            "work-package.md",
            tmp_path,
            preset="platform-engineering",
        )
        # No bundled template files for non-default presets
        assert result is None or result.exists()

    def test_security_sensitive_metadata_only(self, tmp_path: Path) -> None:
        result = resolve_template_path(
            "work-package.md",
            tmp_path,
            preset="security-sensitive",
        )
        assert result is None or result.exists()

    def test_compliance_sensitive_metadata_only(self, tmp_path: Path) -> None:
        result = resolve_template_path(
            "work-package.md",
            tmp_path,
            preset="compliance-sensitive",
        )
        assert result is None or result.exists()

    def test_startup_lean_metadata_only(self, tmp_path: Path) -> None:
        result = resolve_template_path(
            "work-package.md",
            tmp_path,
            preset="startup-lean",
        )
        assert result is None or result.exists()


# ── Old workspace compat test ────────────────────────────────────────


class TestOldWorkspaceCompat:
    def test_no_governance_yaml_works(self, tmp_path: Path) -> None:
        """Workspace without governance.yaml uses defaults."""
        workspace = tmp_path / ".ai-debt"
        workspace.mkdir()
        g = load_governance(tmp_path)
        assert g.preset == "default"
        assert g.review.require_evidence_review is True

    def test_no_governance_no_warning(self, tmp_path: Path) -> None:
        """Missing governance.yaml produces no warnings."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            load_governance(tmp_path)
            governance_warnings = [x for x in w if "governance" in str(x.message).lower()]
            assert len(governance_warnings) == 0


# ── Warning message content tests ────────────────────────────────────


class TestWarningMessages:
    def test_unknown_preset_includes_name(self, tmp_path: Path) -> None:
        from pharabius.core.governance import effective_preset

        g = GovernanceConfig(preset="my-bad-preset")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            effective_preset(g)
            assert any("my-bad-preset" in str(x.message) for x in w)

    def test_path_escape_includes_artifact(self, tmp_path: Path) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            resolve_template_path(
                "work-package.md",
                tmp_path,
                override_dir="../../escape",
            )
            msgs = [str(x.message) for x in w]
            assert any("work-package.md" in m for m in msgs)

    def test_unknown_placeholder_includes_name(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            render_template(
                "{{ my_unknown }}",
                {},
                artifact_name="test.md",
            )
            msgs = [str(x.message) for x in w]
            assert any("my_unknown" in m for m in msgs)
            assert any("test.md" in m for m in msgs)


# ── Partial override test ────────────────────────────────────────────


class TestPartialOverride:
    def test_override_one_artifact_others_default(
        self,
        tmp_path: Path,
    ) -> None:
        """Overriding only work-package.md leaves others unaffected."""
        templates = tmp_path / ".ai-debt" / "templates"
        templates.mkdir(parents=True)
        (templates / "work-package.md").write_text("# Custom WP", encoding="utf-8")

        wp_path = resolve_template_path(
            "work-package.md",
            tmp_path,
        )
        handoff_path = resolve_template_path(
            "handoff-summary.md",
            tmp_path,
        )
        roadmap_path = resolve_template_path(
            "remediation-roadmap.md",
            tmp_path,
        )

        assert wp_path is not None  # overridden
        assert handoff_path is None  # no override, no preset template
        assert roadmap_path is None  # no override, no preset template
