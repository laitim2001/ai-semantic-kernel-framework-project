# Sprint 173 Checklist — Tenant Scope Foundation

**Sprint**: 173
**Branch**: `research/memory-system-enterprise`
**Plan**: [sprint-173-plan.md](sprint-173-plan.md)

---

## ADR — MUST be first deliverable

- [ ] `docs/02-architecture/adr/ADR-048-tenant-scope-for-memory.md` drafted
- [ ] JWT claim schema defined (`sub, org_id, workspace_id, agent_memberships, exp, iat, iss`)
- [ ] Key rotation strategy (RS256, 90-day rotation)
- [ ] Membership validation flow (DB + 5min cache)
- [ ] Defense layers (middleware + repository + storage)
- [ ] Negative test matrix documented
- [ ] ADR reviewed and approved before code phase begins

## Backend — Core Types

- [ ] `ScopeContext` frozen dataclass in `integrations/memory/scope.py`
- [ ] `to_filter()`, `to_sql_where()`, `as_hashed_key_prefix()` methods
- [ ] `ScopeNotProvidedError` exception class
- [ ] SHA-256 hash helper for key prefixes

## Backend — JWT Middleware

- [ ] `get_scope(request)` FastAPI dependency in `api/middleware/tenant_scope.py`
- [ ] RS256 JWT signature verification
- [ ] Expiration check
- [ ] `user_memberships` cross-check with 5min cache
- [ ] 401 on invalid signature / expired
- [ ] 403 on valid JWT but scope mismatch
- [ ] ScopeContext attached to `request.state.scope`

## Backend — Membership Schema

- [ ] `UserMembership` ORM model in `domain/auth/models/`
- [ ] Alembic migration for `user_memberships` table
- [ ] Repository with caching (5min lru_cache or Redis)
- [ ] Indexes: `(user_id)`, `(org_id, workspace_id)`

## Backend — Memory Layer Refactor

- [ ] `UnifiedMemoryManager.search()` takes `scope: ScopeContext`
- [ ] `UnifiedMemoryManager.get()` takes `scope: ScopeContext`
- [ ] `UnifiedMemoryManager.add()` takes `scope: ScopeContext`
- [ ] `UnifiedMemoryManager.update_importance()` takes `scope: ScopeContext`
- [ ] Legacy shim for grace period (converts `user_id` → default ScopeContext)
- [ ] `MEMORY_SCOPE_STRICT_MODE` feature flag
- [ ] Counter key pattern uses hashed prefix (replaces Sprint 170 format)

## Backend — Mem0 Collection Strategy

- [ ] `Mem0Client.__init__(org_id, ...)` selects/creates `ipa_memory_{org_id}`
- [ ] Legacy data → `ipa_memory_default`
- [ ] Collection lifecycle (auto-create on first use, safe reuse)

## Backend — PostgreSQL Scope Columns

- [ ] Alembic migration adds `org_id`, `workspace_id`, `agent_id` to `session_memory`
- [ ] Defaults: `org_id='default'`, `workspace_id='default'`, `agent_id=NULL`
- [ ] Composite index `(org_id, workspace_id, user_id)`
- [ ] `SessionMemoryRepository` queries include scope filter

## Backend — Pipeline Integration

- [ ] `step1_memory.py` reads `ctx.scope` from pipeline context
- [ ] `step1_memory.py` passes `scope` to `memory_manager.search()`
- [ ] `step8_postprocess.py` same for write
- [ ] Pipeline context object has `scope: ScopeContext` field

## Migration Scripts

- [ ] `scripts/migrate_redis_counter_keys.py` — rehash existing counters, idempotent
- [ ] `scripts/migrate_legacy_qdrant_to_default_org.py` — move legacy data to default collection
- [ ] Both dry-run + apply modes
- [ ] Progress output

## Tests — Unit

- [ ] `test_scope_context.py` — immutability, filter serialization
- [ ] `test_scope_context.py` — hashed prefix stable and consistent
- [ ] `test_jwt_scope_middleware.py` — valid JWT → ScopeContext attached
- [ ] `test_jwt_scope_middleware.py` — invalid signature → 401
- [ ] `test_jwt_scope_middleware.py` — expired → 401
- [ ] `test_jwt_scope_middleware.py` — missing org_id → 401
- [ ] `test_jwt_scope_middleware.py` — scope mismatch → 403
- [ ] `test_memory_scope_enforcement.py` — org_A memory invisible to org_B
- [ ] `test_memory_scope_enforcement.py` — strict mode raises on missing scope
- [ ] `test_legacy_shim.py` — grace mode routes to default
- [ ] `test_user_membership_cache.py` — 5min TTL, invalidation on revoke

## Tests — Integration

- [ ] `test_multi_org_isolation.py` — real API calls with 2 JWTs, verify isolation
- [ ] `test_multi_org_isolation.py` — pipeline Step 1 read + Step 8 write both scope-aware

## Tests — Security

- [ ] `test_jwt_forgery.py` — request body scope injection ignored
- [ ] `test_jwt_forgery.py` — claim tampering without re-signing rejected
- [ ] `test_scope_key_enumeration.py` — `SCAN memory:counter:*` reveals hashes only

## Verification

- [ ] All Python files pass `black`, `isort`, `flake8`, `mypy`
- [ ] Alembic migrations: `upgrade head` + `downgrade -1` work
- [ ] `pytest backend/tests/unit/integrations/memory/test_scope_context.py test_memory_scope_enforcement.py test_legacy_shim.py -v`
- [ ] `pytest backend/tests/unit/api/middleware/test_jwt_scope_middleware.py test_user_membership_cache.py -v`
- [ ] `pytest backend/tests/integration/security/test_multi_org_isolation.py -v`
- [ ] `pytest backend/tests/security/ -v`
- [ ] Manual: issue 2 JWTs for 2 orgs → call API → verify isolation via logs
- [ ] Manual: `redis-cli SCAN memory:counter:*` → verify hashed prefixes visible (not raw user_ids)
- [ ] Manual: run migration scripts on staging → spot check 10 entries for correctness
- [ ] ADR-048 linked from Phase 48 README
