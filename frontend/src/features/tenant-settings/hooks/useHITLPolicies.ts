/**
 * File: frontend/src/features/tenant-settings/hooks/useHITLPolicies.ts
 * Purpose: TanStack Query hook for /admin/tenants/{id}/hitl-policies (Sprint 57.48 Track A).
 * Category: Frontend / tenant-settings / hooks
 * Scope: Phase 57 / Sprint 57.49 Day 1 (Track A 1.1.4)
 *
 * Created: 2026-05-26 (Sprint 57.49 Day 1)
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Initial creation (Sprint 57.49 Day 1)
 *
 * Related:
 *   - ../services/tenantSettingsService.ts (fetchHITLPolicies)
 *   - ../components/tabs/HITLPoliciesTab.tsx (consumer)
 */

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { fetchHITLPolicies } from "../services/tenantSettingsService";
import type { HITLPolicyListResponse } from "../types";

export const HITL_POLICIES_QUERY_KEY_BASE = ["tenant-settings", "hitl-policies"] as const;

export function useHITLPolicies(tenantId: string) {
  return useQuery<HITLPolicyListResponse, Error>({
    queryKey: [...HITL_POLICIES_QUERY_KEY_BASE, tenantId],
    queryFn: ({ signal }) => fetchHITLPolicies(tenantId, undefined, undefined, signal),
    enabled: Boolean(tenantId),
    placeholderData: keepPreviousData,
  });
}
