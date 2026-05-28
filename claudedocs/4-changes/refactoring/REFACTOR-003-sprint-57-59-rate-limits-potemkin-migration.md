# REFACTOR-003: RateLimits Potemkin Migration — two-table split (Sprint 57.59)

**Date**: 2026-05-28
**Sprint**: 57.59
**Scope**: `infrastructure/db` (NEW table + ORM + Alembic) + Cat 12 (middleware) + Cat 2 (tool gate) + Cat 9 (admin endpoints) + `platform_layer/tenant` (counter + config store)

## Problem

The `rate_limits` ORM table (`infrastructure/db/models/api_keys.py:141`) was defined + migrated (`0006_api_keys_rate_limits.py` + RLS `0009`) since the Phase 49 V2 baseline but **never queried or written** in production — an AP-4 Potemkin Feature surfaced during Sprint 57.58 Day 0 三-Prong. Meanwhile Sprint 57.48-57.58 stored rate-limit config in `tenant.meta_data["rate_limits"]` JSONB (opaque `{label, value}` strings) and tracked live usage only in Redis (ephemeral; lost on restart).

## Root Cause

The original Phase 49 schema intent (a per-(tenant, resource, window) usage table with `quota`/`used`/`window_start`/`window_end`) was never wired; later sprints independently reimplemented config + usage in JSONB + Redis without using the table. The table's `window_start NOT NULL` unique key also means it is a usage-instance table that cannot hold window-agnostic config — so a clean activation requires splitting config into its own table.

## Solution (C1 two-table split — user-locked 2026-05-28)

- **NEW `rate_limit_configs` table** (Alembic `0019`, `down_revision = 0018_tenant_settings_extension`): `id` + `tenant_id` (FK CASCADE) + `resource_type` + `window_type` + `quota` + timestamps + unique `(tenant_id, resource_type, window_type)` + **two RLS policies** (`tenant_isolation_*` USING + `tenant_insert_*` WITH CHECK, per 0009 pattern). Durable config, replaces JSONB.
- **NEW `RateLimitConfig` ORM** (sibling of `RateLimit`) + `__all__` export.
- **Data migration** (additive): reads `tenants."metadata" ? 'rate_limits'`, INLINE-parses each `{label, value}` → config rows (skips unparseable); `meta_data` retained as transitional fallback; `downgrade()` drops policies + table (no data loss).
- **NEW `RateLimitConfigStore`** (`platform_layer/tenant/rate_limit_config_store.py`): `list_configs` / `replace_configs` (composite-replace) / `_project_config_to_item` ({label,value} back-compat).
- **Re-point GET/PUT** (`admin/tenants.py`): config table source of truth + fallback meta_data + transitional dual-write; API shape UNCHANGED (frontend untouched).
- **Activate `rate_limits` usage table**: `RedisRateLimitCounter` write-through (`window_start`+`window_end` upsert via `pg_insert.on_conflict_do_update`, `used = GREATEST`) + `_recover_from_table` on Redis miss; optional `session_factory` DI (counter singleton self-acquires session + RLS context; `main.py` injects `get_session_factory`).
- **Re-point middleware + tool gate + usage GET** to the tables (fallback meta_data / Redis peek + table fallback). Cat 2 seam stays LLM-neutral.

## Verification

- pytest 1819 → **1840** (+21; 6 migration + 9 GET/PUT-table + 6 usage-persistence): data-migration correctness + ORM CRUD + RLS multi-tenant isolation + GET-from-table + GET-fallback + PUT-replace + audit + write-through create/update + Redis-restart recovery + multi-tenant usage isolation
- migration up/down/up clean (head `0019`); `check_rls_policies` PASS (20 RLS tables, +1); `check_llm_sdk_leak` PASS
- mypy --strict 0 / 9/9 V2 lints / 0 frontend touched (Vitest 675 unaffected) / HEX_OKLCH 48
- **AP-4 closure**: `rate_limits` usage table now written (`pg_insert`) + queried (recovery + usage GET)

## Impact

- Config + usage both DB-backed + RLS-enforced; JSONB path deprecated (transitional fallback + dual-write retained)
- Counters now durable (survive Redis restart via table recovery)
- 0 AP-4 Potemkin tables in RateLimits subsystem
- Deferred: `AD-RateLimits-MetaData-Cleanup-Phase58` (remove fallback + dual-write + clear JSONB after 1-2 sprints validation)
- Calibration: `mixed-multidomain-bundle-mechanical` 0.65 tier-3 2nd validation ~0.34 → tighten 0.45 (Sprint 57.60+)
- PR: (pending) `feature/sprint-57-59-rate-limits-potemkin-migration`
