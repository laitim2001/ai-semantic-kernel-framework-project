# Sprint 173 Plan — Tenant Scope Foundation

**Phase**: 48 — Memory System Improvements
**Sprint**: 173
**Branch**: `research/memory-system-enterprise`
**Worktree**: `ai-semantic-kernel-memory-research`
**Date**: 2026-04-20
**Depends on**: Sprint 172 (L2 PostgreSQL schema hosts new scope columns)

---

## Background

V9 audit + enterprise research identified: IPA currently has only `user_id` isolation. Enterprise deployment requires 4-level scope:
- `org_id` — hard isolation (different companies/BUs)
- `workspace_id` — team/department
- `user_id` — individual (existing)
- `agent_id` — specific expert agent (ties to Phase 46 Expert Registry)

Also addresses Sprint 170 Implementation Notes item #1 (tenant enumeration via Redis key pattern) and fulfills Security Engineer's v1 requirement for a JWT ADR before implementation.

---

## Key Architecture Decision: ADR First

**Sprint 173 begins with an ADR (Architecture Decision Record)** before any code. The ADR defines:
- JWT claim schema for scope propagation
- Key rotation strategy
- Membership validation mechanism
- Defense-in-depth: middleware + repository layer + storage layer enforcement
- Non-destructive rollout: legacy entries default `org_id="default"`

No code lands until ADR reviewed and approved.

---

## User Stories

### US-1: Hard Org-Level Isolation
- **As** an enterprise platform operator
- **I want** memories from `org_A` to be completely invisible to users in `org_B`
- **So that** multi-tenant SaaS deployment meets compliance requirements

### US-2: Scope Context Flows from JWT Only
- **As** a security engineer
- **I want** scope values derived exclusively from server-verified JWT claims, never request body
- **So that** clients cannot forge cross-tenant access via payload manipulation

### US-3: Redis Key Pattern Does Not Leak Tenants
- **As** a security engineer
- **I want** Redis keys containing tenant IDs hashed or obfuscated
- **So that** `SCAN memory:counter:*` cannot enumerate active tenants

---

## Technical Specifications

### 0. Architecture Decision Record (prerequisite deliverable)

`docs/02-architecture/adr/ADR-048-tenant-scope-for-memory.md`

Contents:
- JWT claim schema: `{sub, org_id, workspace_id, agent_memberships, exp, iat, iss}`
- Signing: RS256 with key rotation every 90 days via `JWT_KEY_ROTATION_SCHEDULE`
- Membership validation: DB lookup `user_memberships` table on each request (cached 5min)
- Defense layers: (1) FastAPI dependency reads JWT → ScopeContext; (2) all memory methods require ScopeContext typed param; (3) Qdrant + PG queries include scope filter mandatorily
- Legacy entry handling: auto-assign `org_id="default"`, `workspace_id="default"` on access
- Negative test matrix: forged JWT, expired JWT, valid JWT wrong org, missing org claim

### Backend — Core Types

1. **`ScopeContext` dataclass** (`integrations/memory/scope.py` — new file)
   ```python
   @dataclass(frozen=True)
   class ScopeContext:
       org_id: str              # required, never empty
       workspace_id: str = "default"
       user_id: str = ""
       agent_id: Optional[str] = None

       def to_filter(self) -> dict: ...           # for Qdrant payload filter
       def to_sql_where(self) -> dict: ...        # for SQLAlchemy filter
       def as_hashed_key_prefix(self) -> str: ... # SHA-256 prefix for Redis keys
   ```
   Immutable. Any code accepting raw string scope is a bug.

2. **Key Hashing**
   - Redis keys use SHA-256(org_id + workspace_id + user_id)[:16] as prefix
   - New pattern: `memory:counter:{layer}:{hashed_prefix}:{memory_id}` (replaces Sprint 170 pattern)
   - Migration: Sprint 173 includes script to re-key existing counters

### Backend — Middleware

3. **JWT Scope Injection** (`api/middleware/tenant_scope.py` — new)
   - FastAPI dependency `get_scope(request) -> ScopeContext`
   - Validates JWT signature + expiration
   - Extracts claims + cross-checks `user_memberships` table
   - Rejects with 401 if invalid; 403 if scope not permitted for requested resource
   - Attaches `ScopeContext` to request state

4. **Membership Validation**
   - New table `user_memberships` (user_id, org_id, workspace_id, role, created_at, revoked_at)
   - Cached in Redis 5min via `@lru_cache` wrapper on repository method

### Backend — Memory Layer Changes

5. **`UnifiedMemoryManager` refactor** (`unified_memory.py`)
   - All public methods take `scope: ScopeContext` typed parameter (not `user_id: str`)
   - Legacy signature shim: `def _legacy_shim(user_id: str) -> ScopeContext` converts to default org during grace period
   - Feature flag `MEMORY_SCOPE_STRICT_MODE` (default False for dev; True for prod) — when True, reject calls without scope

6. **Qdrant Collection Strategy**
   - Collection-per-org: `ipa_memory_{org_id}`
   - `Mem0Client.__init__` accepts `org_id`, creates/uses the appropriate collection
   - Legacy data migrated into `ipa_memory_default` collection

