/**
 * File: frontend/tests/unit/pages/state-inspector/StateInspectorPage.test.tsx
 * Purpose: Vitest coverage for StateInspectorPage (US-C4) — KPI / chain / selection / diff / live backend.
 * Category: Frontend / Tests / pages / state-inspector
 * Scope: Phase 57 / Sprint 57.19 Day 4 / US-C4
 *
 * Created: 2026-05-17 (Sprint 57.19 Day 4 / US-C4)
 *
 * Modification History (newest-first):
 *   - 2026-05-17: Initial creation (Sprint 57.19 Day 4 / US-C4)
 */

import "@testing-library/jest-dom/vitest";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as stateService from "@/features/state/services/stateService";

vi.mock("@/components/AppShellV2", () => ({
  AppShellV2: ({ children, pageTitle }: { children: ReactNode; pageTitle: string }) => (
    <div data-testid="app-shell" data-page-title={pageTitle}>
      {children}
    </div>
  ),
}));

vi.mock("@/features/auth/components/RequireAuth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

import { StateInspectorPage } from "@/pages/state-inspector/StateInspectorPage";

function wrap(children: ReactNode, initialEntries: string[] = ["/state-inspector"]) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("StateInspectorPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders AppShellV2 pageTitle", () => {
    render(wrap(<StateInspectorPage />));
    expect(screen.getByTestId("app-shell")).toHaveAttribute("data-page-title", "State Inspector");
  });

  it("renders 4 KPI cards", () => {
    render(wrap(<StateInspectorPage />));
    expect(screen.getByText("Current version")).toBeInTheDocument();
    expect(screen.getByText("Transient size")).toBeInTheDocument();
    expect(screen.getByText("Durable bytes")).toBeInTheDocument();
    expect(screen.getByText("Pending approvals")).toBeInTheDocument();
  });

  it("renders all 10 version chain entries", () => {
    render(wrap(<StateInspectorPage />));
    // 10 mockup-fixture versions: v18..v9. Some labels (v18 selected, v17 parent)
    // appear multiple times across chain + current-state header + Stat; assert >= 1.
    for (const v of [18, 17, 16, 15, 14, 13, 12, 11, 10, 9]) {
      expect(screen.getAllByText(`v${v}`).length).toBeGreaterThanOrEqual(1);
    }
  });

  it("defaults to v18 selected (mockup default)", () => {
    render(wrap(<StateInspectorPage />));
    // v18 appears in both the chain entry AND the right-side current-state header
    expect(screen.getAllByText("v18").length).toBeGreaterThanOrEqual(2);
  });

  it("clicking v11 updates selected current-state header", async () => {
    const user = userEvent.setup();
    render(wrap(<StateInspectorPage />));
    // click v11 entry in chain
    await user.click(screen.getByText("v11"));
    // current-state header now should show v11 (count >= 2 — chain + header)
    expect(screen.getAllByText("v11").length).toBeGreaterThanOrEqual(2);
  });

  it("renders carryover banner about Cat 7 version-chain endpoint", () => {
    render(wrap(<StateInspectorPage />));
    expect(screen.getByRole("status")).toHaveTextContent(/version chain/i);
  });

  it("renders diff section with pre-formatted text", () => {
    render(wrap(<StateInspectorPage />));
    expect(screen.getByText(/durable\.pending_approval_ids/)).toBeInTheDocument();
    expect(screen.getByText(/transient\.token_usage_so_far/)).toBeInTheDocument();
  });

  it("calls fetchStateSnapshot when ?session_id=<uuid> provided", async () => {
    const spy = vi.spyOn(stateService, "fetchStateSnapshot").mockResolvedValue({
      session_id: "abc12345-aaaa-bbbb-cccc-ddddeeeeffff",
      tenant_id: "tenant-aaaa-bbbb",
      version: 42,
      parent_version: 41,
      turn_num: 42,
      state_data: { foo: "bar" },
      state_hash: "hash-v42",
      reason: "test",
    });
    render(wrap(<StateInspectorPage />, ["/state-inspector?session_id=abc12345-aaaa-bbbb-cccc-ddddeeeeffff"]));
    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith("abc12345-aaaa-bbbb-cccc-ddddeeeeffff", expect.anything());
    });
  });
});
