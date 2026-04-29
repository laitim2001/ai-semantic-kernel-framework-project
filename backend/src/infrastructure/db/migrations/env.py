"""
File: backend/src/infrastructure/db/migrations/env.py
Purpose: Alembic environment for V2 async migrations (SQLAlchemy 2.0 + asyncpg).
Category: Infrastructure / Migration runtime
Scope: Sprint 49.2 (initial Alembic setup)
Owner: infrastructure/db owner; per 09-db-schema-design.md migration plan

Description:
    Drives Alembic forward / reverse migrations for the V2 backend. Loads
    DATABASE_URL from core.config.Settings (single source of truth, shared
    with the runtime async engine in infrastructure/db/engine.py).

    Async pattern (per SQLAlchemy 2.0 cookbook):
        run_migrations_online() schedules run_async_migrations() on a fresh
        AsyncEngine + NullPool, runs DDL inside a single transaction via
        connection.run_sync(do_run_migrations), then disposes the engine.

Created: 2026-04-29 (Sprint 49.2 Day 1.2)
Last Modified: 2026-04-29

Modification History:
    - 2026-04-29: Initial creation (Sprint 49.2 Day 1.2)

Related:
    - backend/alembic.ini (this env's parent config)
    - backend/src/infrastructure/db/base.py (Base.metadata target — Sprint 49.2 Day 1.3)
    - backend/src/core/config/__init__.py (Settings.database_url)
    - 09-db-schema-design.md §Migration 策略
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ---------------------------------------------------------------------
# Alembic Config + logging
# ---------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------
# Single-source DATABASE_URL from Settings (NOT alembic.ini)
# Why: avoid drift between runtime engine + migration runner.
# ---------------------------------------------------------------------
from core.config import get_settings  # noqa: E402

config.set_main_option("sqlalchemy.url", get_settings().database_url)

from infrastructure.db import models  # noqa: E402,F401  (registers ORM)

# ---------------------------------------------------------------------
# Target metadata (Base.metadata accumulates all ORM model tables)
# Models are imported here so Alembic autogenerate sees them.
# ---------------------------------------------------------------------
from infrastructure.db.base import Base  # noqa: E402,F401

target_metadata = Base.metadata


# ---------------------------------------------------------------------
# Offline mode (emit SQL to stdout; no DB connection)
# ---------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emit SQL to stdout."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------
# Online mode (live async DB connection)
# ---------------------------------------------------------------------
def do_run_migrations(connection: Connection) -> None:
    """Sync runner invoked by AsyncConnection.run_sync."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Build an AsyncEngine with NullPool, run migrations, dispose."""
    section = config.get_section(config.config_ini_section, {})
    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (live async connection)."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------
# Entry: dispatch by mode
# ---------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
