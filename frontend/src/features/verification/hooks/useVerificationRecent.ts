/**
 * File: frontend/src/features/verification/hooks/useVerificationRecent.ts
 * Purpose: TanStack Query hook for paginated verification_log read (US-4 list page).
 * Category: Frontend / verification / hooks
 * Scope: Phase 57 / Sprint 57.11 Day 2 / US-3
 *
 * Description:
 *   Wraps `verificationService.fetchVerificationRecent` with:
 *   - `queryKey: [...VERIFICATION_RECENT_QUERY_KEY_BASE, filter]` — TanStack auto-refetches
 *     when any filter field changes (form submit produces new filter object → new key)
 *   - `signal` forwarded for auto-cancellation on stale query / unmount
 *   - `placeholderData: keepPreviousData` so paginating offset doesn't flash empty state
 *
 *   No refetchInterval — verification_log is append-only and queried on demand.
 *
 * Created: 2026-05-10 (Sprint 57.11 Day 2 / US-3)
 *
 * Related:
 *   - ../services/verificationService.ts
 *   - ../components/VerificationList.tsx (Day 3 consumer)
 *   - ../types.ts
 */

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { verificationService } from "../services/verificationService";
import type { VerificationLogFilter, VerificationLogPage } from "../types";

/**
 * Single-source query key prefix for verification recent queries. Exported so
 * a future invalidation hook (Phase 58+ retention purge) can invalidate ALL
 * filter combinations without enumerating each.
 */
export const VERIFICATION_RECENT_QUERY_KEY_BASE = ["verification", "recent"] as const;

export function useVerificationRecent(filter: VerificationLogFilter) {
  return useQuery<VerificationLogPage, Error>({
    queryKey: [...VERIFICATION_RECENT_QUERY_KEY_BASE, filter],
    queryFn: ({ signal }) => verificationService.fetchVerificationRecent(filter, signal),
    placeholderData: keepPreviousData,
  });
}
