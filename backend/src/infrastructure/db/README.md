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

## Sprint 49.3 deliverables — DONE (2026-04-29)

### Migrations (5 new: 0005-0009)
- `0005_audit_log_append_only` — audit_log + ROW UPDATE/DELETE trigger + STATEMENT TRUNCATE trigger + state_snapshots STATEMENT TRUNCATE 補裝（49.2 deferred）
- `0006_api_keys_rate_limits` — 2 tables + 4 indexes (incl. partial WHERE status='active')
- `0007_memory_layers` — 5 memory tables: memory_system / memory_tenant / memory_role / memory_user / memory_session_summary
- `0008_governance` — 3 tables: approvals / risk_assessments / guardrail_events
- `0009_rls_policies` — RLS on 13 tenant-scoped tables (26 policies; ENABLE + FORCE)

### ORM models (4 new files)
- `audit.py` — AuditLog (BIGSERIAL pk, hash chain via `audit_helper.py`)
- `api_keys.py` — ApiKey + RateLimit (TenantScopedMixin)
- `memory.py` — 5 memory layer classes (2 TenantScopedMixin, 2 junction, 1 global)
- `governance.py` — Approval / RiskAssessment / GuardrailEvent (junction-via-session)

### Helpers
- `audit_helper.py` — `compute_audit_hash` + `append_audit` with tenant-scoped chain

### Tests added (33 new = 73 total all-green)
- `test_audit_append_only.py` (6)
- `test_api_keys_crud.py` (5)
- `test_memory_models_crud.py` (6)
- `test_governance_models_crud.py` (6)
- `test_rls_enforcement.py` (6 — uses `rls_app_role` SET LOCAL ROLE)
- `test_qdrant_namespace.py` (3)
- security `test_red_team_isolation.py` (6 — AC-10 attack vectors)

### 🚧 Carried forward to Sprint 49.4
- **pg_partman extension**: `postgres:16-alpine` image lacks the extension. Needs image upgrade + Dockerfile + docker-compose env adjustment in 49.4 lint+infra phase.

## Multi-tenant Rules cross-check

| Rule | Status |
|------|--------|
| 鐵律 1 — All session-scoped tables have `tenant_id NOT NULL` | ✅ 13 RLS-eligible tables |
| 鐵律 2 — Every query filters by `tenant_id` (or RLS) | ✅ RLS USING clause + app-layer filter |
| 鐵律 3 — Every endpoint depends on `get_db_session_with_tenant` | ✅ middleware + dep ready (`platform_layer/middleware/`) |
