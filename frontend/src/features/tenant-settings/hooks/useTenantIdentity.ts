/**
 * File: frontend/src/features/tenant-settings/hooks/useTenantIdentity.ts
 * Purpose: TanStack Query hook for /admin/tenants/{id}/identity (Sprint 57.50).
 * Category: Frontend / tenant-settings / hooks
 * Scope: Phase 57 / Sprint 57.50 Day 1 (closes AD-TenantSettings-IdentityFixture-Cleanup)
 *
 * Created: 2026-05-26 (Sprint 57.50 Day 1)
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Initial creation (Sprint 57.50 Day 1)
 *
 * Related:
 *   - ../services/tenantSettingsService.ts (fetchTenantIdentity)
 *   - ../components/tabs/GeneralTab.tsx (consumer — Identity & SSO Card)
 */

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { fetchTenantIdentity } from "../services/tenantSettingsService";
import type { TenantIdentity } from "../types";

export const TENANT_IDENTITY_QUERY_KEY_BASE = ["tenant-settings", "identity"] as const;

export function useTenantIdentity(tenantId: string) {
  return useQuery<TenantIdentity, Error>({
    queryKey: [...TENANT_IDENTITY_QUERY_KEY_BASE, tenantId],
    queryFn: ({ signal }) => fetchTenantIdentity(tenantId, signal),
    enabled: Boolean(tenantId),
    placeholderData: keepPreviousData,
  });
}
