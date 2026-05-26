/**
 * File: frontend/tests/unit/tenant-settings/useSubResourceHooks.test.tsx
 * Purpose: Vitest coverage for 5 NEW Sprint 57.49 sub-resource hooks (Members/HITL/FF/Quotas/RateLimits).
 * Category: Frontend / Tests / tenant-settings / unit
 * Scope: Phase 57 / Sprint 57.49 Day 1 (Track A 1.1.x — fixture → real backend migration)
 *
 * Description:
 *   Verifies each of 5 NEW hooks (useTenantMembers / useHITLPolicies / useFeatureFlags
 *   / useQuotas / useRateLimits) honors the standard pattern:
 *   - QUERY_KEY_BASE is exported + correct namespace
 *   - `enabled: Boolean(tenantId)` short-circuit when empty
 *   - Service call on success returns the mock data
 *
 * Created: 2026-05-26 (Sprint 57.49 Day 1)
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Initial creation (Sprint 57.49 Day 1)
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import * as svc from "@/features/tenant-settings/services/tenantSettingsService";
import {
  TENANT_MEMBERS_QUERY_KEY_BASE,
  useTenantMembers,
} from "@/features/tenant-settings/hooks/useTenantMembers";
import {
  HITL_POLICIES_QUERY_KEY_BASE,
  useHITLPolicies,
} from "@/features/tenant-settings/hooks/useHITLPolicies";
import {
  FEATURE_FLAGS_QUERY_KEY_BASE,
  useFeatureFlags,
} from "@/features/tenant-settings/hooks/useFeatureFlags";
import {
  QUOTAS_QUERY_KEY_BASE,
  useQuotas,
} from "@/features/tenant-settings/hooks/useQuotas";
import {
  RATE_LIMITS_QUERY_KEY_BASE,
  useRateLimits,
} from "@/features/tenant-settings/hooks/useRateLimits";

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

describe("Sprint 57.49 — sub-resource hook QUERY_KEY_BASE namespacing", () => {
  test("TENANT_MEMBERS_QUERY_KEY_BASE = ['tenant-settings', 'members']", () => {
    expect(TENANT_MEMBERS_QUERY_KEY_BASE).toEqual(["tenant-settings", "members"]);
  });

  test("HITL_POLICIES_QUERY_KEY_BASE = ['tenant-settings', 'hitl-policies']", () => {
    expect(HITL_POLICIES_QUERY_KEY_BASE).toEqual(["tenant-settings", "hitl-policies"]);
  });

  test("FEATURE_FLAGS_QUERY_KEY_BASE = ['tenant-settings', 'feature-flags']", () => {
    expect(FEATURE_FLAGS_QUERY_KEY_BASE).toEqual(["tenant-settings", "feature-flags"]);
  });

  test("QUOTAS_QUERY_KEY_BASE = ['tenant-settings', 'quotas']", () => {
    expect(QUOTAS_QUERY_KEY_BASE).toEqual(["tenant-settings", "quotas"]);
  });

  test("RATE_LIMITS_QUERY_KEY_BASE = ['tenant-settings', 'rate-limits']", () => {
    expect(RATE_LIMITS_QUERY_KEY_BASE).toEqual(["tenant-settings", "rate-limits"]);
  });
});

describe("useTenantMembers (Sprint 57.49)", () => {
  test("disabled when tenantId is empty", async () => {
    const spy = vi.spyOn(svc, "fetchTenantMembers").mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    const { result } = renderHook(() => useTenantMembers(""), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.isFetching).toBe(false));
    expect(spy).not.toHaveBeenCalled();
  });

  test("fetches with tenantId + returns data on success", async () => {
    const payload = {
      items: [{ id: "u1", email: "a@b.com", display_name: "A", status: "active", created_at: "2026-01-01T00:00:00Z" }],
      total: 1,
      limit: 50,
      offset: 0,
    };
    vi.spyOn(svc, "fetchTenantMembers").mockResolvedValueOnce(payload);
    const { result } = renderHook(() => useTenantMembers("tenant-x"), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(payload);
  });
});

describe("useHITLPolicies (Sprint 57.49)", () => {
  test("disabled when tenantId is empty", async () => {
    const spy = vi.spyOn(svc, "fetchHITLPolicies").mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    const { result } = renderHook(() => useHITLPolicies(""), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.isFetching).toBe(false));
    expect(spy).not.toHaveBeenCalled();
  });

  test("fetches with tenantId + projects 4 risk rows on success", async () => {
    const payload = {
      items: [
        { risk: "CRITICAL", policy: "always_ask", sla_seconds: 300, reviewers: "@platform-l2" },
        { risk: "HIGH", policy: "always_ask", sla_seconds: 900, reviewers: "@platform-l2" },
        { risk: "MEDIUM", policy: "ask_once", sla_seconds: 3600, reviewers: "@platform-l1" },
        { risk: "LOW", policy: "auto", sla_seconds: null, reviewers: "" },
      ],
      total: 4,
      limit: 50,
      offset: 0,
    };
    vi.spyOn(svc, "fetchHITLPolicies").mockResolvedValueOnce(payload);
    const { result } = renderHook(() => useHITLPolicies("tenant-x"), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items).toHaveLength(4);
  });
});

describe("useFeatureFlags (Sprint 57.49)", () => {
  test("disabled when tenantId is empty", async () => {
    const spy = vi.spyOn(svc, "fetchFeatureFlags").mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    const { result } = renderHook(() => useFeatureFlags(""), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.isFetching).toBe(false));
    expect(spy).not.toHaveBeenCalled();
  });

  test("fetches with tenantId + exposes tenant-resolved boolean values", async () => {
    const payload = {
      items: [
        {
          name: "subagent.fork.enabled",
          value: true,
          default_enabled: true,
          overridden: false,
          description: "Allow concurrent fork mode",
          updated_at: "2026-05-26T00:00:00Z",
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    };
    vi.spyOn(svc, "fetchFeatureFlags").mockResolvedValueOnce(payload);
    const { result } = renderHook(() => useFeatureFlags("tenant-x"), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items[0]!.value).toBe(true);
  });
});

describe("useQuotas (Sprint 57.49)", () => {
  test("disabled when tenantId is empty", async () => {
    const spy = vi.spyOn(svc, "fetchQuotas").mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    const { result } = renderHook(() => useQuotas(""), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.isFetching).toBe(false));
    expect(spy).not.toHaveBeenCalled();
  });

  test("fetches and returns quotas with current_usage = null at admin layer", async () => {
    const payload = {
      items: [
        { resource: "tokens_per_day", limit: 10_000_000, unit: "tokens", period: "day", current_usage: null },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    };
    vi.spyOn(svc, "fetchQuotas").mockResolvedValueOnce(payload);
    const { result } = renderHook(() => useQuotas("tenant-x"), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items[0]!.current_usage).toBeNull();
  });
});

describe("useRateLimits (Sprint 57.49)", () => {
  test("disabled when tenantId is empty", async () => {
    const spy = vi.spyOn(svc, "fetchRateLimits").mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    });
    const { result } = renderHook(() => useRateLimits(""), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.isFetching).toBe(false));
    expect(spy).not.toHaveBeenCalled();
  });

  test("fetches and returns label/value pairs", async () => {
    const payload = {
      items: [
        { label: "API requests", value: "100 / min" },
        { label: "Tool calls", value: "1,000 / min" },
      ],
      total: 2,
      limit: 50,
      offset: 0,
    };
    vi.spyOn(svc, "fetchRateLimits").mockResolvedValueOnce(payload);
    const { result } = renderHook(() => useRateLimits("tenant-x"), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items).toHaveLength(2);
  });
});
