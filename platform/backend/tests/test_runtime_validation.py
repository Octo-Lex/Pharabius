"""S01-S05 tests — Runtime validation results.

These tests verify the runtime smoke test script structure,
Dockerfile correctness, and compose configuration.
The actual runtime validation is performed by running
`python scripts/runtime_smoke_test.py` with Docker Desktop running.
"""

from __future__ import annotations

from pathlib import Path

PLATFORM_DIR = Path(__file__).resolve().parent.parent.parent


class TestDockerfile:
    """Verify backend Dockerfile is correct."""

    def test_dockerfile_exists(self) -> None:
        assert (PLATFORM_DIR / "backend" / "Dockerfile").exists()

    def test_dockerfile_installs_pharabius_first(self) -> None:
        content = (PLATFORM_DIR / "backend" / "Dockerfile").read_text(encoding="utf-8")
        # Must install pharabius CLI package before platform
        assert "COPY pyproject.toml /tmp/pharabius/" in content
        assert "COPY src/ /tmp/pharabius/src/" in content
        assert "pip install --no-cache-dir /tmp/pharabius/" in content

    def test_dockerfile_installs_platform(self) -> None:
        content = (PLATFORM_DIR / "backend" / "Dockerfile").read_text(encoding="utf-8")
        assert "COPY platform/backend/pyproject.toml /app/" in content
        assert "COPY platform/backend/src/ /app/src/" in content
        assert "pip install --no-cache-dir ." in content

    def test_dockerfile_creates_storage_dir(self) -> None:
        content = (PLATFORM_DIR / "backend" / "Dockerfile").read_text(encoding="utf-8")
        assert "mkdir -p /var/lib/pharabius/bundles" in content

    def test_dockerfile_exposes_8000(self) -> None:
        content = (PLATFORM_DIR / "backend" / "Dockerfile").read_text(encoding="utf-8")
        assert "EXPOSE 8000" in content
        assert "uvicorn" in content


class TestComposeConfig:
    """Verify docker-compose.yml is valid."""

    def test_compose_file_exists(self) -> None:
        assert (PLATFORM_DIR / "docker-compose.yml").exists()

    def test_compose_has_db_service(self) -> None:
        content = (PLATFORM_DIR / "docker-compose.yml").read_text(encoding="utf-8")
        assert "postgres:16" in content
        assert "POSTGRES_DB: pharabius" in content

    def test_compose_has_backend_service(self) -> None:
        content = (PLATFORM_DIR / "docker-compose.yml").read_text(encoding="utf-8")
        assert "DATABASE_URL" in content
        assert "ADMIN_TOKEN" in content
        assert "STORAGE_PATH" in content

    def test_compose_db_uses_non_default_port(self) -> None:
        content = (PLATFORM_DIR / "docker-compose.yml").read_text(encoding="utf-8")
        # Port 5433 to avoid conflict with local PostgreSQL
        assert "5433:5432" in content

    def test_compose_has_healthcheck(self) -> None:
        content = (PLATFORM_DIR / "docker-compose.yml").read_text(encoding="utf-8")
        assert "pg_isready" in content

    def test_compose_has_named_volumes(self) -> None:
        content = (PLATFORM_DIR / "docker-compose.yml").read_text(encoding="utf-8")
        assert "pgdata:" in content
        assert "bundle_storage:" in content


class TestRuntimeSmokeScript:
    """Verify runtime smoke test script structure."""

    def test_script_exists(self) -> None:
        assert (PLATFORM_DIR / "scripts" / "runtime_smoke_test.py").exists()

    def test_script_has_all_steps(self) -> None:
        content = (PLATFORM_DIR / "scripts" / "runtime_smoke_test.py").read_text(encoding="utf-8")
        assert "S01" in content  # Docker availability
        assert "S02" in content  # Compose config
        assert "S03" in content  # Build and start
        assert "S04" in content  # Schema init
        assert "S05" in content  # Upload
        assert "S06" in content  # Query

    def test_script_creates_sample_bundle(self) -> None:
        content = (PLATFORM_DIR / "scripts" / "runtime_smoke_test.py").read_text(encoding="utf-8")
        assert "create_sample_bundle" in content
        assert "debt-register.json" in content

    def test_script_has_cleanup(self) -> None:
        content = (PLATFORM_DIR / "scripts" / "runtime_smoke_test.py").read_text(encoding="utf-8")
        assert "docker compose" in content
        assert "down -v" in content

    def test_script_tests_upload(self) -> None:
        content = (PLATFORM_DIR / "scripts" / "runtime_smoke_test.py").read_text(encoding="utf-8")
        assert "/api/v1/bundles" in content

    def test_script_tests_query_endpoints(self) -> None:
        content = (PLATFORM_DIR / "scripts" / "runtime_smoke_test.py").read_text(encoding="utf-8")
        assert "/api/v1/repositories" in content
        assert "/api/v1/portfolio" in content


class TestBackendStartup:
    """Verify backend app initializes DB on startup."""

    def test_main_has_startup_event(self) -> None:
        content = (
            Path(__file__).resolve().parent.parent / "src/pharabius_platform/main.py"
        ).read_text(encoding="utf-8")
        assert "on_event" in content or "lifespan" in content
        assert "init_db" in content

    def test_main_reads_database_url(self) -> None:
        content = (
            Path(__file__).resolve().parent.parent / "src/pharabius_platform/main.py"
        ).read_text(encoding="utf-8")
        assert "DATABASE_URL" in content
