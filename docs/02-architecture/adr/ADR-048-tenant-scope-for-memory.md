# ADR-048: Tenant Scope for Memory System

**Status**: DRAFT (skeleton — requires fleshing out + sign-off before Sprint 173 code phase)
**Date**: 2026-04-20
**Author(s)**: Chris Lai (draft)
**Deciders**: backend-lead, sec-lead, SRE-lead
**Target Sprint**: 173 (tenant scope foundation) — this ADR gates the entire sprint

---

## Sign-Off (required before Sprint 173 code)

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Backend Lead | _TBD_ | _pending_ | _pending_ |
| Security Lead | _TBD_ | _pending_ | _pending_ |
| SRE Lead | _TBD_ | _pending_ | _pending_ |
| Compliance (optional for GDPR aspects) | _TBD_ | _pending_ | _pending_ |

**ADR approval gate enforced via GitHub PR check label `adr-048-approved`.**

---

## Context

IPA Platform currently isolates memory by `user_id` only. V9 audit + enterprise research (2026-04-17 series) + Sprint 173 team review (2026-04-20) identified multi-level tenant scope as the critical enterprise-readiness gap:

- **Regulatory**: multi-tenant SaaS deployment requires GDPR-compliant isolation per organization
- **Operational**: shared L3 (mem0 + Qdrant) without scope is single-tenant by accident
- **Architectural**: Sprint 174 (bitemporal), Sprint 175-176 (Active Retrieval), Sprint 177a (GDPR) all depend on scope foundation

This ADR defines the tenant scope model, JWT integration, and defense-in-depth enforcement for the memory subsystem. Non-memory tenant concerns (billing, RBAC for non-memory resources) are out of scope.

---

## Decision Summary

Adopt a **4-level scope hierarchy** (`org_id / workspace_id / user_id / agent_id`) propagated from JWT claims via FastAPI middleware into a frozen `ScopeContext` dataclass, enforced at three layers (middleware / repository / storage). Redis caches use hashed prefixes with deployment salt. Qdrant storage uses a **hybrid tiering model**: dedicated collections for T1 orgs, shared collection with payload filter for SMB orgs.

---

## Decision Details

### 1. Async Cache Choice (CRITICAL from Batch 2 review)

**Decision**: Use **Redis** for `user_memberships` cache (NOT `@lru_cache` which breaks on async coroutines).

**Rationale**:
- `@lru_cache` on async functions caches the coroutine object, not the resolved value → awaiting twice raises `RuntimeError`
- `async-lru` library works but is per-process (multi-node deploys get inconsistent cache)
- Redis cache is cross-process, supports pub/sub invalidation, observable via existing Redis metrics

**Config**:
- TTL: 300 seconds (5 minutes)
- Invalidation: pub/sub on role change (`membership_invalidate` channel)
- Key pattern: `membership:{user_id_hash}` (hashed to avoid tenant enumeration)

**Alternative considered**: `async-lru`. Rejected due to multi-node inconsistency.

### 2. JWT Claim Schema

**Decision**: Define bounded claim schema with overflow fallback.

**Schema**:
```json
{
  "iss": "ipa-platform",
  "sub": "user_xyz",
  "exp": 1745712000,
  "iat": 1745708400,
  "org_id": "org_abc",
  "workspace_id": "wsp_1",
  "agent_memberships": ["agent_A", "agent_B", "..."],
  "has_more_memberships": false,
  "tier": "t1"
}
```

