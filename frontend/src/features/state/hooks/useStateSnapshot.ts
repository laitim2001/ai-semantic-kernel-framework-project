/**
 * File: frontend/src/features/state/hooks/useStateSnapshot.ts
 * Purpose: TanStack Query hook for latest state snapshot (US-C4 consumer).
 * Category: Frontend / state / hooks
 * Scope: Phase 57 / Sprint 57.19 Day 4 / US-C4
 *
 * Created: 2026-05-17 (Sprint 57.19 Day 4 / US-C4)
 *
 * Modification History (newest-first):
 *   - 2026-05-17: Initial creation (Sprint 57.19 Day 4 / US-C4)
 *
 * Related:
 *   - ../services/stateService.ts
 *   - ../types.ts
 */

import { useQuery } from "@tanstack/react-query";

import { fetchStateSnapshot } from "../services/stateService";
import type { StateSnapshot } from "../types";

export const STATE_SNAPSHOT_QUERY_KEY_BASE = ["state", "snapshot"] as const;

export function useStateSnapshot(sessionId: string | null) {
  return useQuery<StateSnapshot, Error>({
    queryKey: [...STATE_SNAPSHOT_QUERY_KEY_BASE, sessionId ?? ""],
    queryFn: ({ signal }) => fetchStateSnapshot(sessionId as string, signal),
    enabled: Boolean(sessionId),
    staleTime: 5_000,
  });
}
