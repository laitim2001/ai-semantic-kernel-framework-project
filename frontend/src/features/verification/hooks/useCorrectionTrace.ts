/**
 * File: frontend/src/features/verification/hooks/useCorrectionTrace.ts
 * Purpose: TanStack Query hook for full correction trace of one session.
 * Category: Frontend / verification / hooks
 * Scope: Phase 57 / Sprint 57.11 Day 2 / US-3
 *
 * Description:
 *   Wraps `verificationService.fetchCorrectionTrace` with:
 *   - `queryKey: [...CORRECTION_TRACE_QUERY_KEY_BASE, sessionId]` — per-session caching
 *   - `enabled: sessionId !== null` — gate when no sessionId selected (avoid 404 noise)
 *   - `signal` forwarded for auto-cancellation
 *
 * Created: 2026-05-10 (Sprint 57.11 Day 2 / US-3)
 *
 * Related:
 *   - ../services/verificationService.ts
 *   - ../components/CorrectionTraceView.tsx (Day 3 consumer)
 */

import { useQuery } from "@tanstack/react-query";

import { verificationService } from "../services/verificationService";
import type { CorrectionTraceResponse } from "../types";

/**
 * Single-source query key prefix for correction trace queries. Per-session
 * via the appended sessionId — invalidate single session via
 * [...BASE, sessionId] or all sessions via [...BASE] prefix.
 */
export const CORRECTION_TRACE_QUERY_KEY_BASE = ["verification", "correction-trace"] as const;

export function useCorrectionTrace(sessionId: string | null) {
  return useQuery<CorrectionTraceResponse, Error>({
    queryKey: [...CORRECTION_TRACE_QUERY_KEY_BASE, sessionId],
    queryFn: ({ signal }) => {
      if (sessionId === null) {
        // Should not fire because of `enabled` gate below; defensive throw.
        throw new Error("sessionId required");
      }
      return verificationService.fetchCorrectionTrace(sessionId, signal);
    },
    enabled: sessionId !== null,
  });
}