**Bounds**:
- `agent_memberships` capped at **50 entries**; overflow → `has_more_memberships: true` + DB lookup on demand
- Without bounds: token DoS possible via oversized claims (CRITICAL #2 from Batch 2)
- Claim total JSON size ≤ 8KB (FastAPI default header limit alignment)

**Signing**: RS256 with key rotation every **90 days**. Keys stored in KMS (AWS KMS / Azure Key Vault). JWK endpoint for public key distribution with allowlist validation.

**Validation layers**:
1. Signature verification (PyJWT with `algorithms=["RS256"]` explicit, prevents `alg:none` + HS/RS confusion)
2. `exp` / `nbf` / `iss` / `kid` checks (kid must be in allowlist, no path traversal)
3. `org_id` non-empty (rejects tokens with missing scope)
4. `user_memberships` DB cross-check (rejects valid JWT for deleted user)

### 3. Strict Mode Prod Default (CRITICAL from Batch 2)

**Decision**: `MEMORY_SCOPE_STRICT_MODE=True` is enforced in production via startup validator.

**Enforcement**:
```python
@validator("MEMORY_SCOPE_STRICT_MODE")
def enforce_prod_strict(cls, v, values):
    if os.getenv("IPA_ENV") == "production" and not v:
        raise ValueError("MEMORY_SCOPE_STRICT_MODE must be True in production")
    return v
```

**CI check**: `pytest tests/config/test_prod_strict_enforced.py` asserts the raise.

**Dev override**: `IPA_ENV=development` allows `False` for legacy-data grace mode.

### 4. Qdrant Tiering Model (HIGH from Batch 2)

**Decision**: Hybrid tiering.

| Org Tier | Collection Strategy | Criteria |
|----------|---------------------|----------|
| **T1 (dedicated)** | `ipa_memory_{org_id}` | Enterprise customers with compliance/isolation SLA |
| **SMB (shared)** | `ipa_memory_shared`, filtered by payload `org_id` | Default for new orgs; lower isolation overhead |

**Tier classification**: stored in `org_memberships.tier` (PG), propagated into `ScopeContext.tier: Literal["t1", "smb"]`

**Rationale**: Pure collection-per-org doesn't scale past ~500 orgs (Qdrant metadata RAM pressure). Shared collection with payload filter scales but lacks physical isolation for compliance-sensitive tenants.

**Collection creation**: distributed lock via Redis `SET NX` to prevent concurrent create race.

**Migration**: legacy data → `ipa_memory_default` (treated as SMB-tier "default" org).

### 5. ContextVar Propagation (HIGH from Batch 2)

**Decision**: Use Python `contextvars.ContextVar[ScopeContext]` for scope propagation across async boundaries.

**Pattern**:
```python
current_scope: ContextVar[ScopeContext] = ContextVar("current_scope")

# Middleware sets:
token = current_scope.set(scope)
try:
    return await call_next(request)
finally:
    current_scope.reset(token)

# asyncio.gather preserves contextvars automatically.
# ThreadPoolExecutor needs explicit copy_context:
ctx = copy_context()
await loop.run_in_executor(executor, lambda: ctx.run(work_fn))
```

**Why not thread-local**: asyncio tasks share threads; thread-local leaks across requests.

**Verification**: AC in Sprint 173 asserts scope preserved through `asyncio.gather` + executor fan-out.

### 6. Tombstone / Erasure Semantics (coordinates with Sprints 174 + 177a)

**Decision**: Introduce `forgotten_users` tombstone table (created by Sprint 177a) consumed by Sprint 174 bitemporal `search_as_of()`.

**Rationale**: GDPR Article 17 "right to erasure" must apply to historical views. Sprint 174's `as_of` query without tombstone filter leaks erased data.

**Distinction**:
- **Superseded** (keep historical for audit): new version created, old remains queryable via `as_of` < supersede point
- **Erased** (hard-delete from ALL views): tombstone entry filters from all queries including `as_of`

**Schema reference**: see Sprint 177a plan §1.

### 7. Hash Deployment Salt (HIGH from Batch 2)

**Decision**: SHA-256 with deployment-level salt.

**Rationale**: 64-bit hash prefix (as originally planned) has birthday collision probability ~1 in 2^32 — acceptable for small deployments, risky at scale. Adding deployment salt also prevents rainbow table attacks and cross-environment hash reuse.

**Config**:
- `MEMORY_HASH_SALT: str` — 32-byte random, one per deployment, stored in secret manager
- Key derivation: `SHA-256(org_id || "|" || workspace_id || "|" || user_id || "|" || SALT)[:24]` → 96-bit prefix

**Rotation**: salt does not rotate frequently (would require re-keying all data); treat as deployment-scoped constant. Re-key only on compromise.

### 8. JWT Attack Matrix (documented negative tests)

Sprint 173 test `test_jwt_forgery.py` must cover all of:

| Attack | Rejection Mechanism |
|--------|---------------------|
| `alg:none` | PyJWT explicit `algorithms=["RS256"]` |
| HS256 signing with RS256 public key (HS/RS confusion) | Same — reject non-RS256 algs |
| `kid` path traversal (e.g., `../../../etc/passwd`) | Allowlist of valid kid values |
| `jku` / `jwk` header pointing to attacker URL | Ignore these headers; use server-side key registry |
| Expired `exp` | PyJWT default |
| Future `nbf` (not before) | PyJWT default |
| Missing `iss` | Explicit check |
| Wrong `iss` | Explicit check against `ISSUER` config |
| Replay of valid token for deleted user | `user_memberships` cross-check (5min cache + pub/sub invalidation) |
| Claim `agent_memberships` exceeding cap 50 | Bounds validator in middleware |
| Missing `org_id` | Explicit check |
| Body-injected scope override | Middleware uses JWT only; request body scope ignored |

### 9. Defense-In-Depth Summary

| Layer | Enforcement |
|-------|-------------|
| **Middleware** | JWT validation + ScopeContext attachment to `request.state.scope` |
| **Repository** | All memory repo methods take `scope: ScopeContext` typed parameter (no string scope) |
| **Storage (Qdrant)** | Collection-per-org OR payload filter; scope filter applied by `UnifiedMemoryManager` NOT by LLM output |
| **Storage (PG)** | SQL `WHERE org_id = :scope.org_id AND workspace_id = :scope.workspace_id ...` in all queries |
| **Storage (Redis)** | Hashed key prefixes prevent enumeration via `SCAN` |

No single-point-of-failure: if middleware bypassed (unlikely — internal caller forgets), repository requires `ScopeContext` → code doesn't compile without passing one → storage enforces filter.

### 10. Non-Destructive Rollout (legacy data)

**Decision**: Legacy entries (without scope fields) auto-assigned `org_id="default"`, `workspace_id="default"` by backfill.

**Grace mode**: `MEMORY_SCOPE_STRICT_MODE=False` in dev allows scope-less callers (routed to default). **Disabled in prod.**

**Migration scripts**: idempotent, dry-run mode, runs as dedicated `ipa_migrator` role with least-privilege grants.

---

## Consequences

**Positive**:
- Enterprise isolation: compliant with GDPR / SOC 2 / ISO 27001 tenant separation
- Scope propagation pattern reusable beyond memory (future knowledge, tools, audit)
- Tier flexibility accommodates both compliance-sensitive + SMB customers
- Clear separation of erased vs superseded supports both audit and right-to-erasure

**Negative / Costs**:
- Every memory API call adds scope-related overhead (hash + filter + cache lookup) — measurable, expected < 5ms
- T1 tier dedicated collections consume Qdrant metadata RAM — ops monitoring required
- JWT key rotation introduces operational complexity (90-day cadence + rollout coordination)
- Membership cache TTL creates 5-minute revocation window (mitigated by pub/sub invalidation but cross-datacenter lag may exceed)

**Risks**:
- **Legacy data migration complexity**: backfill scripts must handle mixed org/workspace assignment — risk of misattribution. Mitigation: dry-run + spot-check + rollback plan.
- **Tier transition**: moving an SMB org to T1 (dedicated collection) requires data migration. Mitigation: Sprint 178+ or ops procedure, out of Sprint 173 scope.

---

## Negative Test Matrix (for Sprint 173 `test_jwt_forgery.py`)

Minimum 12 test cases (see section 8); each asserts 401 or 403 with specific error message.

---

## Alternatives Considered

### Alt 1: Collection-per-org only (no tier)
Rejected: doesn't scale past ~500 orgs; Qdrant RAM pressure; slow startup as metadata grows.

### Alt 2: Shared collection + payload filter only (no tier)
Rejected: no physical isolation for compliance-sensitive tenants (T1 enterprise customers explicit requirement).

### Alt 3: Separate Qdrant instance per tenant
Rejected: operational overhead (100s-1000s of Qdrant instances to manage); cost; high-enterprise-only solution.

### Alt 4: `async-lru` for membership cache
Rejected: per-process cache incompatible with multi-node deployment (stale roles after revocation on some nodes).

### Alt 5: Include scope in request body
Rejected: trust boundary violation; enables forgery. JWT-only is the safe path.

---

## Coordination with Other Decisions

- **Sprint 174 (Bitemporal)**: `search_as_of()` MUST filter against `forgotten_users` tombstone (established here, implemented in Sprint 177a)
- **Sprint 175-176 (Active Retrieval)**: LLM-generated topics MUST NOT influence scope; scope filter is always from `ScopeContext` not LLM output
- **Sprint 177a (GDPR)**: `forget_user` writes tombstone + HMAC audit chain; depends on this ADR's scope model

---

## Open Issues (must resolve before sign-off)

1. **Tier classification ownership**: who decides org tier? Sales ops? Self-service + audit?
2. **Salt rotation on compromise**: documented rollout procedure missing
3. **JWT key registry format**: JSON file vs dedicated service (Vault, KMS)?
4. **Cross-datacenter pub/sub latency**: if multi-region, membership revocation window may exceed 5min
5. **Membership DB schema**: not detailed here — needs separate data-model ADR or spec

---

## Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1-draft | 2026-04-20 | Initial skeleton from Sprint 173 v2 Implementation Notes | Chris Lai |
| _pending_ | _TBD_ | Fleshed out after sign-off discussion | _pending_ |
