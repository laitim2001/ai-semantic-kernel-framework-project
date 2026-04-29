# platform_layer/middleware

Per-request middleware + DB session dependencies.

**Implementation Phase**: Sprint 49.3 ✅ COMPLETED (2026-04-29)

## Sprint 49.3 deliverables

### `tenant_context.py`

| Component | Purpose |
|-----------|---------|
| `TenantContextMiddleware` | Reads `X-Tenant-Id` header → sets `request.state.tenant_id` |
| `get_db_session_with_tenant` | FastAPI dep that opens AsyncSession + `set_config('app.tenant_id', :tid, true)` per-request, with commit/rollback |

### Behaviour

- Missing `X-Tenant-Id` header → **401 Unauthorized**
- Invalid UUID format → **400 Bad Request**
- Valid UUID → request proceeds; PostgreSQL RLS policies (migration 0009) filter rows by tenant scope.

## Usage

```python
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from platform_layer.middleware import TenantContextMiddleware, get_db_session_with_tenant

app = FastAPI()
app.add_middleware(TenantContextMiddleware)

@app.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db_session_with_tenant)):
    # All queries here are auto-scoped to request's tenant via RLS
    ...
```

## Future (Phase 49.4+)

- Replace `X-Tenant-Id` header extraction with **JWT claim parsing**.
- `request.state.tenant_id` contract stays identical, so endpoints don't change.

## Related

- `0009_rls_policies.py` migration — the RLS policies this dep activates
- `.claude/rules/multi-tenant-data.md` 鐵律 3 (every endpoint dep)
- `14-security-deep-dive.md` §RLS / SET LOCAL
