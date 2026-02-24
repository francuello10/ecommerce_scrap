"""
Alembic environment configuration for async SQLAlchemy.
Uses asyncpg driver with the DATABASE_URL_SYNC for migrations.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Add src to python path so models can be imported ─────────────────
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# ── Load app config ───────────────────────────────────────────────────
from core.config import settings  # noqa: E402
# Import all models so Alembic detects them via Base.metadata
from core.models import *  # noqa: F401, F403, E402
from core.database import Base  # noqa: E402

# ── Alembic Config ────────────────────────────────────────────────────
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url from alembic.ini with our settings
config.set_main_option(
    "sqlalchemy.url",
    settings.database_url_sync or settings.database_url.replace("+asyncpg", "")
)


def include_name(name, type_, parent_names):
    """Exclude Directus internal tables from autogenerate."""
    if type_ == "table" and name.startswith("directus_"):
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_name=include_name,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_name=include_name,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