7. **PostgreSQL Column Additions**
   - `session_memory` table (Sprint 172) ALTER: add `org_id VARCHAR(64) NOT NULL DEFAULT 'default'`, `workspace_id VARCHAR(64) NOT NULL DEFAULT 'default'`, `agent_id VARCHAR(64) NULL`
   - Indexes: `(org_id, workspace_id, user_id)` composite

### Backend — Pipeline Integration

8. **Step 1 Memory Read**
   - Retrieves `ScopeContext` from request state (propagated by middleware)
   - Passes to `UnifiedMemoryManager.search(query, scope=ctx.scope)`

9. **Step 8 Postprocess**
   - Same — all memory writes include scope

### Testing

10. **Unit Tests**
    - `test_scope_context.py` — immutability, filter serialization, hashed prefix
    - `test_jwt_scope_middleware.py` — valid JWT → ScopeContext; forged → 401; wrong org → 403
    - `test_memory_scope_enforcement.py` — memory from org_A invisible to org_B caller
    - `test_legacy_shim.py` — requests without scope during grace period routed to "default" org

11. **Integration Test**
    - `test_multi_org_isolation.py` — seed memories in org_A and org_B → verify complete isolation via real API calls

12. **Security Regression Test**
    - `test_jwt_forgery.py` — attempt scope injection via body → middleware rejects
    - `test_scope_key_enumeration.py` — `redis-cli SCAN memory:counter:*` reveals hashed prefixes, not plaintext user_ids

---

## File Changes

| File | Action | Purpose |
|------|--------|---------|
| `docs/02-architecture/adr/ADR-048-tenant-scope-for-memory.md` | Create | ADR — MUST be approved before code |
| `backend/src/integrations/memory/scope.py` | Create | `ScopeContext` dataclass |
| `backend/src/api/middleware/tenant_scope.py` | Create | JWT scope injection middleware |
| `backend/src/domain/auth/models/user_membership.py` | Create | `UserMembership` ORM |
| `backend/alembic/versions/XXX_add_user_memberships.py` | Create | Migration |
| `backend/alembic/versions/XXX_add_session_memory_scope_cols.py` | Create | ALTER session_memory |
| `backend/src/integrations/memory/unified_memory.py` | Modify | All methods take `ScopeContext` |
| `backend/src/integrations/memory/mem0_client.py` | Modify | Collection-per-org; accept org_id |
| `backend/src/integrations/orchestration/pipeline/steps/step1_memory.py` | Modify | Propagate scope to memory layer |
| `backend/src/integrations/orchestration/pipeline/steps/step8_postprocess.py` | Modify | Same for write path |
| `backend/scripts/migrate_redis_counter_keys.py` | Create | Re-key existing counters |
| `backend/scripts/migrate_legacy_qdrant_to_default_org.py` | Create | Migrate mem0 legacy data |
| `backend/tests/unit/integrations/memory/test_scope_context.py` | Create | ScopeContext tests |
| `backend/tests/unit/api/middleware/test_jwt_scope_middleware.py` | Create | Middleware tests |
| `backend/tests/unit/integrations/memory/test_memory_scope_enforcement.py` | Create | Enforcement tests |
| `backend/tests/integration/security/test_multi_org_isolation.py` | Create | E2E isolation |
| `backend/tests/security/test_jwt_forgery.py` | Create | Forgery rejection |

---

## Acceptance Criteria

- [ ] **AC-1**: ADR-048 committed and reviewed before code lands
- [ ] **AC-2**: `ScopeContext` is frozen dataclass; all memory methods take it as typed param
- [ ] **AC-3**: JWT middleware rejects forged tokens (signature invalid), expired tokens, missing `org_id` claim
- [ ] **AC-4**: `user_memberships` lookup cached 5min; stale membership < 5min acceptable
- [ ] **AC-5**: Legacy entries (no scope) auto-routed to `org_id="default"` via shim (feature flag `MEMORY_SCOPE_STRICT_MODE=False`)
- [ ] **AC-6**: Redis counter keys hashed — `SCAN memory:counter:*` reveals 16-char hex prefixes, not plaintext user_ids
- [ ] **AC-7**: Qdrant collection-per-org — org_A and org_B use different collections
- [ ] **AC-8**: `session_memory` has `org_id`, `workspace_id`, `agent_id` columns with correct defaults
- [ ] **AC-9**: E2E: request with org_A JWT cannot see memories of org_B (test via real HTTP calls)
- [ ] **AC-10**: Counter key migration script moves legacy keys to hashed format (idempotent)
- [ ] **AC-11**: `MEMORY_SCOPE_STRICT_MODE=True` → missing scope raises `ScopeNotProvidedError` (not silent default)

---

## Out of Scope

- Cross-tenant memory sharing / promotion path (future phase; research Doc 08 §A.3 concept)
- Tenant-specific rate limiting (ops concern)
- Multi-region data residency (compliance phase)
- Fine-grained per-document permissions (OPA / Rego — later)
