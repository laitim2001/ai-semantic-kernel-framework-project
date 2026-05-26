/**
 * File: frontend/src/features/tenant-settings/hooks/useFeatureFlags.ts
 * Purpose: TanStack Query hook for /admin/tenants/{id}/feature-flags (Sprint 57.48 Track B).
 * Category: Frontend / tenant-settings / hooks
 * Scope: Phase 57 / Sprint 57.49 Day 1 (Track A 1.1.2)
 *
 * Created: 2026-05-26 (Sprint 57.49 Day 1)
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Initial creation (Sprint 57.49 Day 1)
 *
 * Related:
 *   - ../services/tenantSettingsService.ts (fetchFeatureFlags)
 *   - ../components/tabs/FeatureFlagsTab.tsx (consumer)
 */

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { fetchFeatureFlags } from "../services/tenantSettingsService";
import type { FeatureFlagListResponse } from "../types";

export const FEATURE_FLAGS_QUERY_KEY_BASE = ["tenant-settings", "feature-flags"] as const;

export function useFeatureFlags(tenantId: string) {
  return useQuery<FeatureFlagListResponse, Error>({
    queryKey: [...FEATURE_FLAGS_QUERY_KEY_BASE, tenantId],
    queryFn: ({ signal }) => fetchFeatureFlags(tenantId, undefined, undefined, signal),
    enabled: Boolean(tenantId),
    placeholderData: keepPreviousData,
  });
}
