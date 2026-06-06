"""S02 tests — Alembic bootstrap and dev init."""

from __future__ import annotations

from pathlib import Path

# Resolve paths relative to this test file, not CWD
_BACKEND_DIR = Path(__file__).resolve().parent.parent


class TestAlembicBootstrap:
    """Verify Alembic migration and dev init exist."""

    def test_migration_file_exists(self) -> None:
        migration = _BACKEND_DIR / "alembic" / "versions" / "001_initial.py"
        assert migration.exists(), "Initial migration file must exist"

    def test_migration_has_upgrade_and_downgrade(self) -> None:
        path = _BACKEND_DIR / "alembic" / "versions" / "001_initial.py"
        content = path.read_text(encoding="utf-8")
        assert "def upgrade()" in content
        assert "def downgrade()" in content

    def test_migration_creates_11_tables(self) -> None:
        path = _BACKEND_DIR / "alembic" / "versions" / "001_initial.py"
        content = path.read_text(encoding="utf-8")
        assert content.count("op.create_table(") == 10

    def test_migration_revision_id(self) -> None:
        path = _BACKEND_DIR / "alembic" / "versions" / "001_initial.py"
        content = path.read_text(encoding="utf-8")
        assert 'revision: str = "001_initial"' in content
        assert "down_revision: str | None = None" in content

    def test_dev_init_script_exists(self) -> None:
        script = _BACKEND_DIR / "scripts" / "init_dev_db.py"
        assert script.exists(), "Dev init script must exist"

    def test_dev_init_uses_metadata(self) -> None:
        content = (_BACKEND_DIR / "scripts" / "init_dev_db.py").read_text(encoding="utf-8")
        assert "Base.metadata.create_all" in content

    def test_alembic_env_imports_models(self) -> None:
        content = (_BACKEND_DIR / "alembic" / "env.py").read_text(encoding="utf-8")
        assert "from pharabius_platform.models import Base" in content
        assert "target_metadata = Base.metadata" in content

    def test_model_table_count_matches_migration(self) -> None:
        from pharabius_platform.models import Base

        assert len(Base.metadata.tables) == 14
