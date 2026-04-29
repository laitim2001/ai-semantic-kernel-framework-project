# infrastructure/db

Async PostgreSQL via SQLAlchemy 2.0 + asyncpg + Alembic migrations.

**Implementation Phase**: Sprint 49.2 ✅ COMPLETED (2026-04-29)

## Sprint 49.2 deliverables — DONE

### Code (4 modules + base + 4 ORM model files)
- `base.py` — `Base` (DeclarativeBase) + `TenantScopedMixin` (forces `tenant_id NOT NULL`)
- `engine.py` — async engine + session factory singletons + `dispose_engine()`
- `session.py` — `get_db_session()` FastAPI async dependency
- `exceptions.py` — `DBException` / `StateConflictError` / `MigrationError`
- `models/identity.py` — Tenant / User / Role / UserRole / RolePermission
- `models/sessions.py` — Session / Message (partitioned) / MessageEvent (partitioned)
- `models/tools.py` — ToolRegistry / ToolCall / ToolResult
- `models/state.py` — StateSnapshot / LoopState + `compute_state_hash` + `append_snapshot`

### Migrations (4)
- `0001_initial_identity` — 5 identity tables
- `0002_sessions_partitioned` — sessions + 3 monthly partitions for messages + 3 for message_events
- `0003_tools` — tools_registry (global) + tool_calls + tool_results
- `0004_state` — state_snapshots (append-only trigger) + loop_states + sessions FK back-fill

### Tests (29 PASS + 1 SKIPPED)
- `test_engine_connect.py` — 3 ping/version/factory tests
- `test_models_crud.py` — 8 CRUD tests (Tenant/User/Session/Message/MessageEvent/ToolRegistry/ToolCall/ToolResult)
- `test_partition_routing.py` — 4 tests verify `tableoid::regclass` routing
- `test_state_append_only.py` — 3 tests + 1 skipped (TRUNCATE → 49.3)
- `test_state_race.py` — 7 tests (StateVersion 雙因子 race; 5x parametrize anti-flaky)
- `test_imports.py` — 4 tests carried from 49.1 (LLM SDK leak guard etc.)

## Multi-tenant rule (`.claude/rules/multi-tenant-data.md` 鐵律 1)

All session-scoped tables inherit `TenantScopedMixin`:
- ✅ users, roles, sessions, messages, message_events, tool_calls, state_snapshots, loop_states

Tables that DO NOT inherit (intentionally global / junction):
- `tenants` — root of the hierarchy
- `tools_registry` — global tool metadata, shared across tenants
- `user_roles` — junction; tenant inferred via FK chain
- `role_permissions` — tenant inferred via role
- `tool_results` — tenant inferred via tool_call → session → tenant

## Usage

### Run migrations
```bash
cd backend
alembic upgrade head            # apply all
alembic downgrade base          # revert all
alembic current                 # show current
alembic history --verbose       # full history
```

### Run tests
```bash
# Pre-requisite: docker compose up postgres
docker compose -f docker-compose.dev.yml up -d postgres

# From backend/
cd backend
alembic upgrade head
pytest tests/unit/infrastructure/db/ -v
```

### Use in FastAPI
```python
from infrastructure.db import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

@router.get("/")
async def list_sessions(db: AsyncSession = Depends(get_db_session)):
    ...
```

## Sprint 49.3 will add (deferred from 49.2)
- audit_log + append-only + hash chain + STATEMENT-level TRUNCATE trigger
- api_keys / rate_limits
- 5-layer memory tables (memory_system / memory_tenant / memory_role / memory_user / memory_session_summary)
- approvals / risk_assessments / guardrail_events
- RLS policies on all session-scoped tables
- per-request `SET LOCAL app.tenant_id` middleware
- pg_partman automation (rolling +6 months partitions)
- Qdrant tenant-aware namespace
