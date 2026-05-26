# CHANGE-022: MembersTab — fixture → useTenantMembers real backend (shared hook)

**Date**: 2026-05-26
**Sprint**: 57.49 Day 1 (Track A 1.1.5 + Track B shared)
**Scope**: Frontend / tenant-settings / MembersTab + shared hook

## Problem

MembersTab consumed `MEMBERS` (8 hard-coded rows) fixture. Sprint 57.47 shipped `/admin/tenants/{id}/members` endpoint projecting from User ORM.

## Solution

- NEW `useTenantMembers(tenantId, limit?, offset?)` hook — **SHARED with Track B `TenantMembersDrawer`** (one cache namespace per tenant)
- NEW `fetchTenantMembers` service func with optional pagination
- `MembersTab` accepts `tenantId: string` prop; consumes hook
- Adapter (backend User schema is leaner than mockup fixture):
  - `role` (admin/operator/compliance) NOT in User ORM → status Badge shown instead
  - `last_active` NOT in User ORM → `created_at` rendered via `toLocaleDateString`
  - `c` (avatar hue index) NOT in backend → `hueFromId` helper derives stable hue from user `id` charCodes (preserves visual variety per row)
  - `display_name` `null` fallback → email local-part (e.g., `bob@acme.com` → "bob")

## Verification

- `useSubResourceHooks.test.tsx` covers hook + QUERY_KEY_BASE
- `tenantSettingsService.test.ts` covers fetchTenantMembers URL build w/ + w/o pagination
- `TenantMembersDrawer.test.tsx` covers shared hook in drawer context

## Impact

Frontend now shows real tenant member list. Role / last-active / capacity columns deferred Phase 58+ (User ORM extension required for those fields).
