/**
 * File: frontend/tests/unit/memory/MemoryByScopeBrowser.test.tsx
 * Purpose: Vitest tests for MemoryByScopeBrowser — 5-layer cards + drill-in detail panel.
 * Category: Frontend / tests / unit / memory
 * Scope: Phase 57 / Sprint 57.12 Day 2-3 / US-5
 *
 * Created: 2026-05-10 (Sprint 57.12 Day 2-3 / US-5)
 *
 * Modification History:
 *   - 2026-05-10: Initial creation (Sprint 57.12 Day 2-3 / US-5)
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { MemoryByScopeBrowser } from "@/features/memory/components/MemoryByScopeBrowser";
import { memoryService } from "@/features/memory/services/memoryService";
import type { MemoryEntryPage } from "@/features/memory/types";

function renderBrowser() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryByScopeBrowser />
    </QueryClientProvider>,
  );
}

const SYSTEM_PAGE: MemoryEntryPage = {
  items: [
    {
      id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
      layer: "system",
      scope_id: null,
      key: "global_rule_1",
      content: "Always cite sources",
      category: "rule",
      expires_at_ms: null,
      created_at_ms: Date.UTC(2026, 4, 1, 0, 0, 0),
      updated_at_ms: Date.UTC(2026, 4, 1, 0, 0, 0),
      tenant_id: null,
    },
  ],
  total: 1,
  has_more: false,
  next_offset: null,
  page_size: 50,
};

describe("MemoryByScopeBrowser (Sprint 57.12 US-5)", () => {
  test("renders 5 layer cards; role + session disabled", () => {
    renderBrowser();
    expect(screen.getByTestId("layer-card-system")).toBeEnabled();
    expect(screen.getByTestId("layer-card-tenant")).toBeEnabled();
    expect(screen.getByTestId("layer-card-user")).toBeEnabled();
    expect(screen.getByTestId("layer-card-role")).toBeDisabled();
    expect(screen.getByTestId("layer-card-session")).toBeDisabled();
  });

  test("selecting system layer auto-queries + lists entries (no scope input needed)", async () => {
    vi.spyOn(memoryService, "fetchByScope").mockResolvedValue(SYSTEM_PAGE);
    renderBrowser();
    fireEvent.click(screen.getByTestId("layer-card-system"));
    await waitFor(() => expect(screen.getByTestId("scope-entries")).toBeInTheDocument());
    expect(screen.getByText(/Always cite sources/i)).toBeInTheDocument();
  });

  test("selecting user layer shows scope_id input; submitting triggers fetch", async () => {
    const spy = vi.spyOn(memoryService, "fetchByScope").mockResolvedValue({
      ...SYSTEM_PAGE,
      items: [],
      total: 0,
    });
    renderBrowser();
    fireEvent.click(screen.getByTestId("layer-card-user"));
    expect(screen.getByTestId("scope-id-input")).toBeInTheDocument();
    fireEvent.change(screen.getByTestId("scope-id-input"), {
      target: { value: "some-user-uuid" },
    });
    fireEvent.click(screen.getByTestId("scope-submit"));
    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith(
        "user",
        "some-user-uuid",
        expect.any(Number),
        expect.any(Number),
        expect.anything(),
      ),
    );
  });
});
