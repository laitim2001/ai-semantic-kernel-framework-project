# Sprint 57.59 — Plan

**Phase**: 57+ Frontend SaaS / Phase 58.x Portfolio Deeper Extensions
**Sprint**: 57.59 (post-57.58 RateLimits RuntimeEnforcement)
**Branch**: `feature/sprint-57-59-rate-limits-potemkin-migration`
**Class**: `mixed-multidomain-bundle` 0.65 (tier-2; DB schema + service + 4 re-points + frontend)
**Agent-delegated**: yes (≥80% Day 1 via code-implementer; sequential)
**Agent-factor**: `mixed-multidomain-bundle-mechanical` 0.65 (tier-3 **2nd validation** — Sprint 57.58 1st = ~0.49 BELOW band)
**Plan version**: v1 — drafted 2026-05-28 Day 0 (pre-三-Prong)
**Template**: mirrors `sprint-57-58-plan.md` 9-section structure

---

## 1. Sprint Goal

Close the **AP-4 Potemkin Feature** surfaced in Sprint 57.58 (`AD-RateLimits-Potemkin-Migration-Phase58`) by **activating the dormant `rate_limits` schema via a two-table split** (Option C1, user-locked 2026-05-28):

- **NEW `rate_limit_configs` table** = durable per-(tenant, resource_type, window_type) quota config — replaces `tenant.meta_data["rate_limits"]` JSONB as the source of truth
- **Repurpose existing `rate_limits` table** = per-(tenant, resource_type, window_type, window_start) live usage instances (was Potemkin since Phase 49; now actually wired)
- **Data migration**: existing `meta_data["rate_limits"]` `{label, value}` rows → `rate_limit_configs` rows (via Sprint 57.58 `parse_rate_limit_item()`)
- **Re-point all RateLimits read/write paths** (Sprint 57.48 GET + 57.57 PUT + 57.58 usage GET + 57.58 middleware) from JSONB to the tables
- Redis stays the hot-path counter (Sprint 57.58); the `rate_limits` usage table becomes its durable backing

After this sprint: 0 AP-4 Potemkin tables in the RateLimits subsystem; config + usage both DB-backed + RLS-enforced; JSONB path deprecated (kept as transitional read-fallback, cleared in follow-up).

---

## 2. Background & Context

### 2.1 What Sprint 57.58 left (verified Sprint 57.58 Day 0 + this sprint Day 0 Prong)

- ✅ Runtime enforcement: `RateLimitMiddleware` (Cat 12) + Cat 2 tool gate + Redis sliding-window counter — all read config from `tenant.meta_data["rate_limits"]`
- ✅ Live usage: `GET /admin/tenants/{tid}/rate-limits/usage` (Redis peek) + frontend Live usage Card
- ✅ WRITE: `PUT /admin/tenants/{tid}/rate-limits` writes `{label, value}` items to `meta_data` JSONB (Sprint 57.57)
- ✅ READ: `GET /admin/tenants/{tid}/rate-limits` reads `meta_data` JSONB (Sprint 57.48)
- ❌ **`rate_limits` ORM table** (`api_keys.py:141`, migration `0006_api_keys_rate_limits.py` + RLS `0009_rls_policies.py`) — defined + applied to DB since Phase 49 but NEVER queried/written = AP-4 Potemkin

### 2.2 The two-table split (Option C1)

| Concern | Storage (after this sprint) | Was (before) |
|---------|----------------------------|--------------|
| **Config** (quota per resource+window_type) | NEW `rate_limit_configs` table (`tenant_id, resource_type, window_type, quota`) | `tenant.meta_data["rate_limits"]` JSONB `{label, value}` |
| **Live usage** (used per resource+window_type+window_start) | existing `rate_limits` table (`tenant_id, resource_type, window_type, window_start, used` + denormalized `quota` snapshot) | Redis only (ephemeral) |
| **Hot-path counter** | Redis sliding window (unchanged) + durable backing in `rate_limits` table | Redis only |

**Why two tables**: the existing `rate_limits` table forces `window_start NOT NULL` in its unique key — every row is a live window instance, so config (window-instance-agnostic) cannot live there. Splitting config into its own table is the clean normalization (Sprint 57.59 Day 0 schema-tension analysis; user-locked C1 over C2 nullable-window_start single-table).

### 2.3 Why `mixed-multidomain-bundle-mechanical` 0.65 (tier-3 2nd validation)

Multi-track with mechanical pattern reuse:

