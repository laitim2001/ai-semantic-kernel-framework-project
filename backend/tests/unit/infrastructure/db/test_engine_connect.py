"""
File: backend/tests/unit/infrastructure/db/test_engine_connect.py
Purpose: Smoke test — async engine connects to docker compose PostgreSQL and runs SELECT 1.
Category: Tests / Infrastructure / DB
Scope: Sprint 49.2 Day 1.7

Description:
    Asserts that the singleton AsyncEngine + async_sessionmaker built from
    Settings can establish a real connection to the docker compose
    PostgreSQL service and execute a trivial query.

    Per .claude/rules/testing.md AP-10 對策:
        Tests use the REAL docker compose PostgreSQL container.
        DO NOT use SQLite — V1 教訓 mock vs real divergence.

    Pre-requisite:
        docker compose -f docker-compose.dev.yml up -d postgres

Created: 2026-04-29 (Sprint 49.2 Day 1.7)
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import dispose_engine, get_engine, get_session_factory


@pytest.mark.asyncio
async def test_engine_can_ping_postgres() -> None:
    """Engine can connect to docker compose PostgreSQL and run SELECT 1."""
    engine = get_engine()
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
    finally:
        await dispose_engine()


@pytest.mark.asyncio
async def test_engine_reports_pg_version() -> None:
    """Engine reports a real PostgreSQL version (validates real DB, not mock)."""
    engine = get_engine()
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar() or ""
            assert "PostgreSQL" in version
            # Pinned to PG 16+ per docker-compose.dev.yml
            assert "16." in version or "17." in version
    finally:
        await dispose_engine()


@pytest.mark.asyncio
async def test_session_factory_yields_async_session() -> None:
    """Session factory yields a real AsyncSession bound to the engine."""
    factory = get_session_factory()
    try:
        async with factory() as session:
            assert isinstance(session, AsyncSession)
            result = await session.execute(text("SELECT 42"))
            assert result.scalar() == 42
    finally:
        await dispose_engine()
