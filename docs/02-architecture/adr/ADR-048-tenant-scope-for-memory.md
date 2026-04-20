# ADR-048: Tenant Scope for Memory System

**Status**: **ACCEPTED v0.2** (all 3 sign-offs received 2026-04-20; Sprint 173 code phase unblocked)
**Date**: 2026-04-20 (v0.1) → 2026-04-20 (v0.2 integration)
**Author(s)**: Chris Lai (draft v0.1), ADR coordinator (v0.2 integration)
**Deciders**: backend-lead, sec-lead, SRE-lead
**Target Sprint**: 173 (tenant scope foundation) — this ADR gates the entire sprint

**v0.1 review outcome**: SRE REJECT (3 BLOCKER) + Security/Backend APPROVE-WITH-COMMENTS (10 HIGH total). Full consolidated findings: [ADR-048-review-feedback-consolidated.md](ADR-048-review-feedback-consolidated.md).
**v0.2 delta**: all 3 BLOCKERS + 10 HIGHs addressed. Open Issues #1-5 closed with explicit resolutions. Two new sections added (§11 Runbooks, §12 Observability).

---

## Sign-Off (required before Sprint 173 code)

| Role | v0.1 Verdict | v0.2 Re-Review | Final Signature |
|------|-------------|----------------|-----------------|
| Backend Lead | APPROVE-WITH-COMMENTS | (same — v0.1 items tracked as S173 plan follow-ups H4/H5/H6) | **✅ 2026-04-20** |
| Security Lead | APPROVE-WITH-COMMENTS | **APPROVE** (all HIGH/MEDIUM/LOW resolved) | **✅ 2026-04-20** |
| SRE Lead | **REJECT** | **APPROVE-WITH-COMMENTS** (3 BLOCKER + 4 HIGH resolved; 5 follow-ups → S174/178) | **✅ 2026-04-20** |
| Compliance (GDPR aspects) | N/A | Coordinated via §6 + Sprint 177a; not required for S173 | _deferred to S177a_ |

**ADR approval gate enforced via GitHub PR check label `adr-048-approved`** — applied 2026-04-20.

### Residual follow-ups (tracked, non-blocking)

Must not delay Sprint 173 code phase; schedule as ops/planning tasks.

| ID | Owner | Track | Description |
|----|-------|-------|-------------|
| S173-FU-1 | Backend | S173 plan | Add §10.1 backfill concurrency spec before first commit |
| S173-FU-2 | Backend | S173 plan | `mypy --strict` AC — fail if any repo method has `Optional[ScopeContext]=None` |
| S173-FU-3 | Backend | S173 plan | Alembic downgrade test fixture with populated scope columns |
| ADR-048a | Backend | Companion ADR | Membership DB schema + refresh_token_families (incl. reuse-detection per Security comment) |
| OPS-S174-01 | SRE | Sprint 174 | Flesh out RB-MEM-01..06 from skeletons to executable procedures |
| OPS-S174-02 | SRE | Sprint 174 | Re-pin §12 alert thresholds against B1 benchmark result |
| OPS-S174-03 | SRE | Sprint 174 | `jti:revoked` Redis availability runbook + circuit-breaker spec (fail-closed for privileged ops) |
| OPS-S174-04 | SRE | Sprint 174 | Load-test scope overhead <5ms P95 under 2× prod traffic |
| OPS-S178-01 | SRE | Sprint 178 | RB-MEM-01 dry-run rehearsal before first T1 SLA signed |
| SEC-POSTFU-01 | Sec | Ongoing | Synthetic cross-tenant probe uses dedicated test-tenant (RB-MEM-06 ongoing check) |

---

## Context

IPA Platform currently isolates memory by `user_id` only. V9 audit + enterprise research (2026-04-17 series) + Sprint 173 team review (2026-04-20) identified multi-level tenant scope as the critical enterprise-readiness gap:

