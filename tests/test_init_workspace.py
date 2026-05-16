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
