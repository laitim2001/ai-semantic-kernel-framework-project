"""
infrastructure.db — Async SQLAlchemy 2.0 + Alembic migrations.

Sprint 49.2 deliverables:
    - Base + TenantScopedMixin (base.py)
    - DBException + StateConflictError + MigrationError (exceptions.py)
    - AsyncEngine + async_sessionmaker singletons (engine.py)
    - FastAPI dependency get_db_session (session.py)
    - Alembic migrations 0001-0004 (migrations/versions/)
    - 13 ORM models (models/)

Public surface:
    Base, TenantScopedMixin               — declarative base + multi-tenant rule
    DBException, StateConflictError       — domain exceptions
    get_engine, get_session_factory       — singleton accessors
    dispose_engine                        — teardown helper
    get_db_session                        — FastAPI dependency
    models                                — re-export of all ORM models

Per .claude/rules/multi-tenant-data.md, all session-scoped tables in
this package inherit TenantScopedMixin.
"""

from __future__ import annotations

from infrastructure.db.base import Base, TenantScopedMixin
from infrastructure.db.engine import (
    dispose_engine,
    get_engine,
    get_session_factory,
)
from infrastructure.db.exceptions import (
    DBException,
    MigrationError,
    StateConflictError,
)
from infrastructure.db.session import get_db_session

__all__ = [
    "Base",
    "TenantScopedMixin",
    "DBException",
    "StateConflictError",
    "MigrationError",
    "get_engine",
    "get_session_factory",
    "dispose_engine",
    "get_db_session",
]
