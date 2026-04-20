# Sprint 173 Plan — Tenant Scope Foundation

**Phase**: 48 — Memory System Improvements
**Sprint**: 173
**Branch**: `research/memory-system-enterprise`
**Worktree**: `ai-semantic-kernel-memory-research`
**Date**: 2026-04-20
**Plan Version**: **v2** (integrated Batch 2 team review findings — 4 CRITICAL + 8 HIGH + 12 MEDIUM + 7 LOW)
**Depends on**: Sprint 172 (L2 PostgreSQL schema hosts new scope columns)

---

## v2 Revision Notes

Batch 2 agent team review surfaced 31 findings on Sprint 173 + Sprint 174. Full findings in `phase-48-review-consolidated.md`. Sprint 173 v2 integrates:

### CRITICAL (4)
1. **[py] `@lru_cache` on async functions is a footgun** — caches coroutine not result → use `async-lru` library / `cachetools.TTLCache` / **Redis preferred** for cross-process invalidation
2. **[sec] Unbounded `agent_memberships` JWT claim array → token DoS** — cap at 50 entries, overflow via DB lookup
3. **[sec] `MEMORY_SCOPE_STRICT_MODE=False` default** risks prod left-on-grace-mode → Prod must `fail-closed` + CI assertion

### HIGH (8)
4. **[arch] Qdrant collection-per-org won't scale past ~500 orgs** → hybrid tier model (T1 dedicated / SMB shared + payload filter); add tier flag in `ScopeContext`
5. **[arch] `ContextVar[ScopeContext]` propagation missing** for `asyncio.gather` / executor fan-out — add explicit AC
6. **[sec] Membership cache invalidation** — 5min TTL = 5min post-revoke access window → add pub/sub invalidation on role change
7. **[sec] 64-bit hash prefix collision risk** → add deployment salt to hash input
8. **[sec] JWT attack matrix incomplete** — need alg:none, HS/RS confusion, kid traversal, jku, jwk spoof tests
9. **[arch] Collection creation non-atomic across restarts** → distributed lock (Redis SET NX)
10. **[qa] Multi-org tests N=2 insufficient** — use N≥3 for transitivity
11. **[qa] ADR must include sign-off table** (security + backend leads + SRE) with PR check labels

### MEDIUM (12) / LOW (7) — see Implementation Notes below

**ADR-048 rewrite required before any code**. Full rewrite spec in Implementation Notes section.

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

---

## v2 Implementation Notes (from Batch 2 team review)

### CRITICAL #1 — Membership Cache (NO lru_cache on async)

```python
# WRONG (footgun):
@lru_cache(maxsize=1000)
async def get_membership(user_id): ...  # caches coroutine, awaiting twice raises RuntimeError

# RIGHT — Redis cache (cross-process, TTL, invalidatable):
async def get_membership(user_id: str) -> list[Membership]:
    cached = await redis.get(f"membership:{user_id}")
    if cached:
        return Membership.parse_list(cached)
    result = await self.repo.get_by_user(user_id)
    await redis.setex(f"membership:{user_id}", 300, json.dumps(...))
    return result

# Alternative: async-lru library (pip install async-lru)
from async_lru import alru_cache
@alru_cache(maxsize=1000, ttl=300)
async def get_membership(user_id): ...
```

### CRITICAL #2 — JWT Claim Bounds

```python
# Claim schema (documented in ADR-048):
{
  "sub": "user_xyz",
  "org_id": "org_abc",
  "workspace_id": "wsp_1",
  "agent_memberships": ["agent_A", ...],  # CAPPED AT 50
  "has_more_memberships": true,            # if user has > 50
  "exp": ..., "iat": ..., "iss": ...
}

# Server-side overflow handling:
if payload.get("has_more_memberships"):
    full_memberships = await db.get_agent_memberships(user_id)  # DB lookup on demand

# Middleware validation:
if len(payload.get("agent_memberships", [])) > 50:
    raise InvalidJWT("agent_memberships exceeds cap")
```

### CRITICAL #3 — Strict Mode Prod Default

```python
# core/settings.py
class Settings(BaseSettings):
    MEMORY_SCOPE_STRICT_MODE: bool = Field(
        default=False,
        description="MUST be True in production. Grace mode only for dev."
    )

    @validator("MEMORY_SCOPE_STRICT_MODE")
    def enforce_prod_strict(cls, v, values):
        if os.getenv("IPA_ENV") == "production" and not v:
            raise ValueError("MEMORY_SCOPE_STRICT_MODE must be True in production")
        return v

# CI test (pytest):
def test_prod_strict_mode_enforced():
    os.environ["IPA_ENV"] = "production"
    with pytest.raises(ValueError):
        Settings(MEMORY_SCOPE_STRICT_MODE=False)
```

