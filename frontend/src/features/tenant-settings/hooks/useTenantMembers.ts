/**
 * File: frontend/src/features/tenant-settings/hooks/useTenantMembers.ts
 * Purpose: TanStack Query hook for /admin/tenants/{id}/members (Sprint 57.47 endpoint).
 * Category: Frontend / tenant-settings / hooks
 * Scope: Phase 57 / Sprint 57.49 Day 1 (Track A + B shared hook)
 *
 * Description:
 *   Mirrors useTenantSettings pattern (`enabled: Boolean(tenantId)` + signal +
 *   keepPreviousData). Shared between TenantSettings MembersTab + AdminTenants
 *   TenantMembersDrawer (Sprint 57.49 Track B); same query key namespace so
 *   both views benefit from one cache entry per (tenant_id, limit, offset).
 *
 * Created: 2026-05-26 (Sprint 57.49 Day 1)
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Initial creation (Sprint 57.49 Day 1) — Track A + B shared hook
 *
 * Related:
 *   - ../services/tenantSettingsService.ts (fetchTenantMembers)
 *   - ../components/tabs/MembersTab.tsx (consumer)
 *   - frontend/src/features/admin-tenants/components/TenantMembersDrawer.tsx (consumer)
 */

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { fetchTenantMembers } from "../services/tenantSettingsService";
import type { TenantMemberListResponse } from "../types";

export const TENANT_MEMBERS_QUERY_KEY_BASE = ["tenant-settings", "members"] as const;

export function useTenantMembers(tenantId: string, limit?: number, offset?: number) {
  return useQuery<TenantMemberListResponse, Error>({
    queryKey: [...TENANT_MEMBERS_QUERY_KEY_BASE, tenantId, limit ?? 50, offset ?? 0],
    queryFn: ({ signal }) => fetchTenantMembers(tenantId, limit, offset, signal),
    enabled: Boolean(tenantId),
    placeholderData: keepPreviousData,
  });
}
