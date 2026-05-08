/**
 * File: frontend/tests/unit/cost-dashboard/migrate.test.tsx
 * Purpose: Sprint 57.7 US-B3 migration regression tests for CostOverview.
 * Category: Frontend / tests / unit / cost-dashboard
 * Scope: Phase 57 / Sprint 57.7 Day 3 Tier 3
 *
 * Description:
 *   2 tests covering the AppShell + Tailwind migration (target +2 baseline):
 *   1. CostOverview wraps content in AppShell (header + main slot present)
 *   2. CostOverview renders without inline `style` attributes (no inline-style regression)
 *
 *   Existing 4 cost-dashboard Vitest tests (costService / costStore / MonthPicker)
 *   serve as the regression sentinel — they must continue passing post-migrate
 *   per V2 紀律 0 test deletion.
 *
 * Created: 2026-05-10 (Sprint 57.7 Day 3 Tier 3)
 */

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { CostOverview } from "../../../src/features/cost-dashboard/components/CostOverview";

function renderInRouter(initialPath = "/cost-dashboard") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <CostOverview />
    </MemoryRouter>,
  );
}

describe("CostOverview — Sprint 57.7 US-B3 migration", () => {
  it("renders inside AppShell (brand link + main slot heading visible)", () => {
    renderInRouter();
    // Brand link is the AppShell footprint; presence proves the wrap.
    expect(screen.getByRole("link", { name: "IPA Platform" })).toBeInTheDocument();
    // Page heading still rendered inside main slot.
    expect(
      screen.getByRole("heading", { level: 1, name: "Cost Dashboard" }),
    ).toBeInTheDocument();
  });

  it("page heading + h1 wrapper carry no inline style (Tailwind migration of CostOverview-owned JSX)", () => {
    renderInRouter();
    // Pre-migration: <div style={{ padding: "2rem" }}><h1>...</h1>... — h1's
    // outer wrapper carried inline style. Post-migration: AppShell + Tailwind
    // utilities. We check the heading + its parent + grandparent have no
    // inline style. Child components (MonthPicker / CostBreakdownTable) are
    // out of scope per V2 紀律 surgical change — their migration deferred.
    const heading = screen.getByRole("heading", { level: 1, name: "Cost Dashboard" });
    expect(heading.getAttribute("style")).toBeNull();
    expect(heading.parentElement?.getAttribute("style")).toBeNull();
    expect(heading.parentElement?.parentElement?.getAttribute("style")).toBeNull();
  });
});
