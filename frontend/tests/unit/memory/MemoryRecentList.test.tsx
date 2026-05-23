/**
 * File: frontend/tests/unit/memory/MemoryRecentList.test.tsx
 * Purpose: Vitest tests for MemoryRecentList — layer filter + table + pagination + empty + error retry.
 * Category: Frontend / tests / unit / memory
 * Scope: Phase 57 / Sprint 57.12 Day 2-3 / US-5
 *
 * Created: 2026-05-10 (Sprint 57.12 Day 2-3 / US-5)
 *
 * Modification History:
 *   - 2026-05-24: Sprint 57.33 Day 2 US-C3 — defensive spec: list survives backend payload with `items: undefined` (AD-Overview-PreExisting-Route-Crashes regression guard)
 *   - 2026-05-10: Initial creation (Sprint 57.12 Day 2-3 / US-5)
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { MemoryRecentList } from "@/features/memory/components/MemoryRecentList";
import { memoryService } from "@/features/memory/services/memoryService";
import type { MemoryEntryPage } from "@/features/memory/types";

function renderList() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRecentList />
    </QueryClientProvider>,
  );
}

const SAMPLE_PAGE: MemoryEntryPage = {
  items: [
    {
      id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      layer: "user",
      scope_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
      key: null,
      content: "Prefers concise responses",
      category: "preference",
      expires_at_ms: null,
      created_at_ms: Date.UTC(2026, 4, 10, 8, 0, 0),
      updated_at_ms: Date.UTC(2026, 4, 10, 8, 0, 0),
      tenant_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    },
  ],
  total: 1,
  has_more: false,
  next_offset: null,
  page_size: 50,
};

describe("MemoryRecentList (Sprint 57.12 US-5)", () => {
  test("renders table rows + layer badge after fetch success", async () => {
    vi.spyOn(memoryService, "fetchRecent").mockResolvedValue(SAMPLE_PAGE);
    renderList();
    await waitFor(() => expect(screen.getByTestId("memory-table")).toBeInTheDocument());
    expect(screen.getByTestId("memory-scope-badge-user")).toBeInTheDocument();
    expect(screen.getByText(/Prefers concise responses/i)).toBeInTheDocument();
  });

  test("pagination Prev disabled at offset 0", async () => {
    vi.spyOn(memoryService, "fetchRecent").mockResolvedValue(SAMPLE_PAGE);
    renderList();
    await waitFor(() => expect(screen.getByTestId("pagination-prev")).toBeInTheDocument());
    expect(screen.getByTestId("pagination-prev")).toBeDisabled();
    // has_more=false → Next disabled too
    expect(screen.getByTestId("pagination-next")).toBeDisabled();
  });

  test("empty state shown when no entries", async () => {
    vi.spyOn(memoryService, "fetchRecent").mockResolvedValue({
      ...SAMPLE_PAGE,
      items: [],
      total: 0,
    });
    renderList();
    await waitFor(() => expect(screen.getByText(/No memory entries in this layer/i)).toBeInTheDocument());
  });

  test("error state shows retry button (StrictMode-safe retryClicked)", async () => {
    // Stateful mock — reject until shouldFail is flipped (avoids TanStack v5
    // mount-time refetch count flakiness per Sprint 57.9 D-PRE-10).
    let shouldFail = true;
    vi.spyOn(memoryService, "fetchRecent").mockImplementation(async () => {
      if (shouldFail) throw new Error("Audit role required");
      return SAMPLE_PAGE;
    });
    renderList();
    await waitFor(() => expect(screen.getByTestId("error-retry")).toBeInTheDocument());
    expect(screen.getByText(/Audit role required/i)).toBeInTheDocument();
    shouldFail = false;
    fireEvent.click(screen.getByTestId("error-retry"));
    await waitFor(() => expect(screen.getByTestId("memory-table")).toBeInTheDocument());
  });

  test("changing layer dropdown triggers a new fetch with the selected layer", async () => {
    const spy = vi.spyOn(memoryService, "fetchRecent").mockResolvedValue(SAMPLE_PAGE);
    renderList();
    await waitFor(() => expect(screen.getByTestId("filter-layer")).toBeInTheDocument());
    fireEvent.change(screen.getByTestId("filter-layer"), { target: { value: "tenant" } });
    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({ layer: "tenant" }),
        expect.anything(),
      ),
    );
  });

  // FIX-Sprint-57-33 US-C3 (2026-05-24): regression guard for
  // AD-Overview-PreExisting-Route-Crashes — list must survive a backend payload
  // where the `items` field is missing/undefined. Prior code did
  // query.data.items.length and query.data.items.map without ?? [] fallback,
  // crashing with "Cannot read properties of undefined (reading 'length')".
  test("survives backend payload with items field missing (defensive guard)", async () => {
    vi.spyOn(memoryService, "fetchRecent").mockResolvedValue({
      // Intentional shape: items omitted. Cast through unknown — MemoryEntryPage
      // asserts items as non-optional but runtime can diverge.
      total: 0,
      has_more: false,
      next_offset: null,
      page_size: 50,
    } as unknown as MemoryEntryPage);
    expect(() => renderList()).not.toThrow();
    // The "no entries" empty state appears once the query resolves cleanly.
    await waitFor(() =>
      expect(screen.getByText(/No memory entries in this layer/i)).toBeInTheDocument(),
    );
  });
});
