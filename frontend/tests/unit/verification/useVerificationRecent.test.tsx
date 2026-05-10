/**
 * File: frontend/tests/unit/verification/useVerificationRecent.test.tsx
 * Purpose: Vitest tests for useVerificationRecent TanStack Query hook (Sprint 57.11 US-3).
 * Category: Frontend / tests / unit / verification
 * Scope: Phase 57 / Sprint 57.11 Day 2 / US-3
 *
 * Description:
 *   Mirror useAuditLog.test.tsx pattern (Sprint 57.9 US-4) — single-source
 *   QUERY_KEY_BASE export check + initial fetch happy path + error path.
 *   Per D-PRE-10 (Sprint 57.9): refetch test uses delta assertion to tolerate
 *   TanStack v5 internal mount-time refetches.
 *
 * Created: 2026-05-10 (Sprint 57.11 Day 2 / US-3)
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import {
  useVerificationRecent,
  VERIFICATION_RECENT_QUERY_KEY_BASE,
} from "@/features/verification/hooks/useVerificationRecent";
import { verificationService } from "@/features/verification/services/verificationService";
import type { VerificationLogPage } from "@/features/verification/types";

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

const SAMPLE_PAGE: VerificationLogPage = {
  items: [
    {
      id: 7,
      tenant_id: "11111111-1111-4111-8111-111111111111",
      session_id: "22222222-2222-4222-8222-222222222222",
      turn_index: 0,
      verifier_name: "pii_redaction",
      verifier_type: "rules_based",
      passed: true,
      score: 0.99,
      reason: null,
      suggested_correction: null,
      correction_attempt: 0,
      created_at_ms: Date.UTC(2026, 4, 10, 8, 0, 0),
    },
  ],
  total: 1,
  has_more: false,
  next_offset: null,
  page_size: 50,
};

describe("useVerificationRecent (Sprint 57.11 US-3)", () => {
  test("VERIFICATION_RECENT_QUERY_KEY_BASE is single-source ['verification', 'recent']", () => {
    expect(VERIFICATION_RECENT_QUERY_KEY_BASE).toEqual(["verification", "recent"]);
  });

  test("initial fetch returns verification page on success", async () => {
    const spy = vi
      .spyOn(verificationService, "fetchVerificationRecent")
      .mockResolvedValueOnce(SAMPLE_PAGE);

    const { result } = renderHook(() => useVerificationRecent({ limit: 50, offset: 0 }), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(spy).toHaveBeenCalledTimes(1);
    expect(result.current.data).toEqual(SAMPLE_PAGE);
    expect(result.current.error).toBeNull();
  });

  test("error state surfaces when service throws (e.g. 403 auditor RBAC)", async () => {
    vi.spyOn(verificationService, "fetchVerificationRecent").mockRejectedValueOnce(
      new Error("Audit role required"),
    );

    const { result } = renderHook(() => useVerificationRecent({ limit: 50, offset: 0 }), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("Audit role required");
    expect(result.current.data).toBeUndefined();
  });
});
