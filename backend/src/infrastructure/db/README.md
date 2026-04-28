# infrastructure/db

Async PostgreSQL via SQLAlchemy 2.0 + asyncpg + Alembic migrations.

**Implementation Phase**: 49.2 (engine + session + base ORM model + first migration)
**Multi-tenant**: All ORM models inherit `TenantScopedMixin` (Sprint 49.2). RLS policies in Sprint 49.3 (`platform/identity/`).

## Sprint 49.2 deliverables (planned)

- `session.py` — async session factory, FastAPI dependency
- `base.py` — declarative base + TenantScopedMixin (forces `tenant_id NOT NULL`)
- `migrations/` — Alembic env + first revision (sessions / messages / state_snapshots tables per `09-db-schema-design.md`)
