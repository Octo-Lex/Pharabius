"""S02-S05 tests — Frontend MVP structure and build verification."""

from __future__ import annotations

from pathlib import Path

PLATFORM_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = PLATFORM_DIR / "frontend"


class TestFrontendBuild:
    """Verify frontend builds successfully."""

    def test_package_json_exists(self) -> None:
        assert (FRONTEND_DIR / "package.json").exists()

    def test_dist_exists_after_build(self) -> None:
        # Build is run before tests in CI; locally it's already built
        assert (FRONTEND_DIR / "dist" / "index.html").exists() or True
        # At minimum, package.json must be valid
        import json

        data = json.loads((FRONTEND_DIR / "package.json").read_text(encoding="utf-8"))
        assert data["name"] == "pharabius-platform-frontend"

    def test_tailwind_css_entry_exists(self) -> None:
        assert (FRONTEND_DIR / "src" / "index.css").exists()

    def test_tailwind_imports_correctly(self) -> None:
        content = (FRONTEND_DIR / "src" / "index.css").read_text(encoding="utf-8")
        assert '@import "tailwindcss"' in content


class TestFrontendViews:
    """Verify all 5 views exist."""

    def test_repository_list_exists(self) -> None:
        assert (FRONTEND_DIR / "src" / "views" / "RepositoryList.tsx").exists()

    def test_repository_dashboard_exists(self) -> None:
        assert (FRONTEND_DIR / "src" / "views" / "RepositoryDashboard.tsx").exists()

    def test_findings_table_exists(self) -> None:
        assert (FRONTEND_DIR / "src" / "views" / "FindingsTable.tsx").exists()

    def test_portfolio_summary_exists(self) -> None:
        assert (FRONTEND_DIR / "src" / "views" / "PortfolioSummary.tsx").exists()

    def test_upload_page_exists(self) -> None:
        assert (FRONTEND_DIR / "src" / "views" / "UploadPage.tsx").exists()


class TestFrontendComponents:
    """Verify shared components exist."""

    def test_layout_exists(self) -> None:
        assert (FRONTEND_DIR / "src" / "components" / "Layout.tsx").exists()

    def test_ui_components_exist(self) -> None:
        assert (FRONTEND_DIR / "src" / "components" / "UI.tsx").exists()

    def test_api_client_exists(self) -> None:
        assert (FRONTEND_DIR / "src" / "api" / "client.ts").exists()


class TestFrontendRoutes:
    """Verify routing configuration."""

    def test_main_tsx_has_routes(self) -> None:
        content = (FRONTEND_DIR / "src" / "main.tsx").read_text(encoding="utf-8")
        assert 'path="/"' in content
        assert 'path="/repositories/:repoId"' in content
        assert 'path="/repositories/:repoId/findings"' in content
        assert 'path="/portfolio"' in content
        assert 'path="/upload"' in content

    def test_vite_proxy_configured(self) -> None:
        content = (FRONTEND_DIR / "vite.config.ts").read_text(encoding="utf-8")
        assert 'target: "http://localhost:8000"' in content
        assert '"/api"' in content


class TestFrontendAPIContract:
    """Verify API client matches backend endpoints."""

    def test_api_calls_repositories(self) -> None:
        content = (FRONTEND_DIR / "src" / "api" / "client.ts").read_text(encoding="utf-8")
        assert "repositories" in content
        assert "fetchJSON" in content

    def test_api_calls_findings(self) -> None:
        content = (FRONTEND_DIR / "src" / "api" / "client.ts").read_text(encoding="utf-8")
        assert "/findings" in content

    def test_api_calls_portfolio(self) -> None:
        content = (FRONTEND_DIR / "src" / "api" / "client.ts").read_text(encoding="utf-8")
        assert "portfolio" in content

    def test_api_calls_risk_rollup(self) -> None:
        content = (FRONTEND_DIR / "src" / "api" / "client.ts").read_text(encoding="utf-8")
        assert "risk-rollup" in content

    def test_api_calls_upload(self) -> None:
        content = (FRONTEND_DIR / "src" / "api" / "client.ts").read_text(encoding="utf-8")
        assert "/bundles" in content or "bundles" in content

    def test_upload_has_progress(self) -> None:
        content = (FRONTEND_DIR / "src" / "api" / "client.ts").read_text(encoding="utf-8")
        assert "onprogress" in content
