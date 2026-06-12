/**
 * File: frontend/src/features/tenant-settings/hooks/useHarnessPolicy.ts
 * Purpose: TanStack Query hook for GET /admin/tenants/{id}/harness-policy (Sprint 57.106 C3).
 * Category: Frontend / tenant-settings / hooks
 * Scope: Phase 57 / Sprint 57.106 C3 (Harness Policy tab read side)
 *
 * Created: 2026-06-12 (Sprint 57.106 C3)
 *
 * Modification History (newest-first):
 *   - 2026-06-12: Initial creation (Sprint 57.106 C3)
 *
 * Related:
 *   - ../services/tenantSettingsService.ts (getHarnessPolicy)
 *   - ../components/tabs/HarnessPolicyTab.tsx (consumer)
 *   - ./useModelPolicy.ts (read-side pattern authority)
 */

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { getHarnessPolicy } from "../services/tenantSettingsService";
import type { HarnessPolicy } from "../types";

export const HARNESS_POLICY_QUERY_KEY_BASE = ["tenant-settings", "harness-policy"] as const;

export function useHarnessPolicy(tenantId: string) {
  return useQuery<HarnessPolicy, Error>({
    queryKey: [...HARNESS_POLICY_QUERY_KEY_BASE, tenantId],
    queryFn: ({ signal }) => getHarnessPolicy(tenantId, signal),
    enabled: Boolean(tenantId),
    placeholderData: keepPreviousData,
  });
}
