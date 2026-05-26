/**
 * File: frontend/src/features/tenant-settings/hooks/useQuotas.ts
 * Purpose: TanStack Query hook for /admin/tenants/{id}/quotas (Sprint 57.48 Track C).
 * Category: Frontend / tenant-settings / hooks
 * Scope: Phase 57 / Sprint 57.49 Day 1 (Track A 1.1.3 — combined w/ useRateLimits in QuotasTab)
 *
 * Created: 2026-05-26 (Sprint 57.49 Day 1)
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Initial creation (Sprint 57.49 Day 1)
 *
 * Related:
 *   - ../services/tenantSettingsService.ts (fetchQuotas)
 *   - ../components/tabs/QuotasTab.tsx (consumer)
 */

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { fetchQuotas } from "../services/tenantSettingsService";
import type { QuotaListResponse } from "../types";

export const QUOTAS_QUERY_KEY_BASE = ["tenant-settings", "quotas"] as const;

export function useQuotas(tenantId: string) {
  return useQuery<QuotaListResponse, Error>({
    queryKey: [...QUOTAS_QUERY_KEY_BASE, tenantId],
    queryFn: ({ signal }) => fetchQuotas(tenantId, undefined, undefined, signal),
    enabled: Boolean(tenantId),
    placeholderData: keepPreviousData,
  });
}