- **Regulatory**: multi-tenant SaaS deployment requires GDPR-compliant isolation per organization
- **Operational**: shared L3 (mem0 + Qdrant) without scope is single-tenant by accident
- **Architectural**: Sprint 174 (bitemporal), Sprint 175-176 (Active Retrieval), Sprint 177a (GDPR) all depend on scope foundation

This ADR defines the tenant scope model, JWT integration, and defense-in-depth enforcement for the memory subsystem. Non-memory tenant concerns (billing, RBAC for non-memory resources) are out of scope. Membership DB schema is split into companion **ADR-048a** (not blocking S173 per backend-lead comment).

---

## Decision Summary

Adopt a **4-level scope hierarchy** (`org_id / workspace_id / user_id / agent_id`) propagated from JWT claims via FastAPI middleware into a frozen `ScopeContext` dataclass, enforced at three layers (middleware / repository / storage). Redis caches use hashed prefixes with deployment salt. Qdrant storage uses a **hybrid tiering model** with empirically-validated thresholds: dedicated collections for T1 orgs, shared collection with payload filter for SMB orgs.

---

## Decision Details

### 1. Async Cache Choice (v0.1 §1 — unchanged)

**Decision**: Use **Redis** for `user_memberships` cache (NOT `@lru_cache` which breaks on async coroutines).

**Rationale**:
- `@lru_cache` on async functions caches the coroutine object, not the resolved value → awaiting twice raises `RuntimeError`
- `async-lru` library works but is per-process (multi-node deploys get inconsistent cache)
- Redis cache is cross-process, supports pub/sub invalidation, observable via existing Redis metrics

**Config**:
- TTL: 300 seconds (5 minutes) — *see §2 for sensitive-op forced revalidation*
- Invalidation: pub/sub on role change (`membership_invalidate` channel)
- Key pattern: `membership:{user_id_hash}` (hashed to avoid tenant enumeration)

### 2. JWT Claim Schema + Validation (v0.2 adds H2/H3 fixes)

**Decision**: Bounded claim schema, short exp, jti deny-list, KMS-registered key lookup before alg inspection.

**Schema**:
```json
{
  "iss": "ipa-platform",
  "sub": "user_xyz",
  "exp": 1745712000,
  "iat": 1745708400,
  "nbf": 1745708400,
  "jti": "tok_7f1a3d...",
  "org_id": "org_abc",
  "workspace_id": "wsp_1",
  "agent_memberships": ["agent_A", "agent_B", "..."],
  "has_more_memberships": false,
  "tier": "t1"
}
```

**Bounds (unchanged from v0.1)**:
- `agent_memberships` capped at **50 entries**; overflow → `has_more_memberships: true` + DB lookup on demand
- Claim total JSON size ≤ 8KB (FastAPI default header limit alignment)

**v0.2 HIGH H2 — Short exp + jti deny-list**:
- Access token `exp`: **≤ 15 minutes** (tight revocation window under multi-DC replication lag)
- Refresh token rotation: separate flow, tracked via `refresh_token_families` DB table (schema in ADR-048a)
- `jti` deny-list: Redis SET `jwt:revoked:{jti}` with TTL = token's remaining lifetime; checked on every request
- For privileged operations (admin role changes, GDPR delete), bypass membership cache and re-query DB

**v0.2 HIGH H3 — Key lookup precedes alg inspection**:
```
Validation order (each step fails closed):
  1. Parse header → extract `kid`
  2. Lookup `kid` in KMS-backed registry → returns public key metadata
     - Registry MUST only contain RSA public keys (reject HS/symmetric on registration)
     - kid allowlist enforced here; path traversal / wildcards rejected
  3. From registry entry, assert `alg ∈ ["RS256"]`
  4. Ignore any `alg` in JWT header that contradicts registry
  5. PyJWT verify with `algorithms=["RS256"]` explicit
  6. exp / nbf / iss / jti-not-revoked checks
  7. `org_id ∉ {default, *, "", null}` (H1 — reserved sentinels)
  8. `user_memberships` DB cross-check via cache
```

