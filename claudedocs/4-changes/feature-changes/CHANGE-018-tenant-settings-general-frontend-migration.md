# CHANGE-018: GeneralTab — real backend SaaS settings consumption

**Date**: 2026-05-26
**Sprint**: 57.49 Day 1 (Track A 1.1.1)
**Scope**: Frontend / tenant-settings / GeneralTab + _fixtures cleanup

## Problem

GeneralTab in Sprint 57.44 rebuild consumed `GENERAL_FIXTURE` (region/locale/retentionDays) hard-coded fixture values. Sprint 57.46 extended backend `TenantResponse` schema with 5 real SaaS settings fields (`region/locale/retention_days/sso_enabled/seats`) but frontend never migrated.

## Root Cause

Sprint 57.46 was backend-only schema extension; frontend consumption was queued as Sprint 57.49 Track A.

## Solution

- `GeneralTab.tsx` drops `GENERAL_FIXTURE` import; reads `data.region`, `data.locale`, `data.retention_days`, `data.seats` directly from `TenantSettingsResponse`
- `data.sso_enabled` (bool) drives Identity & SSO card "SSO Provider" badge (success/disabled tone)
- `IDENTITY_FIXTURE` retained for `provider/scim/allowedDomains/mfa` (backend gap pending)
- `_fixtures.ts` cleanup: drop `GENERAL_FIXTURE` + `SEATS_FIXTURE` exports
- `types.ts`: `TenantSettingsResponse` extended with 5 fields + `TenantUpdateRequest` extended with same patch-able fields

## Verification

- TenantSettingsView test SAMPLE updated with 5 new fields
- tenantSettingsService test MOCK_RESPONSE updated with 5 new fields
- useTenantSettings test SAMPLE updated with 5 new fields
- New "SSO Provider" assertion in default-tab test
- ESLint + tsc clean

## Impact

Frontend-only; backend schema already shipped Sprint 57.46. GeneralTab now shows real per-tenant `region`/`locale`/`retention_days`/`seats`/`sso_enabled` from DB (Sprint 57.43 `_load_tenant_or_404` enforces tenant access).

PATCH UI for these fields kept as `readOnly` per Sprint 57.49 scope — inline edit deferred Phase 58+ (backend already supports `TenantUpdateRequest` for these).
