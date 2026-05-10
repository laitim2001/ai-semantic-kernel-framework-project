/**
 * File: frontend/src/features/memory/hooks/useMemoryByTime.ts
 * Purpose: TanStack Query hook for memory /by-time/{layer}/{time_scale} read (US-5 time-scale filter).
 * Category: Frontend / memory / hooks
 * Scope: Phase 57 / Sprint 57.12 Day 2 / US-3
 *
 * Description:
 *   Wraps `memoryService.fetchByTime`. Only meaningful for layer=user (backend
 *   returns 400 for other layers — that error surfaces via TanStack `error`).
 *   keepPreviousData for pagination.
 *
 * Created: 2026-05-10 (Sprint 57.12 Day 2 / US-3)
 *
 * Related:
 *   - ../services/memoryService.ts
 *   - ../components/MemoryRecentList.tsx (Day 3 consumer — time-scale dropdown variant)
 *   - ../types.ts
 */

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { memoryService } from "../services/memoryService";
import type { MemoryEntryPage, MemoryLayer, MemoryTimeScale } from "../types";

/** Single-source query key prefix for memory by-time queries. */
export const MEMORY_BY_TIME_QUERY_KEY_BASE = ["memory", "by-time"] as const;

export function useMemoryByTime(
  layer: MemoryLayer | null,
  timeScale: MemoryTimeScale | null,
  limit = 50,
  offset = 0,
) {
  return useQuery<MemoryEntryPage, Error>({
    queryKey: [...MEMORY_BY_TIME_QUERY_KEY_BASE, layer, timeScale, limit, offset],
    queryFn: ({ signal }) =>
      memoryService.fetchByTime(
        layer as MemoryLayer,
        timeScale as MemoryTimeScale,
        limit,
        offset,
        signal,
      ),
    enabled: layer !== null && timeScale !== null,
    placeholderData: keepPreviousData,
  });
}