| Track | Pattern source | Mechanical reuse |
|-------|---------------|-----------------|
| DB migration + ORM | Alembic migration precedent (0006/0009 RLS) + `RateLimit` ORM exists | High — mirror existing table + RLS pattern |
| Config store service | Sprint 57.56 `_PLAN_QUOTA_RESOURCE_WHITELIST` + projection helpers | High |
| 4 endpoint re-points | Sprint 57.48/57.57/57.58 endpoints exist (swap data source) | High — surgical source swap |
| `parse_rate_limit_item()` reuse | Sprint 57.58 normalizer | Verbatim reuse |
| Frontend | UI unchanged; types/service re-point | High |

Genuine NEW design (config table schema + data migration + deprecation path) tempers the "mechanical" rating, but the dominant work is pattern-reuse re-pointing → `mixed-multidomain-bundle-mechanical` 0.65. Sprint 57.58 was the 1st validation (~0.49 BELOW band, single-data-point caution KEEP); this is the **2nd validation** (if also < 0.7 → tighten 0.45; if > 1.20 → rollback 1.0).

### 2.4 Sprint 57.58 carryover chain

- `AD-RateLimits-Potemkin-Migration-Phase58` (this sprint's primary)
- `AD-AgentFactor-Tier-3-MixedBundle-Mechanical-Validation-Sprint-57.59` (2nd validation of agent_factor sub-class)
- `AD-Day0-Prong2-Nested-Shape-Read` (Q3 lesson; codify if 2-3 data points)
- folds in CONDITIONAL `AD-RateLimits-DedicatedTable-Phase58` (same table — closed by this sprint)

### 2.5 Class baseline tracking

- `mixed-multidomain-bundle` 0.65 SCOPE 3rd data point (57.46=0.73 / 57.58=0.32 / 57.59=?)
- `mixed-multidomain-bundle-mechanical` 0.65 tier-3 **2nd validation**
- `medium-backend` heavy sub-portion (DB + service) — informational

### 2.6 Backward-compat + safety (DB migration sensitivity)

- Data migration is **additive** (read meta_data → insert config rows); does NOT delete meta_data in this sprint (kept as transitional read-fallback)
- GET/middleware read config table first, fall back to meta_data if no config rows (transition safety)
- Down-migration drops `rate_limit_configs` (config falls back to meta_data — no data loss since meta_data retained)
- meta_data clear deferred to NEW `AD-RateLimits-MetaData-Cleanup-Phase58` (after 1-2 sprints validation that table path is stable)

---

## 3. User Stories

### US-1: NEW config table + ORM + RLS + data migration

**As a** platform operator
**I want** rate-limit quota config stored in a normalized `rate_limit_configs` table instead of `meta_data` JSONB
**So that** config is queryable, type-safe, RLS-enforced, and not an opaque blob.

**Acceptance**:
- NEW `rate_limit_configs` table: `id` (UUID) + `tenant_id` + `resource_type` (VARCHAR 64) + `window_type` (VARCHAR 32) + `quota` (Integer) + `created_at` + `updated_at`; unique `(tenant_id, resource_type, window_type)`; FK tenant_id → tenants ON DELETE CASCADE
- NEW Alembic migration (next head — Day 0 Prong 3 confirms number): CREATE table + RLS policy (mirror `0009` `tenant_isolation_*` pattern) + data migration upgrade() reading each tenant's `meta_data["rate_limits"]` → `parse_rate_limit_item()` → INSERT config rows; downgrade() DROP table
- NEW `RateLimitConfig(Base, TenantScopedMixin)` ORM in `infrastructure/db/models/api_keys.py` (sibling of `RateLimit`)
- Export in `infrastructure/db/models/__init__.py`
- ~4-5 NEW pytest (migration data-correctness + ORM CRUD + RLS isolation + unique constraint)

### US-2: Config store service + re-point WRITE/READ endpoints

**As a** tenant administrator
**I want** the existing RateLimits PUT/GET endpoints to read/write the config table (not JSONB)
**So that** the admin UI is backed by durable normalized config.

**Acceptance**:
- NEW `RateLimitConfigStore` (`platform_layer/tenant/rate_limit_config_store.py`): `list_configs(tenant_id)` / `replace_configs(tenant_id, items)` (composite-replace, mirrors Sprint 57.57 PUT semantics) + projection `_project_config_to_item()` (config row → `{label, value}` for API back-compat)
- Re-point `GET /admin/tenants/{tid}/rate-limits` (Sprint 57.48) → read config table (fallback meta_data if empty)
- Re-point `PUT /admin/tenants/{tid}/rate-limits` (Sprint 57.57) → write config table via `replace_configs` + `append_audit("tenant_rate_limits_upsert")` unchanged
- API response shape UNCHANGED (`{label, value}` items) — frontend untouched
- ~5-6 NEW pytest (GET from table / GET fallback / PUT replace / PUT audit / multi-tenant)

### US-3: Re-point middleware + usage GET to tables; wire usage table as Redis durable backing

**As a** platform operator
**I want** runtime enforcement to read config from `rate_limit_configs` and persist usage windows to the `rate_limits` table
**So that** the dormant usage table is activated (AP-4 closed) and counters survive Redis restart.

**Acceptance**:
- Re-point `RateLimitMiddleware._load_rate_limits` (Sprint 57.58) → read `rate_limit_configs` (fallback meta_data)
- Re-point Cat 2 tool gate config read → `rate_limit_configs`
- `RedisRateLimitCounter` write-through: on window increment, upsert `rate_limits` usage row (`tenant_id, resource_type, window_type, window_start, used, quota` snapshot); on Redis miss/restart, recover `used` from table
- Re-point `GET /admin/tenants/{tid}/rate-limits/usage` (Sprint 57.58) → read usage table (or Redis fast-path with table fallback)
- ~5-6 NEW pytest (middleware reads config table / usage write-through / Redis-restart recovery from table / usage GET from table / multi-tenant usage isolation)

---

## 4. Technical Specification

### 4.1 NEW `rate_limit_configs` table + ORM

```python
# === RateLimitConfig: durable per-(tenant,resource,window) quota config ===
# Why: Sprint 57.48-57.58 stored config in tenant.meta_data["rate_limits"] JSONB
# (opaque {label,value} strings). This normalizes it to a queryable RLS-enforced
# table, separate from the rate_limits usage table (which forces window_start NOT NULL
# so cannot hold window-agnostic config). Closes AP-4 Potemkin (rate_limits usage table).
# Alternative considered (C2): nullable window_start single table — rejected: semantic
# overload (a row is config-or-usage by null-ness); C1 two-table split is cleaner.
# Reference: 09-db-schema-design.md §rate limits / Sprint 57.59 Day 0 schema-tension analysis
class RateLimitConfig(Base, TenantScopedMixin):
    __tablename__ = "rate_limit_configs"
    id: Mapped[PyUUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    window_type: Mapped[str] = mapped_column(String(32), nullable=False)
    quota: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint("tenant_id", "resource_type", "window_type", name="uq_rate_limit_configs_tenant_resource_window"), ...)
```

### 4.2 Alembic migration `0019_rate_limit_configs.py` (Day 0 Prong 3 D-DAY0-J: head=0018 → next=0019)

```python
def upgrade():
    op.create_table("rate_limit_configs", ...)  # cols + unique (tenant_id,resource_type,window_type) + FK CASCADE
    op.execute("ALTER TABLE rate_limit_configs ENABLE ROW LEVEL SECURITY")
    # Day 0 D-DAY0-K: 0009 uses TWO policies per table — mirror both:
    op.execute("CREATE POLICY tenant_isolation_rate_limit_configs ON rate_limit_configs USING (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("CREATE POLICY tenant_insert_rate_limit_configs ON rate_limit_configs FOR INSERT WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    # Data migration (Day 0 D-DAY0-N: INLINE parse, do NOT import rate_limit_counter — Redis dep; Alembic dep-light):
    conn = op.get_bind()
    for tenant in conn.execute(text("SELECT id, meta_data FROM tenants WHERE meta_data ? 'rate_limits'")):
        for item in tenant.meta_data["rate_limits"]:  # {label, value} e.g. {"label":"API requests","value":"100 / min"}
            parsed = _inline_parse(item)  # label→resource_type + value "N / unit"→(quota, window_type); None=skip
            if parsed: conn.execute(insert rate_limit_configs row)

def downgrade():
    op.execute("DROP POLICY IF EXISTS tenant_insert_rate_limit_configs ON rate_limit_configs")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_rate_limit_configs ON rate_limit_configs")
    op.drop_table("rate_limit_configs")  # config falls back to retained meta_data — no data loss
```

> **Note (Day 0 D-DAY0-N)**: `parse_rate_limit_item()` in `rate_limit_counter.py` imports Redis types at module level → do NOT import into the migration. INLINE the parse logic (`_inline_parse` helper local to the migration) — Alembic migrations are historical snapshots, must be dep-light + stable. The two parse implementations are acceptable duplication (migration = frozen point-in-time; service = live).
> **Note (Day 0 D-DAY0-K)**: add BOTH `tenant_isolation_*` (USING) + `tenant_insert_*` (WITH CHECK) policies — `check_rls_policies` V2 lint expects the 0009 two-policy pattern.

### 4.3 `RateLimitConfigStore` service

`platform_layer/tenant/rate_limit_config_store.py` — CRUD over config table:
- `async def list_configs(tenant_id) -> list[RateLimitConfigRow]`
- `async def replace_configs(tenant_id, items)` — composite-replace (delete-all + insert; mirrors Sprint 57.57 PUT dict-identity-swap intent at table level)
- `_project_config_to_item(config) -> {label, value}` — API back-compat projection

### 4.4 Endpoint re-points (surgical data-source swaps)

| Endpoint | Sprint | Before | After |
|----------|--------|--------|-------|
| `GET /rate-limits` | 57.48 | read meta_data | `RateLimitConfigStore.list_configs` (fallback meta_data if empty) |
| `PUT /rate-limits` | 57.57 | write meta_data | `RateLimitConfigStore.replace_configs` + audit unchanged |
| `GET /rate-limits/usage` | 57.58 | Redis peek | usage table read (Redis fast-path + table fallback) |
| `RateLimitMiddleware` + Cat 2 gate | 57.58 | read meta_data | read config table (fallback meta_data) |

API response shapes UNCHANGED → frontend untouched (US has no frontend track beyond type-alignment verification).

### 4.5 Redis write-through to usage table

`RedisRateLimitCounter.check_and_increment` — after Redis increment, async upsert `rate_limits` usage row. Day 0 D-DAY0-G: the table has BOTH `window_start` AND `window_end` (NOT NULL) → populate both:
- `window_start` = current window anchor (floor of now to window boundary)
- `window_end` = `window_start + window_seconds`
- `used` = post-increment count; `quota` = config snapshot (denormalized — see §8 R9)

On Redis cache miss (restart), `_recover_from_table(tenant, resource, window)` seeds Redis from the table's `used` for the current window (`window_end > now`). Fail-open preserved (table write failure logs + continues; Redis hot-path unaffected).

### 4.6 Verification

- ~15 NEW pytest (US-1 ~4-5 + US-2 ~5-6 + US-3 ~5-6)
- pytest baseline 1819 → ~1834+
- Frontend: 0 new tests expected (UI unchanged); confirm existing QuotasTab + useRateLimits* still green
- mypy --strict 0 / 9/9 V2 lints / 0 SDK leak / HEX_OKLCH baseline 48 / DUAL CLEAN 22/22 PARITY 15 consec 57.45-57.59

### 4.7 Risk mitigation

| Risk | Mitigation |
|------|-----------|
| Data migration corrupts existing config | Additive only (no meta_data delete); downgrade drops table cleanly; migration test on seeded tenants |
| `parse_rate_limit_item` import-heavy in migration | Day 0 Prong 3 decides import vs inline; keep migration dep-light |
| Per-request DB read for config (latency) | Config cached in middleware (60s TTL, same as Sprint 57.58); table read only on cache miss |
| Per-request usage table write (latency) | Async/best-effort write-through; Redis stays hot-path; fail-open |
| RLS missing on new table | Migration includes ENABLE RLS + policy; `check_rls_policies` V2 lint enforces |
| meta_data fallback drift | Transitional only; NEW `AD-RateLimits-MetaData-Cleanup-Phase58` removes fallback after validation |

---

## 5. File Change List

### Backend (NEW + EDIT)

**NEW**:
- `backend/src/infrastructure/db/migrations/versions/00XX_rate_limit_configs.py` (Day 0 Prong 3 confirms number; CREATE table + RLS + data migration)
- `backend/src/platform_layer/tenant/rate_limit_config_store.py` (`RateLimitConfigStore`)
- `backend/tests/integration/api/test_rate_limit_config_migration.py` (~4-5 migration + ORM + RLS tests)
- `backend/tests/integration/api/test_admin_tenant_rate_limits_table.py` (~5-6 re-pointed GET/PUT tests)
- `backend/tests/integration/agent_harness/test_rate_limit_usage_persistence.py` (~5-6 middleware config-read + usage write-through + Redis-recovery tests)

**EDIT**:
- `backend/src/infrastructure/db/models/api_keys.py` — NEW `RateLimitConfig` ORM (sibling of `RateLimit`)
- `backend/src/infrastructure/db/models/__init__.py` — export `RateLimitConfig`
- `backend/src/api/v1/admin/tenants.py` — re-point GET + PUT + usage GET to tables (fallback meta_data)
- `backend/src/platform_layer/middleware/rate_limit.py` — `_load_rate_limits` read config table
- `backend/src/platform_layer/tenant/rate_limit_counter.py` — write-through usage table + `_recover_from_table`
- `backend/src/platform_layer/tenant/tool_rate_limit_gate.py` — config read from table
- `backend/tests/integration/api/conftest.py` — `RATE_LIMIT_CONFIG_%` sweep + `rate_limit_configs`/`rate_limits` table cleanup

### Frontend (verify-only; no functional change expected)

- Confirm `useRateLimits` / `useRateLimitsSave` / `useRateLimitsUsage` + QuotasTab unchanged (API shapes preserved); align types only if response field names shift (should not)

### Sprint artifacts (Day 0 + Day 2)

- `sprint-57-59-plan.md` (this) + `sprint-57-59-checklist.md`
- `agent-harness-execution/phase-57/sprint-57-59/progress.md` + `retrospective.md`
- `memory/project_phase57_59_rate_limits_potemkin_migration.md`
- `claudedocs/4-changes/refactoring/REFACTOR-003-sprint-57-59-rate-limits-potemkin-migration.md` (refactor — schema migration, not a feature)

---

## 6. Workload

**Agent-delegated: yes** (≥80% Day 1 via code-implementer; sequential — backend migration+ORM+service agent → backend re-points agent → verify)

**Bottom-up est ~18 hr** → class-calibrated commit ~11.7 hr (mult 0.65 `mixed-multidomain-bundle`) → **agent-adjusted commit ~7.6 hr** (`agent_factor` 0.65 `mixed-multidomain-bundle-mechanical` tier-3 2nd validation)

| Task | Bottom-up | Class-calibrated | Agent-adjusted |
|------|-----------|-----------------|---------------|
| Day 0 三-Prong (Path + Content + **Schema verify critical**) + plan | 1.0 hr | 1.0 hr | 1.0 hr (parent) |
| US-1: table + ORM + Alembic + data migration + tests | 6 hr | 3.9 hr | 2.5 hr |
| US-2: config store + GET/PUT re-point + tests | 5 hr | 3.25 hr | 2.1 hr |
| US-3: middleware/gate/usage re-point + write-through + tests | 5 hr | 3.25 hr | 2.1 hr |
| Day 1 validation sweep | 0.5 hr | 0.5 hr | parent |
| Day 2 closeout | 0.7 hr | 0.7 hr | 0.7 hr (parent) |
| **Total** | **~18 hr** | **~11.7 hr** | **~7.6 hr** |

Validation threshold: `actual/agent-adjusted` in [0.85, 1.20]; < 0.7 OR > 1.20 → tier-3 `mixed-multidomain-bundle-mechanical` 2nd-validation rollback rule fires (57.58 1st was ~0.49 → if 57.59 also < 0.7, tighten 0.45).

---

## 7. Acceptance Criteria

### Functional
- [ ] `rate_limit_configs` table created + RLS + unique constraint
- [ ] Data migration: existing `meta_data["rate_limits"]` → config rows (idempotent; additive)
- [ ] GET/PUT re-pointed to config table; API response shape UNCHANGED
- [ ] Middleware + Cat 2 gate read config from table (fallback meta_data)
- [ ] Usage write-through to `rate_limits` table; Redis-restart recovery from table
- [ ] usage GET reads table/Redis
- [ ] Multi-tenant isolation on both new+existing tables (RLS test)
- [ ] Down-migration drops `rate_limit_configs` cleanly (meta_data fallback intact)
- [ ] Frontend QuotasTab + 3 hooks unchanged + green

### Quality
- [ ] pytest 1819 → 1834+ (NO regressions)
- [ ] mypy --strict 0 / 9/9 V2 lints (incl. `check_rls_policies` on new table) / 0 SDK leak
- [ ] HEX_OKLCH baseline 48 / DUAL CLEAN 22/22 PARITY 15 consec
- [ ] Vitest 675 unchanged (no frontend functional change) / Vite build clean

### Process
- [ ] Day 0 三-Prong (Path + Content + **Schema verify** mandatory — new table)
- [ ] AP-4 Potemkin closed (`rate_limits` table now queried/written)
- [ ] Sequential code-implementer agent delegation
- [ ] Day 2 closeout artifacts (retro Q1-Q6 + memory + CLAUDE.md + next-phase + REFACTOR-003)
- [ ] PR + CI green + merge

---

## 8. Risks

| # | Risk | Class | Mitigation |
|---|------|-------|-----------|
| R1 | Data migration on production tenants corrupts/loses config | DB migration | Additive only (no delete); downgrade safe; test on seeded multi-tenant fixtures; `parse_rate_limit_item` skips unparseable items gracefully |
| R2 | Alembic head number drift | Risk Class (Schema) | Day 0 Prong 3: `ls migrations/versions | sort -V | tail -3` confirms next number |
| R3 | `parse_rate_limit_item` import heavy in migration | Tooling | Day 0 Prong 3 decides import-vs-inline; Alembic migrations dep-light |
| R4 | Per-request config/usage DB I/O latency | Performance | Middleware 60s config cache (Sprint 57.58) + async best-effort usage write-through; Redis hot-path unchanged |
| R5 | RLS missing on new table → `check_rls_policies` lint fail | Security | Migration includes ENABLE RLS + `tenant_isolation_rate_limit_configs` policy (mirror 0009) |
| R6 | meta_data fallback masks table-read bugs | Logic | Tests assert table-read path explicitly (not just fallback); NEW `AD-RateLimits-MetaData-Cleanup-Phase58` removes fallback after validation |
| R7 | `mixed-multidomain-bundle-mechanical` 0.65 tier-3 2nd validation surfaces < 0.7 OR > 1.20 | Calibration | 2nd validation: if < 0.7 tighten 0.45; if > 1.20 rollback 1.0 (57.58 1st = ~0.49 below) |
| R8 | Citus sharding (future) on `rate_limit_configs` distribution key | Architecture | tenant_id is the natural distribution key (consistent with other business tables); note for Citus PoC |
| R9 | Existing `RateLimit` usage table `quota` column now denormalized snapshot | Schema | Document: `quota` on usage row = config snapshot at window open (avoids hot-path join); config table is authoritative for current quota |

---

## 9. Carryover ADs (for Sprint 57.60+ pickup)

| ID | Status | Notes |
|----|--------|-------|
| `AD-RateLimits-MetaData-Cleanup-Phase58` | NEW | After 1-2 sprints validating table path stable → remove `meta_data["rate_limits"]` read-fallback + clear stored JSONB (data migration); ~1-2 hr |
| `AD-RateLimits-SyntaxValidation-Phase58` | CARRYOVER | Now easier post-split (config table has typed `quota`/`window_type` columns); PUT-time validation |
| `AD-RateLimits-Alerting-Phase58` | CARRYOVER | SSE 80% threshold; pairs with usage table |
| `AD-AgentFactor-Tier-3-MixedBundle-Mechanical-Validation-Sprint-57.60` | CONDITIONAL | 3rd validation IF Sprint 57.60 is another mechanical multi-track bundle |
| `AD-Day0-Prong2-Nested-Shape-Read` | CONTINUES | Codify if 2-3 data points (57.58 D-DAY1-1 was 1st) |
| `AD-medium-frontend-Baseline-Recalibration` / `AD-MediumBackend-AICadence-Recalibration` / `AD-Test-Cleanup-Pattern-Shared-Helper` | CONTINUES | Phase 58+ |

---

**Plan v1 status**: drafted 2026-05-28 Day 0 (pre-Day 0 三-Prong Verify); awaiting user approval before checklist v1 + Day 0 三-Prong execution.

**Open user decision points** (Day 0 approval gate):
1. **Confirm scope** C1 two-table split + additive data migration (meta_data retained as fallback) + 4 endpoint re-points + Redis write-through to usage table
2. **Agent delegation**: sequential 2-agent (backend migration+ORM+service+re-points → verify) vs 3-agent split
3. **REFACTOR-003 vs CHANGE-029**: classify as REFACTOR (schema migration) — confirm
4. **meta_data cleanup timing**: deferred to `AD-RateLimits-MetaData-Cleanup-Phase58` (this sprint keeps fallback) — confirm not in-scope this sprint
