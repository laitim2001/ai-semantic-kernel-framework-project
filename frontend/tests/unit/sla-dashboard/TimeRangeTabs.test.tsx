/**
 * File: frontend/tests/unit/sla-dashboard/TimeRangeTabs.test.tsx
 * Purpose: Vitest spec for <TimeRangeTabs> (Sprint 57.25 Day 1 US-B1).
 * Category: Frontend / tests / unit / sla-dashboard
 * Scope: Phase 57 / Sprint 57.25 Day 1 US-B1
 *
 * Modification History:
 *   - 2026-05-19: Initial creation (Sprint 57.25 Day 1 US-B1)
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TimeRangeTabs } from "@/features/sla-dashboard/components/TimeRangeTabs";

describe("<TimeRangeTabs>", () => {
  it("renders all 4 range tabs (1h / 24h / 7d / 30d)", () => {
    render(<TimeRangeTabs />);
    expect(screen.getByTestId("sla-range-tab-1h")).toBeInTheDocument();
    expect(screen.getByTestId("sla-range-tab-24h")).toBeInTheDocument();
    expect(screen.getByTestId("sla-range-tab-7d")).toBeInTheDocument();
    expect(screen.getByTestId("sla-range-tab-30d")).toBeInTheDocument();
  });

  it("defaults to 24h active per mockup-faithful default", () => {
    render(<TimeRangeTabs />);
    const t24h = screen.getByTestId("sla-range-tab-24h");
    expect(t24h.getAttribute("aria-selected")).toBe("true");
    const t1h = screen.getByTestId("sla-range-tab-1h");
    expect(t1h.getAttribute("aria-selected")).toBe("false");
  });

  it("changes active tab on click (local state; no refetch wired this sprint)", () => {
    render(<TimeRangeTabs />);
    fireEvent.click(screen.getByTestId("sla-range-tab-7d"));
    expect(screen.getByTestId("sla-range-tab-7d").getAttribute("aria-selected")).toBe("true");
    expect(screen.getByTestId("sla-range-tab-24h").getAttribute("aria-selected")).toBe("false");
  });

  it("renders role tablist with accessible label", () => {
    render(<TimeRangeTabs />);
    const tablist = screen.getByRole("tablist");
    expect(tablist).toBeInTheDocument();
    expect(tablist.getAttribute("aria-label")).toBeTruthy();
  });
});