**Signing**: RS256 with key rotation every **90 days**, overlap window ≤**7 days**. Keys stored in KMS (AWS KMS / Azure Key Vault) — closes Open Issue #3. JWK endpoint for public key distribution. See **Runbook RB-MEM-03** for rotation procedure.

### 3. Strict Mode Prod Default (v0.1 §3 — unchanged text; v0.2 adds prod smoke test)

**Decision**: `MEMORY_SCOPE_STRICT_MODE=True` enforced in production via startup validator + production smoke test.

**Enforcement** (validator unchanged):
```python
@validator("MEMORY_SCOPE_STRICT_MODE")
def enforce_prod_strict(cls, v, values):
    if os.getenv("IPA_ENV") == "production" and not v:
        raise ValueError("MEMORY_SCOPE_STRICT_MODE must be True in production")
    return v
```

**v0.2 M7**: S173 adds production smoke test asserting strict mode active at runtime on deployed instances.

### 4. Qdrant Tiering Model (v0.2 addresses B1 + B3)

**Decision**: Hybrid tiering with empirically-validated thresholds.

| Org Tier | Collection Strategy | Criteria |
|----------|---------------------|----------|
| **T1 (dedicated)** | `ipa_memory_{org_id}` | Enterprise with compliance/isolation SLA |
| **SMB (shared)** | `ipa_memory_shared`, payload filter on `org_id` | Default; lower isolation overhead |

