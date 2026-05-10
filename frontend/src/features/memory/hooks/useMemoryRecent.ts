/**
 * File: frontend/src/features/memory/hooks/useMemoryRecent.ts
 * Purpose: TanStack Query hook for paginated memory /recent read (US-5 recent tab).
 * Category: Frontend / memory / hooks
 * Scope: Phase 57 / Sprint 57.12 Day 2 / US-3
 *
 * Description:
 *   Wraps `memoryService.fetchRecent` with single-source query key + signal
 *   forwarding + keepPreviousData (pagination doesn't flash empty). No
 *   refetchInterval — memory entries change on agent-loop write, queried on demand.
 *
 * Created: 2026-05-10 (Sprint 57.12 Day 2 / US-3)
 *
 * Related:
 *   - ../services/memoryService.ts
 *   - ../components/MemoryRecentList.tsx (Day 3 consumer)
 *   - ../types.ts
 */

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { memoryService } from "../services/memoryService";
import type { MemoryEntryPage, MemoryRecentFilter } from "../types";

/**
 * Single-source query key prefix for memory recent queries. Exported so a
 * future invalidation hook (Phase 58+ memory purge) can invalidate ALL
 * layer + pagination combinations without enumerating each.
 */
export const MEMORY_RECENT_QUERY_KEY_BASE = ["memory", "recent"] as const;

export function useMemoryRecent(filter: MemoryRecentFilter) {
  return useQuery<MemoryEntryPage, Error>({
    queryKey: [...MEMORY_RECENT_QUERY_KEY_BASE, filter],
    queryFn: ({ signal }) => memoryService.fetchRecent(filter, signal),
    placeholderData: keepPreviousData,
  });
}
