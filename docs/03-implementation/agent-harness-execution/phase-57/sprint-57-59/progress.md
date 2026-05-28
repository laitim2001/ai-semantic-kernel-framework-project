# Sprint 57.59 — Progress

**Goal**: Close AP-4 Potemkin via C1 two-table split — NEW `rate_limit_configs` + activate `rate_limits` usage table (`AD-RateLimits-Potemkin-Migration-Phase58`)
**Class**: `mixed-multidomain-bundle` 0.65 (SCOPE 3rd data point)
**Agent-factor**: `mixed-multidomain-bundle-mechanical` 0.65 (tier-3 **2nd validation**)
**Start date**: 2026-05-28

Plan: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-59-plan.md`
Checklist: `docs/03-implementation/agent-harness-planning/phase-57-frontend-saas/sprint-57-59-checklist.md`

---

## Day 0 — 2026-05-28

### Today's Accomplishments

- Plan v1 + checklist v1 drafted (9-section mirror 57.58); user approved 2026-05-28
- Branch `feature/sprint-57-59-rate-limits-potemkin-migration` created from main `5736e0a4`
- Day 0 三-Prong Verify executed (Path + Content + **Schema verify** — new table + data migration)

### Drift findings (15 checks — 12 GREEN + 3 🆕 NOTABLE + 1 🔴 minor; NO CRITICAL)

#### Prong 1 — Path Verify (all GREEN)

- ✅ **D-DAY0-A**: `0019_rate_limit_configs.py` not exist (Alembic head = `0018_tenant_settings_extension.py` → next = **0019**)
- ✅ **D-DAY0-B**: `platform_layer/tenant/rate_limit_config_store.py` NOT exist (Glob 0 results)
- ✅ **D-DAY0-C**: `RateLimitConfig` ORM NOT exist (`api_keys.py` `__all__ = ["ApiKey", "RateLimit"]`)
- ✅ **D-DAY0-D**: Sprint 57.58 re-point targets present (`rate_limit_counter.py` has `parse_rate_limit_item` + `RedisRateLimitCounter` + `check_and_increment` L200 + `peek` L248)

#### Prong 2 — Content Verify (GREEN + nested-shape lesson applied)

- ✅ **D-DAY0-E**: `parse_rate_limit_item(item: object) -> ParsedRateLimit | None` (L158) — parses `{label, value}` dict, returns `ParsedRateLimit` (resource/limit/window) or None (skip)
- ✅ **D-DAY0-F**: `RateLimitItem(BaseModel)` (`tenants.py:1333`) = `{label: str, value: str}` + `model_config = ConfigDict(from_attributes=True)` — confirmed by READING the Pydantic body (per `AD-Day0-Prong2-Nested-Shape-Read` lesson, NOT just grep)
- ✅ **D-DAY0-G** (see NOTABLE below): `RateLimit` usage ORM full schema read
- ✅ **D-DAY0-I**: `check_and_increment` (L200) + `peek` (L248) — write-through hook sites confirmed

#### Prong 3 — Schema Verify (CRITICAL prong; 3 NOTABLE)

- ✅ **D-DAY0-J**: Alembic head `0018` → next = **0019** (no collision)
- ✅ **D-DAY0-L**: `TenantScopedMixin` provides `tenant_id` + FK; `RateLimit` uses it → `RateLimitConfig` mirrors
- ✅ **D-DAY0-M**: `rate_limits` 0006 schema = the ORM (covered by D-DAY0-G)
- ✅ **D-DAY0-O**: data migration uses PostgreSQL JSONB `meta_data ? 'rate_limits'` key-existence operator (supported)

#### 🆕 NOTABLE / 🔴 findings

**🆕 D-DAY0-G — `rate_limits` usage table has `window_end` too (plan only mentioned `window_start`)**
- Full schema: `id` + `resource_type`(VARCHAR64) + `window_type`(VARCHAR32) + `quota`(Integer) + `used`(Integer default 0) + `window_start`(timestamptz NOT NULL) + **`window_end`(timestamptz NOT NULL)** + unique `(tenant_id, resource_type, window_type, window_start)` + index `idx_rate_limits_lookup (tenant_id, resource_type, window_end DESC)`
- **Implication**: US-3 Redis write-through must populate BOTH `window_start` AND `window_end` (window_end = window_start + window_seconds). Plan §4.5 updated to note window_end.

**🆕 D-DAY0-K — RLS in 0009 uses TWO policies per table (loop-based)**
- Pattern: `CREATE POLICY tenant_isolation_{tbl} ... USING (...)` + `CREATE POLICY tenant_insert_{tbl} ... WITH CHECK (...)` (both, for SELECT/UPDATE/DELETE isolation + INSERT check)
- **Implication**: 0019 migration adds BOTH `tenant_isolation_rate_limit_configs` (USING) + `tenant_insert_rate_limit_configs` (WITH CHECK) inline. `check_rls_policies` V2 lint expects this.

**🔴 D-DAY0-N — inline `parse_rate_limit_item` in Alembic migration (do NOT import)**
- `parse_rate_limit_item` lives in `rate_limit_counter.py` which imports Redis types (module-level). Importing the module into an Alembic migration risks pulling heavy/unstable deps.
- **Resolution**: INLINE the parse logic (label→resource_type + value→quota/window_type) directly in the 0019 migration `upgrade()`. Alembic migrations are historical snapshots — should be dep-light + stable even if app code later changes. Day 1 US-1 agent inlines.

### Scope shift assessment

- 0 CRITICAL; 3 NOTABLE refinements (window_end column + RLS double-policy + inline parse) = ~5% scope detail, NOT scope change
- **Go for Day 1** (≤20% shift; risks noted in plan §8)

### Plan v1.1 micro-amendments (audit trail)

1. §4.5 write-through: populate `window_end` (= window_start + window_seconds) in addition to window_start
2. §4.2 migration: add BOTH RLS policies (isolation USING + insert WITH CHECK) per 0009 pattern; migration number = **0019**
3. §4.2 migration: INLINE parse logic (do not import `parse_rate_limit_item`); dep-light Alembic convention

### Day 0 Workload tracking

- Plan v1 + checklist v1 drafting: ~45 min (parent)
- Day 0 三-Prong (parallel Glob/Grep/Read + Alembic head check): ~20 min (parent)
- **Total Day 0**: ~65 min parent; on track vs ~1.0 hr §6 estimate

