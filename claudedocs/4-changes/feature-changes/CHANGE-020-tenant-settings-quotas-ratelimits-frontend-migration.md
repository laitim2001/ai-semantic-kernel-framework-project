# CHANGE-020: QuotasTab (combined) — fixture → useQuotas + useRateLimits real backend

**Date**: 2026-05-26
**Sprint**: 57.49 Day 1 (Track A 1.1.3)
**Scope**: Frontend / tenant-settings / QuotasTab (Usage quotas + Rate limits)

## Problem

QuotasTab consumed `QUOTAS` (5 hard-coded) + `RATE_LIMITS` (3 hard-coded) fixture entries. Sprint 57.48 Track C + D shipped two endpoints.

## Solution

- 2 NEW hooks: `useQuotas(tenantId)` + `useRateLimits(tenantId)`
- 2 NEW service funcs: `fetchQuotas` + `fetchRateLimits`
- `QuotasTab` accepts `tenantId: string` prop; consumes both hooks independently
- Each Card has its own Loading/Error/Empty state
- Adapter: backend `QuotaItem.current_usage` is `null` at admin layer (per Sprint 57.48 Redis-gate decision) — `pct` falls back to 0%; bar-track still rendered for visual consistency
- `formatLimit` helper: tokens ≥1M → "10.0M" formatting; ≥1k → toLocaleString; smaller numeric stays raw
- `RateLimitItem.{label, value}` matches mockup fixture directly — no adapter

## Verification

- `useSubResourceHooks.test.tsx` covers both hooks
- `tenantSettingsService.test.ts` covers both service funcs
- `null` current_usage assertion

## Impact

Quotas tab now shows real PlanQuota limits (tokens_per_day / cost_usd_per_day / sessions / api_keys_max). Live usage tracking deferred Phase 58+ (Redis counter wiring not in admin endpoint scope).
