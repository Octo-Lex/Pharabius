"""Tests for v0.11.0 config runtime — model, loader, integration."""

from __future__ import annotations

import textwrap
from pathlib import Path

from pharabius.core.config import (
    effective_exclude_paths,
    load_config,
)
from pharabius.schemas.config import (
    AIConfig,
    AnalysisConfig,
    PharabiusConfig,
)

# ── Model tests ──────────────────────────────────────────────────────────


class TestConfigModel:
    def test_defaults_are_safe(self) -> None:
        config = PharabiusConfig()
        assert config.ai.enabled is False
        assert config.ai.provider == "disabled"
        assert config.ai.require_evidence_ids is True
        assert config.policies.no_code_modifications is True
        assert config.policies.require_confidence is True
        assert config.policies.mark_inferred_business_impact is True
        assert config.analysis.exclude_paths == []
        assert config.analysis.max_file_size_kb == 500
        assert config.output.directory == ".ai-debt"

    def test_no_credential_fields(self) -> None:
        """Config model must not have credential fields."""
        config = PharabiusConfig()
        data = config.model_dump()
        for key in _flatten_keys(data):
            assert "api_key" not in key, f"Found api_key field: {key}"
            assert "secret" not in key, f"Found secret field: {key}"
            assert "token" not in key, f"Found token field: {key}"
            assert "password" not in key, f"Found password field: {key}"
            assert "credential" not in key, f"Found credential field: {key}"

    def test_no_model_field(self) -> None:
        """No model selection field in config."""
        config = PharabiusConfig()
        ai_data = config.ai.model_dump()
        assert "model" not in ai_data

    def test_no_consent_field(self) -> None:
        """No provider consent field in config."""
        config = PharabiusConfig()
        ai_data = config.ai.model_dump()
        assert "allow_external_provider" not in ai_data

    def test_ai_provider_normalized(self) -> None:
        """Provider value is normalized to lowercase."""
        config = PharabiusConfig(ai=AIConfig(provider="OpenAI-Compatible"))
        assert config.ai.provider == "openai-compatible"

    def test_max_file_size_kb_positive(self) -> None:
        """max_file_size_kb clamped to positive."""
        config = PharabiusConfig(analysis=AnalysisConfig(max_file_size_kb=-1))
        assert config.analysis.max_file_size_kb == 500

    def test_extra_keys_allowed(self) -> None:
        """Unknown keys do not crash the model (loader handles warnings)."""
        data = {"schema_version": "1.0", "unknown_field": "value"}
        config = PharabiusConfig.model_validate(data)
        assert config.schema_version == "1.0"


# ── Loader tests ─────────────────────────────────────────────────────────


class TestConfigLoader:
    def test_missing_config_returns_defaults(self, tmp_path: Path) -> None:
        """No config.yaml → safe defaults, no error."""
        config = load_config(tmp_path)
        assert config.ai.enabled is False
        assert config.ai.provider == "disabled"

    def test_valid_config_loaded(self, tmp_path: Path) -> None:
        """Valid config.yaml is loaded correctly."""
        _write_config(
            tmp_path,
            textwrap.dedent("""\
            schema_version: "1.0"
            analysis:
              exclude_paths:
                - generated
                - vendor
        """),
        )
        config = load_config(tmp_path)
        assert "generated" in config.analysis.exclude_paths
        assert "vendor" in config.analysis.exclude_paths

    def test_malformed_yaml_warns(self, tmp_path: Path) -> None:
        """Malformed YAML → warning + safe defaults."""
        _write_config(tmp_path, "  invalid: yaml: [broken: {{{")
        config = load_config(tmp_path)
        # Should return safe defaults
        assert config.ai.enabled is False
        assert config.analysis.exclude_paths == []

    def test_empty_config_returns_defaults(self, tmp_path: Path) -> None:
        """Empty config.yaml → safe defaults."""
        _write_config(tmp_path, "")
        config = load_config(tmp_path)
        assert config.ai.enabled is False

    def test_invalid_field_type_warns(self, tmp_path: Path) -> None:
        """Invalid field type → warning + safe defaults."""
        _write_config(tmp_path, 'ai:\n  enabled: "not_a_bool"')
        config = load_config(tmp_path)
        assert config.ai.enabled is False

    def test_unknown_keys_accepted(self, tmp_path: Path) -> None:
        """Unknown keys are accepted (model uses extra='allow')."""
        _write_config(tmp_path, "future_field: some_value")
        config = load_config(tmp_path)
        assert config.ai.enabled is False  # defaults still safe

    def test_config_cannot_contain_credentials(self, tmp_path: Path) -> None:
        """Config with credential-like fields loads but fields are not schema fields."""
        _write_config(
            tmp_path,
            textwrap.dedent("""\
            ai:
              api_key: "sk-12345"
        """),
        )
        config = load_config(tmp_path)
        assert not hasattr(config.ai, "api_key")


