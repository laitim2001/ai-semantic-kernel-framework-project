# CHANGE-030: RateLimits 80%-Threshold Usage Alerting (persisted log + GET + QuotasTab surface)

**Change Date**: 2026-05-29
**Sprint**: 57.62
**Change Type**: New Feature
**Scope**: Category 2 (Tool Layer rate-limit gate) + platform_layer/tenant + Cat 9 admin endpoint + Frontend (tenant-settings)
**Status**: ✅ Completed (Day 1 `95c65e09`; closes `AD-RateLimits-Alerting-Phase58`)

## Change Summary

Adds **server-side 80%-threshold usage alerting** to the RateLimits subsystem. When a tenant's rate-limit usage for a `(resource_type, window_type)` crosses 80% of its configured quota, a row is **persisted** to a new `rate_limit_alerts` table — so the breach is captured **even when no admin is watching the live-usage card**. The recent alerts are exposed via a GET endpoint and surfaced in a new QuotasTab "Recent alerts" card.

## Change Reason

Pre-57.62, the RateLimits subsystem enforced limits (57.58 middleware + Cat 2 gate), persisted usage (57.59 two-table split), and showed live usage with threshold colors (57.58 QuotasTab Live usage card). But a breach that happened while no admin had the card open left **no trace** — there was no durable record of "this tenant approached/hit its limit at time T". `AD-RateLimits-Alerting-Phase58` (57.57/57.60/57.61 carryover) asked to capture those unwatched breaches.

**Design pivot at Day 0**: the carryover claimed "SSE infra ~80% from prior sprints; ~3-4 hr". Pre-plan Explore recon proved that false (the only SSE in the repo is the agent-loop `LoopEvent` stream; an admin SSE channel is greenfield ~8-12 hr). User locked **Option A persisted alert log** (~4-6 hr, polling-reuse) over an SSE build.

## Detailed Changes

### Backend (US-1 detection + persistence)
- **NEW `RateLimitAlert` ORM** (`infrastructure/db/models/api_keys.py`, `rate_limit_alerts`, `TenantScopedMixin`): `resource_type`/`window_type`/`severity` (lowercase `warning`/`critical`) + `threshold_pct`/`actual_pct`/`used`/`quota` (int) + `window_start`/`triggered_at`. `UNIQUE (tenant_id, resource_type, window_type, window_start)` + `CHECK severity IN ('warning','critical')` + index `(tenant_id, triggered_at)`.
- **NEW Alembic `0021_rate_limit_alerts`** (down_revision `0020`): CREATE table + `ENABLE` + `FORCE ROW LEVEL SECURITY` + 2 policies (`tenant_isolation_rate_limit_alerts` USING + `tenant_insert_rate_limit_alerts` WITH CHECK, both `current_setting('app.tenant_id', true)::uuid`) + CHECK + index.
- **NEW stateless `RateLimitAlertStore`** (`platform_layer/tenant/rate_limit_alert_store.py`): `ALERT_THRESHOLD_PCT = 80`; `_severity(pct) → "critical" if pct >= 100 else "warning"`; `maybe_record(session, tenant_id, resource_type, window_type, *, used, quota, window_start)` — early-returns on `quota <= 0` or `pct < 80`; idempotent peak/escalate upsert via `pg_insert(...).on_conflict_do_update` (`actual_pct = GREATEST(...)`, severity escalates warning → critical; `triggered_at` not updated); `list_recent(session, tenant_id, limit=20)` newest-first.
- **Detection hook** (`platform_layer/tenant/rate_limit_counter.py`): `RedisRateLimitCounter._write_through` calls `RateLimitAlertStore().maybe_record(...)` after the usage upsert, inside the existing best-effort try/except (fail-open — never breaks enforcement). **Stateless store + session already present → NO ctor DI, NO `api/main.py` wiring** (D-DAY0-G).

### Backend (US-2 read)
- **NEW `GET /api/v1/admin/tenants/{tenant_id}/rate-limits/alerts?limit=N`** (`api/v1/admin/tenants.py`): `RateLimitAlertItem` + `RateLimitAlertsResponse`; default limit 20, `ge=1 le=100`; newest-first; reuses `_load_tenant_or_404`.

### Frontend (US-3 surface)
- **NEW `useRateLimitsAlerts.ts`** (TanStack `useQuery`, `refetchInterval: 15000`, key `RATE_LIMITS_ALERTS_QUERY_KEY_BASE`) + `fetchRateLimitsAlerts(tenantId, limit?, signal?)` in `tenantSettingsService.ts` + `RateLimitAlertItem`/`RateLimitAlertsResponse` TS types (snake_case mirror).
- **`QuotasTab.tsx`**: NEW "Recent alerts" card BELOW the Live usage card (resource · peak % · severity badge `.badge.warning`/`.badge.danger` · relative time + empty state). Reuses existing `--warning`/`--danger` tokens — **0 new oklch** (HEX_OKLCH baseline 48 unchanged). Existing Rate limits + Live usage cards bit-for-bit unchanged (scope-guard test).

### Deliberate design decision (R8 — `severity` 2-tier vs `SLAViolation` 3-tier)
`RateLimitAlert` uses a 2-tier severity (`warning` at ≥80%, `critical` at ≥100%) where `SLAViolation` uses 3-tier (`minor`/`major`/`critical`). This is intentional: rate-limit alerting has two natural states — "approaching the limit" (warning) and "at/over the limit" (critical/throttled) — not three. `threshold_pct`/`actual_pct` are `int` (rate-limit pct is integer-grained) vs `SLAViolation`'s `Numeric(8,4)`.

## Modified Files List

**NEW (7)**: `0021_rate_limit_alerts.py` · `rate_limit_alert_store.py` · `test_rate_limit_alert_store.py` (12) · `test_admin_tenant_rate_limits_alerts.py` (6) · `test_rate_limit_alerts_migration.py` (2) · `useRateLimitsAlerts.ts` · `useRateLimitsAlerts.test.tsx` (4)
**EDIT (10)**: `api_keys.py` · `models/__init__.py` · `rate_limit_counter.py` · `api/v1/admin/tenants.py` · `QuotasTab.tsx` · `tenantSettingsService.ts` · `types.ts` · `QuotasTab.test.tsx` (+13) · sprint progress.md · sprint checklist.md

## Test Checklist

- [x] pytest 1887 → **1907** (+20: 12 store + 6 endpoint + 2 migration); 0 regressions
- [x] Store: 80/90/100 → row+severity; <80 → none; quota<=0 → none; dedup once-per-window (peak); warning→critical escalation; fail-open no-session/DB-error; multi-tenant isolation
- [x] Endpoint: auth/404; empty list; newest-first ordering; limit cap 100; multi-tenant isolation
- [x] mypy `src --strict` 0/319 · 9/9 V2 lints (`check_rls_policies` 21 tables) · black/isort/flake8 clean
- [x] Frontend Vitest → **686** (+17: 4 hook + 13 QuotasTab incl. 2-card scope-guard) · tsc + build ✓ · ESLint exit 0
- [x] OKLCH delta 0 (baseline 48) · Alembic `0021` live down→up clean

## Impact

Backend + frontend. Additive: new table + new GET endpoint + new frontend card. No change to enforcement behavior (alert hook is fail-open best-effort). No schema change to existing tables. API shape of existing RateLimits endpoints unchanged. Closes `AD-RateLimits-Alerting-Phase58`.
