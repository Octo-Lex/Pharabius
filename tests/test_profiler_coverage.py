from __future__ import annotations

from pathlib import Path

from pharabius.core.profiler import profile_repository


def test_profile_empty_repository(tmp_path: Path) -> None:
    profile = profile_repository(tmp_path)

    assert profile.project_name == tmp_path.name
    assert profile.detected_languages == []
    assert profile.package_managers == []
    assert profile.analysis_confidence == "Low"
    assert "No source languages detected" in profile.limitations[0]


def test_profile_monorepo_with_pnpm_workspace(tmp_path: Path) -> None:
    (tmp_path / "pnpm-workspace.yaml").write_text(
        "packages:\n  - 'apps/*'\n  - 'packages/*'\n", encoding="utf-8"
    )
    (tmp_path / "apps").mkdir()
    (tmp_path / "apps" / "web").mkdir()
    (tmp_path / "apps" / "web" / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "packages").mkdir()
    (tmp_path / "packages" / "ui").mkdir()
    (tmp_path / "packages" / "ui" / "package.json").write_text("{}", encoding="utf-8")

    profile = profile_repository(tmp_path)

    assert profile.monorepo is True
    assert "apps/web" in profile.services_or_packages
    assert "packages/ui" in profile.services_or_packages


def test_profile_infrastructure_files(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text("resource {}", encoding="utf-8")
    (tmp_path / "k8s").mkdir()
    (tmp_path / "k8s" / "deployment.yaml").write_text("apiVersion: v1\n", encoding="utf-8")

    profile = profile_repository(tmp_path)

    assert "main.tf" in profile.infrastructure_files
    assert "k8s/deployment.yaml" in profile.infrastructure_files


def test_profile_risk_keywords(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "payment_service.py").write_text(
        "def process_payment(): pass\n", encoding="utf-8"
    )
    (tmp_path / "src" / "auth_middleware.py").write_text(
        "def check_token(): pass\n", encoding="utf-8"
    )

    profile = profile_repository(tmp_path)

    assert "src/payment_service.py" in profile.risk_sensitive_areas
    assert "src/auth_middleware.py" in profile.risk_sensitive_areas


def test_profile_go_project(tmp_path: Path) -> None:
    (tmp_path / "main.go").write_text("package main\n", encoding="utf-8")
    (tmp_path / "go.mod").write_text("module example.com/app\n", encoding="utf-8")

    profile = profile_repository(tmp_path)

    assert "Go" in profile.detected_languages
    assert "go" in profile.package_managers
    assert "main.go" in profile.entry_points


def test_profile_go_test_framework_detected(tmp_path: Path) -> None:
    """Go *_test.go files add 'Go testing' to test frameworks."""
    (tmp_path / "main.go").write_text("package main\n", encoding="utf-8")
    (tmp_path / "main_test.go").write_text(
        'package main\nimport "testing"\nfunc TestMain(t *testing.T) {}\n',
        encoding="utf-8",
    )
    (tmp_path / "go.mod").write_text("module example.com/app\n", encoding="utf-8")

    profile = profile_repository(tmp_path)

    assert "Go testing" in profile.test_frameworks
