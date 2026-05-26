/**
 * File: frontend/tests/unit/tenant-settings/useHITLPoliciesSave.test.tsx
 * Purpose: Vitest coverage for Sprint 57.54 useHITLPoliciesSave mutation hook.
 * Category: Frontend / Tests / tenant-settings / unit
 * Scope: Phase 57 / Sprint 57.54 Track B
 *
 * Description:
 *   Verifies useHITLPoliciesSave mutation hook:
 *   - mutationFn calls saveHITLPolicies(tenantId, payload)
 *   - onSuccess invalidates [...HITL_POLICIES_QUERY_KEY_BASE, tenantId]
 *   - onError propagates Error from service rejection
 *
 * Created: 2026-05-26 (Sprint 57.54 Day 1)
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Initial creation (Sprint 57.54 Day 1 Track B)
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import * as svc from "@/features/tenant-settings/services/tenantSettingsService";
import { HITL_POLICIES_QUERY_KEY_BASE } from "@/features/tenant-settings/hooks/useHITLPolicies";
import { useHITLPoliciesSave } from "@/features/tenant-settings/hooks/useHITLPoliciesSave";
import type { HITLPolicyUpsertRequest, HITLPolicyUpsertResponse } from "@/features/tenant-settings/types";

const MOCK_PAYLOAD: HITLPolicyUpsertRequest = {
  auto_approve_max_risk: "LOW",
  require_approval_min_risk: "MEDIUM",
  reviewer_groups_by_risk: { HIGH: ["@platform-l1"], CRITICAL: ["@platform-l2"] },
  sla_seconds_by_risk: { HIGH: 900, CRITICAL: 300 },
};

const MOCK_RESPONSE: HITLPolicyUpsertResponse = {
  saved_policy: MOCK_PAYLOAD,
  items: [
    { risk: "LOW", policy: "auto", sla_seconds: null, reviewers: "" },
    { risk: "MEDIUM", policy: "ask_once", sla_seconds: null, reviewers: "" },
    { risk: "HIGH", policy: "always_ask", sla_seconds: 900, reviewers: "@platform-l1" },
    { risk: "CRITICAL", policy: "always_ask", sla_seconds: 300, reviewers: "@platform-l2" },
  ],
};

function makeWrapper(): {
  qc: QueryClient;
  wrapper: ({ children }: { children: ReactNode }) => JSX.Element;
} {
  const qc = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  return {
    qc,
    wrapper: ({ children }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    ),
  };
}

describe("Sprint 57.54 — useHITLPoliciesSave hook", () => {
  test("mutationFn invokes saveHITLPolicies(tenantId, payload) on mutate", async () => {
    const spy = vi.spyOn(svc, "saveHITLPolicies").mockResolvedValueOnce(MOCK_RESPONSE);
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useHITLPoliciesSave("tenant-x"), { wrapper });

    await act(async () => {
      result.current.mutate(MOCK_PAYLOAD);
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(spy).toHaveBeenCalledWith("tenant-x", MOCK_PAYLOAD);
    expect(result.current.data).toEqual(MOCK_RESPONSE);
  });

  test("onSuccess invalidates [...HITL_POLICIES_QUERY_KEY_BASE, tenantId]", async () => {
    vi.spyOn(svc, "saveHITLPolicies").mockResolvedValueOnce(MOCK_RESPONSE);
    const { qc, wrapper } = makeWrapper();
    const invalidateSpy = vi.spyOn(qc, "invalidateQueries");

    const { result } = renderHook(() => useHITLPoliciesSave("tenant-x"), { wrapper });

    await act(async () => {
      result.current.mutate(MOCK_PAYLOAD);
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: [...HITL_POLICIES_QUERY_KEY_BASE, "tenant-x"],
    });
  });

  test("propagates Error on service rejection", async () => {
    vi.spyOn(svc, "saveHITLPolicies").mockRejectedValueOnce(new Error("HTTP 422: invalid risk level"));
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useHITLPoliciesSave("tenant-x"), { wrapper });

    await act(async () => {
      result.current.mutate(MOCK_PAYLOAD);
    });
    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error?.message).toContain("invalid risk level");
  });
});
