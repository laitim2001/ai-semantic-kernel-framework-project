# CHANGE-019: FeatureFlagsTab — fixture → useFeatureFlags real backend

**Date**: 2026-05-26
**Sprint**: 57.49 Day 1 (Track A 1.1.2)
**Scope**: Frontend / tenant-settings / FeatureFlagsTab

## Problem

FeatureFlagsTab consumed `FEATURE_FLAGS` fixture (8 hard-coded entries from `_fixtures.ts`). Sprint 57.48 Track B shipped `/admin/tenants/{id}/feature-flags` endpoint exposing tenant-resolved boolean values.

## Solution

- NEW `useFeatureFlags(tenantId)` TanStack Query hook
- NEW `fetchFeatureFlags(tenantId, limit?, offset?)` service function
- `FeatureFlagsTab` accepts `tenantId: string` prop
- Tab consumes hook data; shows Loading/Error/Empty states + BackendGapBanner
- Adapter: backend `FeatureFlagItem.value` (bool) → Switch; numeric override (mockup `ctl: "num"`) not in backend yet — all rows boolean
- `def` derived from `default_enabled` (bool → "on"/"off" Badge)
- `desc` falls back to "—" when backend `description` null

## Verification

- `useSubResourceHooks.test.tsx` covers QUERY_KEY_BASE + enabled guard + success
- `tenantSettingsService.test.ts` covers fetchFeatureFlags URL build

## Impact

Frontend now displays real tenant-effective feature flag state across all 8+ registered flags. Numeric override (legacy mockup `ctl: "num"`) deferred Phase 58+ when backend write API lands.
