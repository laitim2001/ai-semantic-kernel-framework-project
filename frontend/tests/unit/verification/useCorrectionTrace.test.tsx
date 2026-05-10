/**
 * File: frontend/tests/unit/verification/useCorrectionTrace.test.tsx
 * Purpose: Vitest tests for useCorrectionTrace TanStack Query hook (Sprint 57.11 US-3).
 * Category: Frontend / tests / unit / verification
 * Scope: Phase 57 / Sprint 57.11 Day 2 / US-3
 *
 * Description:
 *   Verifies enabled-gate pattern (sessionId=null skip fetch) + happy fetch
 *   when sessionId provided + BASE export.
 *
 * Created: 2026-05-10 (Sprint 57.11 Day 2 / US-3)
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import {
  CORRECTION_TRACE_QUERY_KEY_BASE,
  useCorrectionTrace,
} from "@/features/verification/hooks/useCorrectionTrace";
import { verificationService } from "@/features/verification/services/verificationService";
import type { CorrectionTraceResponse } from "@/features/verification/types";

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

const SAMPLE_TRACE: CorrectionTraceResponse = {
  session_id: "abc-123",
  entries: [],
};

describe("useCorrectionTrace (Sprint 57.11 US-3)", () => {
  test("CORRECTION_TRACE_QUERY_KEY_BASE is single-source ['verification', 'correction-trace']", () => {
    expect(CORRECTION_TRACE_QUERY_KEY_BASE).toEqual(["verification", "correction-trace"]);
  });

  test("enabled gate — sessionId null skips fetch (no service call)", async () => {
    const spy = vi.spyOn(verificationService, "fetchCorrectionTrace");

    const { result } = renderHook(() => useCorrectionTrace(null), {
      wrapper: makeWrapper(),
    });

    // Wait a tick to ensure no fetch fires
    await new Promise((r) => setTimeout(r, 50));
    expect(spy).not.toHaveBeenCalled();
    expect(result.current.fetchStatus).toBe("idle");
    expect(result.current.data).toBeUndefined();
  });

  test("fetches when sessionId provided", async () => {
    const spy = vi
      .spyOn(verificationService, "fetchCorrectionTrace")
      .mockResolvedValueOnce(SAMPLE_TRACE);

    const { result } = renderHook(() => useCorrectionTrace("abc-123"), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(spy).toHaveBeenCalledWith("abc-123", expect.any(AbortSignal));
    expect(result.current.data).toEqual(SAMPLE_TRACE);
  });
});