**Tier default**: new orgs → `smb` (closes Open Issue #1). Manual tier-upgrade flow deferred to Sprint 178+.

**v0.2 BLOCKER B1 — Threshold empirical basis**:
- The "~500 orgs" guidance is **estimated based on Qdrant metadata overhead extrapolation**, not production measurement.
- S173 MUST include a perf test (`scripts/benchmark_qdrant_tiering.py`) that measures Qdrant RAM + metadata startup time at 100 / 500 / 1000 dedicated collections.
- Result becomes authoritative guidance + alerting thresholds in §12.

**v0.2 BLOCKER B3 — Redis SPOF degraded-mode**:
- Collection creation uses Redis `SET NX` lock. If Redis unavailable:
  - New-org signup returns **HTTP 202 Accepted** with job token (not blocking)
  - Creation request queued to PostgreSQL `org_collection_pending` table
  - Background worker retries every 30s when Redis recovers
  - Customer-facing: workspace shows "provisioning" state up to 5 min
- Runbook reference: **RB-MEM-02** (Redis outage during new-org signup)

**v0.2 BLOCKER B2 — SMB→T1 live migration runbook**:
- Full procedure in **RB-MEM-01** (§11)
- Core: dual-write to both collections for 1 hour → verify row-count parity → flip reads to T1 → 24h soak → delete SMB shard
- NOT a Sprint 173 deliverable (migration flow in Sprint 178+); BUT runbook skeleton committed here so ops has a procedure if a T1 SLA is signed before then.

**Migration — legacy data**: → `ipa_memory_default` collection (treated as SMB-tier). See §10.2 for sentinel restrictions.

### 5. ContextVar Propagation (v0.2 adds M1 BackgroundTasks note)

**Decision**: Python `contextvars.ContextVar[ScopeContext]` for scope across async boundaries.

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

# FastAPI BackgroundTasks — run after response, may lose context:
ctx = copy_context()
background_tasks.add_task(ctx.run, bg_work_fn, *args)
```

**Verification**: AC in Sprint 173 asserts scope preserved through `asyncio.gather` + `run_in_executor` + `BackgroundTasks`.

### 6. Tombstone / Erasure Semantics (v0.1 §6 — unchanged)

Coordinates with Sprints 174 + 177a. See v0.1 text.

### 7. Hash Deployment Salt + Rotation Procedure (v0.2 adds H9)

**Decision**: SHA-256 with deployment-level salt; rotation procedure documented.

**Config**:
- `MEMORY_HASH_SALT: str` — 32-byte random, one per deployment, stored in secret manager
- Key derivation: `SHA-256(org_id || "|" || workspace_id || "|" || user_id || "|" || SALT)[:24]` → 96-bit prefix
- Collision math: at 2^48 unique tenants the expected collision probability is < 10^-4 (acceptable)

**v0.2 H9 — Rotation procedure**: see **Runbook RB-MEM-04** for salt compromise response. Compromise = breach incident; procedure covers re-key window, data re-encryption sequence, downtime budget, cutover steps.

**Normal operations**: salt does not rotate (would require re-keying all hashed keys). Rotation happens only on compromise or every 5 years (whichever first).

### 8. JWT Attack Matrix (v0.2 adds row 13 timing side-channel + schema-level body rejection)

| # | Attack | Rejection Mechanism |
|---|--------|---------------------|
| 1 | `alg:none` | PyJWT explicit `algorithms=["RS256"]` |
| 2 | HS/RS confusion | Key registry returns RSA-only; kid→key lookup precedes alg validation (§2) |
| 3 | `kid` path traversal | Allowlist validation against KMS registry |
| 4 | `jku`/`jwk` header pointing to attacker URL | Server-side key registry only; headers ignored |
| 5 | Expired `exp` | PyJWT default |
| 6 | Future `nbf` | PyJWT default |
| 7 | Missing/wrong `iss` | Explicit checks against `ISSUER` config |
| 8 | Revoked token replay | `jti` deny-list (§2 H2) |
| 9 | Replay of valid token for deleted user | `user_memberships` cross-check + pub/sub invalidation |
| 10 | `agent_memberships` cap exceeded | Bounds validator in middleware; fail-closed on overflow |
| 11 | Missing `org_id` | Explicit check |
| 12 | Body-injected scope override | Middleware uses JWT only. **Schema-level (L1)**: Pydantic request models for memory APIs MUST NOT declare `org_id`/`workspace_id` fields |
| **13** | **Timing side-channel on cache-hit vs cache-miss** | **Constant-time auth failure path: fixed 50ms min-delay + randomized jitter ±10ms on 401/403 responses** |

S173 `test_jwt_forgery.py` covers all 13 attacks; each asserts 401 or 403 with specific error message.

### 9. Defense-In-Depth Summary (v0.2 H5 adds mypy-strict enforcement)

| Layer | Enforcement |
|-------|-------------|
| **Middleware** | JWT validation + ScopeContext attachment to `request.state.scope` |
| **Repository** | All memory repo methods take `scope: ScopeContext` typed parameter (no default). **S173 AC**: `mypy --strict` fails if any repo method has `Optional[ScopeContext] = None` — enforced in CI |
| **Storage (Qdrant)** | Collection-per-org OR payload filter; scope filter applied by `UnifiedMemoryManager` NOT by LLM output |
| **Storage (PG)** | SQL `WHERE org_id = :scope.org_id AND workspace_id = :scope.workspace_id ...` in all queries |
| **Storage (Redis)** | Hashed key prefixes (SHA-256[:24] + salt) prevent enumeration via `SCAN` |

### 10. Non-Destructive Rollout (v0.2 adds §10.1 + §10.2)

**Decision**: Legacy entries auto-assigned `org_id="default"`, `workspace_id="default"` by backfill — with additional safeguards.

#### §10.1 (v0.2 H4) — Backfill concurrency spec

Backfill script `scripts/backfill_scope_columns_s173.py` must:
- Process in batches of **1000 rows** with explicit `FOR UPDATE SKIP LOCKED` so concurrent Sprint 172 session writes don't block
- Update `org_id` / `workspace_id` → `"default"` only if currently NULL (idempotent)
- Co-ordinate with live writes: a trigger temporarily rejects INSERT without scope during backfill window (opt-in via `backfill_in_progress` flag)
- `--dry-run` mode prints count and sample
- Alembic migration applies trigger removal as final step

#### §10.2 (v0.2 H1) — Reserved sentinel enforcement

Middleware MUST **reject** incoming JWTs with `org_id ∈ {"default", "*", "", null}`:
- Returns HTTP 403 with error `scope.reserved_sentinel`
- Prevents confused-deputy attack against legacy `default` data
- Legacy `default`-assigned rows accessible only via admin-role migration tooling (requires ops role + audit log)

#### §10.3 — Grace mode

`MEMORY_SCOPE_STRICT_MODE=False` in dev allows scope-less callers (routed to default). **Disabled in prod via startup validator (§3).**

**Migration scripts**: idempotent, dry-run mode, runs as dedicated `ipa_migrator` role with least-privilege grants (matches Sprint 172 pattern).

### 11. Runbooks (v0.2 NEW — closes SRE concerns)

| Runbook | Purpose | Owner | Severity |
|---------|---------|-------|----------|
| **RB-MEM-01** | SMB → T1 live migration | SRE | HIGH (first enterprise SLA trigger) |
| **RB-MEM-02** | Redis outage during new-org signup | SRE | HIGH |
| **RB-MEM-03** | JWT key rotation (key N/N+1 overlap) | SRE + Sec | MEDIUM (routine 90-day) |
| **RB-MEM-04** | Salt compromise response | SRE + Sec | CRITICAL (incident) |
| **RB-MEM-05** | Cross-DC pub/sub partition | SRE | HIGH (multi-region only) |
| **RB-MEM-06** | Legacy `default` org segregation | Ops + Sec | MEDIUM |

Skeleton entries stored at `docs/04-operations/runbooks/RB-MEM-0{1..6}.md` (committed in this ADR PR as `.skeleton.md` stubs; full procedures in a follow-up ops PR).

**RB-MEM-01 skeleton summary**: dual-write 1h → verify row-count parity → cutover reads → 24h soak → delete SMB shard. Rollback: flip reads back; dual-write remains until resolved.

**RB-MEM-02 skeleton summary**: 202 Accepted response → queue to `org_collection_pending` → retry worker → notify customer on completion.

**RB-MEM-03 skeleton summary**: overlap window 7d → publish N+1 via JWK endpoint → switch signing to N+1 → monitor validation failure rate → delete N. Rollback: revert signer config.

**RB-MEM-04 skeleton summary**: declare incident → generate new salt → dual-read old/new hash → re-encrypt all Redis keys → switch readers → purge old salt.

**RB-MEM-05 skeleton summary**: force revalidation against PG for admin ops during partition → alert ops → auto-resume when pub/sub lag returns < 60s.

**RB-MEM-06 skeleton summary**: identify `default`-tagged rows → migrate to owning org if identifiable → quarantine remainder → approval workflow for deletion.

### 12. Observability (v0.2 NEW — closes SRE H10 + ops concerns)

Required metrics and alerts before production rollout:

| Metric | Type | Alert Threshold | Purpose |
|--------|------|-----------------|---------|
| `memory_scope_mismatch_total{layer}` | Counter | **>0 in 5min** — PAGE | Cross-tenant leak detection |
| `qdrant_t1_collection_count` | Gauge | >70% of benchmark ceiling (B1) | T1 capacity planning |
| `qdrant_metadata_ram_bytes` | Gauge | >70% of Qdrant node RAM | T1 scaling trigger |
| `jwt_validation_failure_total{reason}` | Counter | rate spike >3 stddev — WARN | Attack detection |
| `membership_cache_pubsub_lag_seconds` | Histogram | P99 > 60s — PAGE | Cross-DC divergence |
| `membership_cache_hit_ratio` | Gauge | drop > 20pp sudden — WARN | Redis degradation |
| `memory_scope_overhead_ms{layer}` | Histogram | P95 > 10ms — WARN | Performance regression |

Additional **synthetic probe**: cross-tenant read attempt every 60s — page on any success.

---

## Consequences

**Positive** (unchanged from v0.1):
- Enterprise isolation: compliant with GDPR / SOC 2 / ISO 27001 tenant separation
- Scope propagation pattern reusable beyond memory (future knowledge, tools, audit)
- Tier flexibility accommodates compliance-sensitive + SMB customers
- Clear separation of erased vs superseded supports audit + right-to-erasure

**Negative / Costs**:
- Every memory API call adds scope overhead (hash + filter + cache lookup) — target < 5ms P95, alert at >10ms
- T1 tier dedicated collections consume Qdrant metadata RAM — ops monitoring per §12
- JWT key rotation operational complexity (RB-MEM-03 + 7-day overlap window)
- Short JWT `exp` (≤15min) increases auth traffic — refresh token flow must be efficient
- Timing-jitter response adds latency on auth failures

**Risks**:
- **Legacy data migration**: mitigated by dry-run + spot-check + §10.1 batched approach + RB-MEM-06
- **Tier transition**: RB-MEM-01 provides procedure; first enterprise upgrade surfaces real issues
- **Cross-DC latency**: Open Issue #4 closed via forced revalidation for sensitive ops (§2); single-region recommended for v1

---

## Open Issues — Resolutions (v0.2 closure)

| # | Original issue | v0.2 resolution |
|---|---------------|-----------------|
| 1 | Tier classification ownership | Pin default=`smb`; tier-upgrade flow deferred to Sprint 178+. Self-service upgrade requires billing + capacity approval workflow |
| 2 | Salt rotation on compromise | RB-MEM-04 covers procedure; salt stored in KMS secret manager; rotation = declared incident |
| 3 | JWT key registry format | **Azure Key Vault / AWS KMS** (matches existing project pattern); JWK endpoint fetches from KMS with 5min cache |
| 4 | Cross-DC pub/sub latency | Forced revalidation for admin role changes + GDPR ops (bypasses cache); single-region v1; multi-region requires re-ADR |
| 5 | Membership DB schema | **Split into companion ADR-048a** (does not block S173); S173 proceeds with scope columns + membership cross-check via JWT claim |

---

## Negative Test Matrix (for Sprint 173 `test_jwt_forgery.py`)

Minimum **13 test cases** (see §8); each asserts 401 or 403 with specific error message.

---

## Alternatives Considered (unchanged from v0.1)

### Alt 1: Collection-per-org only (no tier)
Rejected: doesn't scale past validated threshold; Qdrant RAM pressure.

### Alt 2: Shared collection + payload filter only (no tier)
Rejected: no physical isolation for compliance-sensitive tenants (T1 requirement).

### Alt 3: Separate Qdrant instance per tenant
Rejected: operational overhead of 100s-1000s instances; cost.

### Alt 4: `async-lru` for membership cache
Rejected: per-process cache incompatible with multi-node deployment.

### Alt 5: Include scope in request body
Rejected: trust boundary violation. JWT-only + schema-level rejection (row 12).

---

## Coordination with Other Decisions

- **Sprint 174 (Bitemporal)**: `search_as_of()` MUST filter against `forgotten_users` tombstone (§6; implemented in Sprint 177a)
- **Sprint 175-176 (Active Retrieval)**: LLM-generated topics MUST NOT influence scope; scope filter always from `ScopeContext` not LLM output
- **Sprint 177a (GDPR)**: `forget_user` writes tombstone + HMAC audit chain; depends on this ADR's scope model
- **Sprint 178+ (tier upgrade ops)**: RB-MEM-01 provides runbook; operational upgrade flow not a sprint deliverable

---

## Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1-draft | 2026-04-20 | Initial skeleton from Sprint 173 v2 Implementation Notes | Chris Lai |
| **0.2** | **2026-04-20** | Integrated 2026-04-20 review findings: 3 BLOCKER (B1 benchmark AC, B2 RB-MEM-01, B3 RB-MEM-02) + 10 HIGH (H1 sentinel, H2 short-exp+jti, H3 key-before-alg, H4 backfill concurrency, H5 mypy-strict, H6 rollback fixture, H7 forced revalidation, H8 JWT overlap, H9 RB-MEM-04, H10 observability). Added §11 Runbooks + §12 Observability. Closed Open Issues #1-5. Attack matrix row 13 (timing side-channel). v0.1 findings preserved in `ADR-048-review-feedback-consolidated.md`. | ADR coordinator |
