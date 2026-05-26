/**
 * File: frontend/src/features/tenant-settings/hooks/useRateLimits.ts
 * Purpose: TanStack Query hook for /admin/tenants/{id}/rate-limits (Sprint 57.48 Track D).
 * Category: Frontend / tenant-settings / hooks
 * Scope: Phase 57 / Sprint 57.49 Day 1 (Track A 1.1.3 — combined w/ useQuotas in QuotasTab)
 *
 * Created: 2026-05-26 (Sprint 57.49 Day 1)
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Initial creation (Sprint 57.49 Day 1)
 *
 * Related:
 *   - ../services/tenantSettingsService.ts (fetchRateLimits)
 *   - ../components/tabs/QuotasTab.tsx (consumer)
 */

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { fetchRateLimits } from "../services/tenantSettingsService";
import type { RateLimitListResponse } from "../types";

export const RATE_LIMITS_QUERY_KEY_BASE = ["tenant-settings", "rate-limits"] as const;

export function useRateLimits(tenantId: string) {
  return useQuery<RateLimitListResponse, Error>({
    queryKey: [...RATE_LIMITS_QUERY_KEY_BASE, tenantId],
    queryFn: ({ signal }) => fetchRateLimits(tenantId, undefined, undefined, signal),
    enabled: Boolean(tenantId),
    placeholderData: keepPreviousData,
  });
}
