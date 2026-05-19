from pathlib import Path

from pharabius.core.init_workspace import initialize_workspace


def test_initialize_workspace_creates_expected_contract(tmp_path: Path) -> None:
    created = initialize_workspace(tmp_path)

    workspace = tmp_path / ".ai-debt"

    assert workspace.exists()
    assert (workspace / "config.yaml").exists()
    assert (workspace / "project-profile.json").exists()
    assert (workspace / "evidence.json").exists()
    assert (workspace / "debt-register.json").exists()
    assert (workspace / "debt-register.md").exists()
    assert (workspace / "architecture-map.md").exists()
    assert (workspace / "dependency-health.md").exists()
    assert (workspace / "test-health.md").exists()
    assert (workspace / "security-exposure.md").exists()
    assert (workspace / "business-risk-proxy.md").exists()
    assert (workspace / "remediation-roadmap.md").exists()
    assert (workspace / "handoff-summary.md").exists()
    assert (workspace / "work-packages").exists()
    assert (workspace / "reports").exists()
    assert (workspace / "reports" / "foundation-audit-report.md").exists()
    assert (workspace / "runs").exists()

    assert len(created) > 0


class TestConfigDefaults:
    """Verify config.yaml contains safe, accurate defaults."""

    def _config(self, tmp_path: Path) -> str:
        initialize_workspace(tmp_path)
        return (tmp_path / ".ai-debt" / "config.yaml").read_text()

    def test_config_ai_disabled(self, tmp_path: Path) -> None:
        """AI must be disabled by default."""
        assert "enabled: false" in self._config(tmp_path)

    def test_config_provider_disabled(self, tmp_path: Path) -> None:
        """Provider must be 'disabled' by default."""
        assert 'provider: "disabled"' in self._config(tmp_path)

    def test_config_no_model_auto(self, tmp_path: Path) -> None:
        """No 'model: auto' default — model must be explicitly set."""
        assert "model:" not in self._config(tmp_path)

    def test_config_no_business_inference(self, tmp_path: Path) -> None:
        """No allow_business_inference — not implemented."""
        assert "allow_business_inference" not in self._config(tmp_path)

    def test_config_no_secrets(self, tmp_path: Path) -> None:
        """No credential/secret fields in config."""
        config = self._config(tmp_path).lower()
        for forbidden in ["api_key", "secret", "token", "password", "credential", ".env"]:
            assert forbidden not in config, f"Forbidden field '{forbidden}' in config"

    def test_config_priority_bands_match_blueprint(self, tmp_path: Path) -> None:
        """Priority bands must match blueprint §12.3."""
        config = self._config(tmp_path)
        assert "low: [0, 10]" in config
        assert "medium: [11, 20]" in config
        assert "high: [21, 35]" in config
        assert "critical: [36, 100]" in config

    def test_config_git_history_disabled(self, tmp_path: Path) -> None:
        """Git history must be disabled — not implemented."""
        assert "include_git_history: false" in self._config(tmp_path)

    def test_config_policies_present(self, tmp_path: Path) -> None:
        """All three policy fields must be present and true."""
        config = self._config(tmp_path)
        assert "no_code_modifications: true" in config
        assert "require_confidence: true" in config
        assert "mark_inferred_business_impact: true" in config