### HIGH #4 — Qdrant Hybrid Tiering

```python
# scope.py
@dataclass(frozen=True)
class ScopeContext:
    org_id: str
    workspace_id: str = "default"
    user_id: str = ""
    agent_id: Optional[str] = None
    tier: Literal["t1", "smb"] = "smb"  # NEW — derived from org_memberships.tier

# mem0_client.py
def _collection_name(scope: ScopeContext) -> str:
    if scope.tier == "t1":
        return f"ipa_memory_{scope.org_id}"  # Dedicated collection
    else:
        return "ipa_memory_shared"  # Shared collection, filtered by payload org_id

# Search path:
filter = {"org_id": scope.org_id, ...}  # Qdrant payload filter enforced
```

### HIGH #5 — ContextVar Propagation

```python
# scope.py — export a ContextVar
from contextvars import ContextVar, copy_context
current_scope: ContextVar[ScopeContext] = ContextVar("current_scope")

# middleware sets it:
async def dispatch(request, call_next):
    scope = await get_scope(request)
    token = current_scope.set(scope)
    try:
        return await call_next(request)
    finally:
        current_scope.reset(token)

# Executor submits preserve context:
async def update_metadata_safe(self, memory_id, count):
    ctx = copy_context()
    def in_executor():
        scope = ctx.run(current_scope.get)  # Access scope inside thread
        # ... uses scope for filter
    await loop.run_in_executor(self._executor, in_executor)

# asyncio.gather preserves contextvars automatically — no extra work
```

### HIGH #6 — Membership Invalidation via Pub/Sub

```python
# On role change:
async def revoke_membership(user_id, org_id):
    await repo.revoke(user_id, org_id)
    await redis.delete(f"membership:{user_id}")  # Cache bust
    await redis.publish("membership_invalidate", user_id)  # Pub/sub for multi-node

# Subscriber (in app lifespan):
async def listen_invalidations():
    async for msg in redis.subscribe("membership_invalidate"):
        local_cache.pop(msg.data, None)
```

### HIGH #7 — Hash with Deployment Salt

```python
# Ensure collision resistance + obscurity:
DEPLOYMENT_SALT = settings.MEMORY_HASH_SALT  # 32-byte random, per-deployment

def as_hashed_key_prefix(scope: ScopeContext) -> str:
    input_bytes = f"{scope.org_id}|{scope.workspace_id}|{scope.user_id}|{DEPLOYMENT_SALT}".encode()
    return hashlib.sha256(input_bytes).hexdigest()[:24]  # 96-bit prefix
```

### HIGH #8 — JWT Attack Matrix

Test file `test_jwt_forgery.py` must include:
- `alg:none` header → reject
- HS256 using RS256 public key as HMAC secret (confusion) → reject
- `kid` header path traversal (`../../etc/passwd`) → reject
- `jku` / `jwk` headers pointing to attacker URL → reject or use allowlist
- Expired `exp` → reject
- Future `nbf` (not before) → reject
- Missing `iss` → reject
- Wrong `iss` → reject
- Replay of valid token for deleted user → rejected via membership check

### HIGH #9-11 — Other items

- **Collection creation distributed lock**: `await redis.set(f"qdrant_create:{org_id}", nonce, nx=True, ex=60)` before CREATE
- **Multi-org tests N≥3**: Test A↔B, B↔C, A↔C transitivity
- **ADR-048 sign-off**: Table with {role, name, signature date} for security-lead, backend-lead, SRE-lead — required before PR merges

---

## ADR-048 Rewrite Spec

The ADR at `docs/02-architecture/adr/ADR-048-tenant-scope-for-memory.md` (from original plan) must be **rewritten** to cover:

1. **Async cache choice**: Redis (cross-process, TTL, pub/sub bust)
2. **JWT claim schema** with `agent_memberships` cap 50 + overflow
3. **Strict mode prod default**: fail-closed + CI enforcement
4. **Qdrant tiering**: T1 dedicated / SMB shared with criteria for tier classification
5. **ContextVar propagation pattern** for asyncio + threads
6. **Tombstone / erasure semantics** (coordinates with Sprint 174 GDPR fix)
7. **Hash deployment salt** storage + rotation
8. **JWT attack matrix** documented negative tests
9. **Sign-off table**: security + backend + SRE leads — block code until signed

ADR approval gate enforced via GitHub PR check label.
