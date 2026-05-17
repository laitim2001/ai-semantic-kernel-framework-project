/**
 * File: frontend/src/features/loops/hooks/useActiveLoops.ts
 * Purpose: TanStack Query hook for active loops list (Overview page ACTIVE_LOOPS widget).
 * Category: Frontend / loops / hooks
 * Scope: Phase 57 / Sprint 57.19 Day 3 / US-C1
 *
 * Description:
 *   Wraps GET /api/v1/loops?status=running. Refreshes every 10 s so the
 *   Overview ACTIVE_LOOPS widget stays live without manual reload.
 *
 * Created: 2026-05-17 (Sprint 57.19 Day 3 / US-C1)
 *
 * Modification History (newest-first):
 *   - 2026-05-17: Initial creation (Sprint 57.19 Day 3 / US-C1)
 *
 * Related:
 *   - ../services/loopsService.ts
 *   - ../types.ts (LoopsPage)
 *   - ../../../pages/overview/OverviewPage.tsx (consumer)
 */

import { useQuery } from "@tanstack/react-query";

import { fetchLoops } from "../services/loopsService";
import type { LoopsPage } from "../types";

export const LOOPS_LIST_QUERY_KEY_BASE = ["loops", "list"] as const;

export function useActiveLoops(limit = 10) {
  return useQuery<LoopsPage, Error>({
    queryKey: [...LOOPS_LIST_QUERY_KEY_BASE, "running", limit],
    queryFn: ({ signal }) => fetchLoops({ status: "running", limit }, signal),
    refetchInterval: 10_000,
    staleTime: 5_000,
  });
}
