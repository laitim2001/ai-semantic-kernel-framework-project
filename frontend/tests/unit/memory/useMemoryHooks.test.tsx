/**
 * File: frontend/tests/unit/memory/useMemoryHooks.test.tsx
 * Purpose: Vitest tests for 3 memory TanStack Query hooks — single-source QUERY_KEY_BASE + fetch + error + enabled gating.
 * Category: Frontend / tests / unit / memory
 * Scope: Phase 57 / Sprint 57.12 Day 2 / US-3
 *
 * Created: 2026-05-10 (Sprint 57.12 Day 2 / US-3)
 *
 * Modification History:
 *   - 2026-05-10: Initial creation (Sprint 57.12 Day 2 / US-3)
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";

import {
  MEMORY_BY_TIME_QUERY_KEY_BASE,
  useMemoryByTime,
} from "@/features/memory/hooks/useMemoryByTime";
import {
  MEMORY_RECENT_QUERY_KEY_BASE,
  useMemoryRecent,
} from "@/features/memory/hooks/useMemoryRecent";
import {
  MEMORY_SCOPE_QUERY_KEY_BASE,
  useMemoryByScope,
} from "@/features/memory/hooks/useMemoryByScope";
import { memoryService } from "@/features/memory/services/memoryService";
import type { MemoryEntryPage } from "@/features/memory/types";

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

const SAMPLE_PAGE: MemoryEntryPage = {
  items: [
    {
      id: "33333333-3333-4333-8333-333333333333",
      layer: "user",
      scope_id: "44444444-4444-4444-8444-444444444444",
      key: null,
      content: "User prefers dark mode",
      category: "preference",
      expires_at_ms: null,
      created_at_ms: Date.UTC(2026, 4, 10, 8, 0, 0),
      updated_at_ms: Date.UTC(2026, 4, 10, 8, 0, 0),
      tenant_id: "55555555-5555-4555-8555-555555555555",
    },
  ],
  total: 1,
  has_more: false,
  next_offset: null,
  page_size: 50,
};

describe("memory hooks single-source query keys (Sprint 57.12 US-3)", () => {
  test("MEMORY_RECENT_QUERY_KEY_BASE === ['memory', 'recent']", () => {
    expect(MEMORY_RECENT_QUERY_KEY_BASE).toEqual(["memory", "recent"]);
  });
  test("MEMORY_SCOPE_QUERY_KEY_BASE === ['memory', 'scope']", () => {
    expect(MEMORY_SCOPE_QUERY_KEY_BASE).toEqual(["memory", "scope"]);
  });
  test("MEMORY_BY_TIME_QUERY_KEY_BASE === ['memory', 'by-time']", () => {
    expect(MEMORY_BY_TIME_QUERY_KEY_BASE).toEqual(["memory", "by-time"]);
  });
});

describe("useMemoryRecent (Sprint 57.12 US-3)", () => {
  test("initial fetch returns page on success", async () => {
    const spy = vi.spyOn(memoryService, "fetchRecent").mockResolvedValueOnce(SAMPLE_PAGE);
    const { result } = renderHook(() => useMemoryRecent({ layer: "user", limit: 50, offset: 0 }), {
      wrapper: makeWrapper(),
    });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(spy).toHaveBeenCalledTimes(1);
    expect(result.current.data).toEqual(SAMPLE_PAGE);
  });

  test("error state surfaces on 403", async () => {
    vi.spyOn(memoryService, "fetchRecent").mockRejectedValueOnce(new Error("Audit role required"));
    const { result } = renderHook(() => useMemoryRecent({ layer: "user", limit: 50, offset: 0 }), {
      wrapper: makeWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("Audit role required");
  });
});

describe("useMemoryByScope (Sprint 57.12 US-3)", () => {
  test("disabled (no fetch) when layer or scopeId is null", async () => {
    const spy = vi.spyOn(memoryService, "fetchByScope").mockResolvedValueOnce(SAMPLE_PAGE);
    const { result } = renderHook(() => useMemoryByScope(null, null), { wrapper: makeWrapper() });
    // enabled:false → query stays in pending without ever calling the fetcher
    await new Promise((r) => setTimeout(r, 10));
    expect(spy).not.toHaveBeenCalled();
    expect(result.current.fetchStatus).toBe("idle");
  });

  test("fetches when both layer + scopeId present", async () => {
    const spy = vi.spyOn(memoryService, "fetchByScope").mockResolvedValueOnce(SAMPLE_PAGE);
    const { result } = renderHook(() => useMemoryByScope("user", "some-uuid"), {
      wrapper: makeWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(spy).toHaveBeenCalledTimes(1);
    expect(result.current.data).toEqual(SAMPLE_PAGE);
  });
});

describe("useMemoryByTime (Sprint 57.12 US-3)", () => {
  test("disabled when timeScale is null", async () => {
    const spy = vi.spyOn(memoryService, "fetchByTime").mockResolvedValueOnce(SAMPLE_PAGE);
    renderHook(() => useMemoryByTime("user", null), { wrapper: makeWrapper() });
    await new Promise((r) => setTimeout(r, 10));
    expect(spy).not.toHaveBeenCalled();
  });

  test("fetches when layer + timeScale present", async () => {
    const spy = vi.spyOn(memoryService, "fetchByTime").mockResolvedValueOnce(SAMPLE_PAGE);
    const { result } = renderHook(() => useMemoryByTime("user", "permanent"), {
      wrapper: makeWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(spy).toHaveBeenCalledTimes(1);
  });
});
