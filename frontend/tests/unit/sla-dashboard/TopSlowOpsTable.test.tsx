/**
 * File: frontend/tests/unit/sla-dashboard/TopSlowOpsTable.test.tsx
 * Purpose: Vitest spec for <TopSlowOpsTable> (Sprint 57.25 Day 2 US-C2).
 * Category: Frontend / tests / unit / sla-dashboard
 * Scope: Phase 57 / Sprint 57.25 Day 2 US-C2
 *
 * Modification History:
 *   - 2026-05-19: Initial creation (Sprint 57.25 Day 2 US-C2)
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TopSlowOpsTable } from "@/features/sla-dashboard/components/TopSlowOpsTable";

describe("<TopSlowOpsTable>", () => {
  it("renders 6 fixture rows mockup-faithful", () => {
    render(<TopSlowOpsTable />);
    expect(screen.getByTestId("sla-slow-ops-table")).toBeInTheDocument();
    [0, 1, 2, 3, 4, 5].forEach((idx) => {
      expect(screen.getByTestId(`sla-slow-ops-row-${idx}`)).toBeInTheDocument();
    });
  });

  it("renders Kind Badge with mockup-faithful tone per kind", () => {
    render(<TopSlowOpsTable />);
    // Row 0 = tool, Row 2 = loop, Row 3 = subagent, Row 4 = verify, Row 5 = memory
    expect(screen.getByTestId("sla-slow-ops-kind-0").getAttribute("data-kind")).toBe("tool");
    expect(screen.getByTestId("sla-slow-ops-kind-2").getAttribute("data-kind")).toBe("loop");
    expect(screen.getByTestId("sla-slow-ops-kind-3").getAttribute("data-kind")).toBe("subagent");
    expect(screen.getByTestId("sla-slow-ops-kind-4").getAttribute("data-kind")).toBe("verify");
    expect(screen.getByTestId("sla-slow-ops-kind-5").getAttribute("data-kind")).toBe("memory");
  });

  it("p99 column renders warning color when > 3000ms", () => {
    render(<TopSlowOpsTable />);
    // Row 0 p99=4400 > 3000 → warning
    expect(screen.getByTestId("sla-slow-ops-p99-0").className).toContain("text-warning");
    // Row 1 p99=5200 > 3000 → warning
    expect(screen.getByTestId("sla-slow-ops-p99-1").className).toContain("text-warning");
    // Row 2 p99=4100 > 3000 → warning
    expect(screen.getByTestId("sla-slow-ops-p99-2").className).toContain("text-warning");
  });

  it("p99 column renders muted color when <= 3000ms", () => {
    render(<TopSlowOpsTable />);
    // Row 3 p99=220 <= 3000 → fg-muted
    expect(screen.getByTestId("sla-slow-ops-p99-3").className).toContain("text-fg-muted");
    // Row 4 p99=180 → fg-muted
    expect(screen.getByTestId("sla-slow-ops-p99-4").className).toContain("text-fg-muted");
  });

  it("renders BackendGapBanner declaring cross-operation p99 gap (AP-2 honesty)", () => {
    render(<TopSlowOpsTable />);
    const banner = screen.getByTestId("backend-gap-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(/cross-operation/i);
  });
});
