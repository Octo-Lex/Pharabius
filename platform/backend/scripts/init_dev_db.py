"""Dev database initialization script.

Creates all tables using SQLAlchemy metadata.
For production, use: alembic upgrade head

Usage:
    cd platform/backend
    python scripts/init_dev_db.py
"""

from __future__ import annotations

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy.ext.asyncio import async_engine_from_config


async def main() -> None:
    from pharabius_platform.models import Base

    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://pharabius:pharabius_dev@localhost:5432/pharabius",
    )

    print(f"Creating tables at: {database_url.split('@')[-1]}")

    engine = async_engine_from_config(
        {"sqlalchemy.url": database_url},
        prefix="sqlalchemy.",
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print(f"Created {len(Base.metadata.tables)} tables:")
    for name in sorted(Base.metadata.tables):
        print(f"  - {name}")

    await engine.dispose()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
