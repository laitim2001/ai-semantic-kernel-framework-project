# CHANGE-023: AdminTenants — TenantMembersDrawer (Track B)

**Date**: 2026-05-26
**Sprint**: 57.49 Day 1 (Track B)
**Scope**: Frontend / admin-tenants / TenantMembersDrawer + TenantsTable row click + AdminTenantsView mount

## Problem

Sprint 57.47 backend shipped `/admin/tenants/{id}/members` endpoint, but `/admin-tenants` list page had no UI surface to drill into a tenant's members. Users had to navigate away to `/tenant-settings` (different page, requires tenant-context switch).

## Solution

- NEW `frontend/src/features/admin-tenants/components/TenantMembersDrawer.tsx`
  - Slide-over right-side drawer (~520 px) over translucent backdrop
  - Closed when `tenantId === null`; opens with selected tenant_id
  - Uses **SHARED** `useTenantMembers` hook from `frontend/src/features/tenant-settings/hooks/` (no hook duplication)
  - Loading / Error / Empty / Populated states
  - Pagination footer (Previous / Next) when `total > PAGE_SIZE` (50)
  - Close triggers: X button / backdrop click / Escape key
- MODIFY `TenantsTable.tsx`:
  - NEW optional `onRowClick?: (tenantId: string) => void` prop
  - Rows become clickable + cursor pointer when handler provided
  - `data-testid="tenant-row-{id}"` for test addressability
- MODIFY `AdminTenantsView.tsx`:
  - Hosts `selectedTenantId` state + drawer mount
  - Wires `setSelectedTenantId` as `onRowClick`

## Verification

- `TenantMembersDrawer.test.tsx`: 9 tests (closed/open/loading/error/empty/rows/close-btn/backdrop/pagination)
- `AdminTenantsView.test.tsx`: 3 NEW integration tests (drawer-closed-default / row-click-opens / close-hides)

## Impact

Platform admins can now drill into per-tenant member rosters inline from the list page. Backend already enforces multi-tenant isolation via `require_tenant_match_or_platform_admin` (Sprint 57.13 US-A3); UI follows.

Shared hook between tenant-settings + admin-tenants validates the Sprint 57.49 design principle: 1 backend endpoint = 1 query namespace = many UI surfaces.
