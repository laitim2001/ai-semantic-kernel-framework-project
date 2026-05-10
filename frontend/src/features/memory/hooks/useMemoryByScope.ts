/**
 * File: frontend/src/features/memory/hooks/useMemoryByScope.ts
 * Purpose: TanStack Query hook for memory /scope/{layer}/{scope_id} read (US-5 by-scope tab drill-in).
 * Category: Frontend / memory / hooks
 * Scope: Phase 57 / Sprint 57.12 Day 2 / US-3
 *
 * Description:
 *   Wraps `memoryService.fetchByScope`. `enabled` gates the query until both
 *   layer + scopeId are present (by-scope tab drills in only after the user
 *   picks a layer card + scope_id). keepPreviousData for pagination.
 *
 * Created: 2026-05-10 (Sprint 57.12 Day 2 / US-3)
 *
 * Related:
 *   - ../services/memoryService.ts
 *   - ../components/MemoryByScopeBrowser.tsx (Day 3 consumer)
 *   - ../types.ts
 */

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { memoryService } from "../services/memoryService";
import type { MemoryEntryPage, MemoryLayer } from "../types";

/** Single-source query key prefix for memory by-scope queries. */
export const MEMORY_SCOPE_QUERY_KEY_BASE = ["memory", "scope"] as const;

export function useMemoryByScope(
  layer: MemoryLayer | null,
  scopeId: string | null,
  limit = 50,
  offset = 0,
) {
  return useQuery<MemoryEntryPage, Error>({
    queryKey: [...MEMORY_SCOPE_QUERY_KEY_BASE, layer, scopeId, limit, offset],
    queryFn: ({ signal }) =>
      memoryService.fetchByScope(layer as MemoryLayer, scopeId as string, limit, offset, signal),
    enabled: layer !== null && scopeId !== null && scopeId.trim() !== "",
    placeholderData: keepPreviousData,
  });
}