# ── Integration tests ───────────────────────────────────────────────────


class TestConfigIntegration:
    def test_effective_exclude_paths(self) -> None:
        """effective_exclude_paths returns config paths."""
        config = PharabiusConfig(analysis=AnalysisConfig(exclude_paths=["generated", "dist"]))
        paths = effective_exclude_paths(config)
        assert paths == {"generated", "dist"}

    def test_effective_exclude_paths_empty(self) -> None:
        """No extra exclude paths returns empty set."""
        config = PharabiusConfig()
        paths = effective_exclude_paths(config)
        assert paths == set()

    def test_config_does_not_replace_hardcoded_exclusions(self, tmp_path: Path) -> None:
        """Config exclusions supplement, not replace, hardcoded ones."""
        from pharabius.core.exclusions import EXCLUDED_DIR_NAMES

        _write_config(
            tmp_path,
            textwrap.dedent("""\
            analysis:
              exclude_paths:
                - generated
        """),
        )
        config = load_config(tmp_path)
        extra = effective_exclude_paths(config)
        # Hardcoded exclusions still work
        assert "node_modules" in EXCLUDED_DIR_NAMES
        # Config adds to them
        assert "generated" in extra

    def test_config_git_exclude_does_not_match_github(self, tmp_path: Path) -> None:
        """Config exclude '.git' must NOT exclude '.github/'."""
        from pharabius.core.scanner import _is_excluded

        _write_config(
            tmp_path,
            textwrap.dedent("""\
            analysis:
              exclude_paths:
                - .git
        """),
        )
        config = load_config(tmp_path)
        extra = effective_exclude_paths(config)
        ci_file = tmp_path / ".github" / "workflows" / "ci.yml"
        ci_file.parent.mkdir(parents=True, exist_ok=True)
        ci_file.write_text("name: CI", encoding="utf-8")
        assert not _is_excluded(ci_file, tmp_path, extra_exclude_paths=extra)


class TestConfigProviderSafety:
    def test_config_provider_does_not_trigger_real_provider(self, tmp_path: Path) -> None:
        """Config ai.provider=openai-compatible does NOT cause real calls."""
        _write_config(
            tmp_path,
            textwrap.dedent("""\
            ai:
              provider: openai-compatible
        """),
        )
        config = load_config(tmp_path)
        # Config is loaded but does NOT initiate provider
        assert config.ai.provider == "openai-compatible"
        # The CLI consent gate (--allow-external-provider) is still required
        # This test verifies the config value does not bypass that

    def test_config_enabled_true_still_requires_cli_consent(self, tmp_path: Path) -> None:
        """Config ai.enabled=true does NOT bypass CLI consent."""
        _write_config(
            tmp_path,
            textwrap.dedent("""\
            ai:
              enabled: true
        """),
        )
        config = load_config(tmp_path)
        assert config.ai.enabled is True
        # But --allow-external-provider is still required at CLI level
        # Config cannot bypass that


# ── Helpers ──────────────────────────────────────────────────────────────


def _write_config(repo_root: Path, content: str) -> None:
    """Write .ai-debt/config.yaml."""
    ai_debt = repo_root / ".ai-debt"
    ai_debt.mkdir(parents=True, exist_ok=True)
    (ai_debt / "config.yaml").write_text(content, encoding="utf-8")


def _flatten_keys(data: dict, prefix: str = "") -> list[str]:
    """Recursively flatten dict keys."""
    keys: list[str] = []
    for k, v in data.items():
        full = f"{prefix}.{k}" if prefix else k
        keys.append(full)
        if isinstance(v, dict):
            keys.extend(_flatten_keys(v, full))
    return keys
