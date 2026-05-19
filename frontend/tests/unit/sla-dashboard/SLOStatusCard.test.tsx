/**
 * File: frontend/tests/unit/sla-dashboard/SLOStatusCard.test.tsx
 * Purpose: Vitest spec for <SLOStatusCard> (Sprint 57.25 Day 2 US-C1).
 * Category: Frontend / tests / unit / sla-dashboard
 * Scope: Phase 57 / Sprint 57.25 Day 2 US-C1
 *
 * Modification History:
 *   - 2026-05-19: Initial creation (Sprint 57.25 Day 2 US-C1)
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SLOStatusCard } from "@/features/sla-dashboard/components/SLOStatusCard";

describe("<SLOStatusCard>", () => {
  it("renders all 5 SLO rows from mockup", () => {
    render(<SLOStatusCard data={null} />);
    const card = screen.getByTestId("sla-slo-card");
    expect(card).toBeInTheDocument();
    [0, 1, 2, 3, 4].forEach((idx) => {
      expect(screen.getByTestId(`sla-slo-row-${idx}`)).toBeInTheDocument();
    });
  });

  it("renders success dot when SLO ok and danger dot when failing", () => {
    render(<SLOStatusCard data={null} />);
    // Row 0 (Loop p95): current 1.84 < target 2.0 → ok
    expect(screen.getByTestId("sla-slo-dot-0").getAttribute("data-ok")).toBe("true");
    // Row 4 (Cost / run): current 0.052 > target 0.05 → failing
    expect(screen.getByTestId("sla-slo-dot-4").getAttribute("data-ok")).toBe("false");
  });

  it("failing SLO renders current value with danger color class", () => {
    render(<SLOStatusCard data={null} />);
    const failing = screen.getByTestId("sla-slo-current-4");
    expect(failing.className).toContain("text-danger");
  });

  it("ok SLO renders current value with muted color class", () => {
    render(<SLOStatusCard data={null} />);
    const ok = screen.getByTestId("sla-slo-current-0");
    expect(ok.className).toContain("text-fg-muted");
  });

  it("derives Loop p95 current from data.loop_simple_p99_ms when provided (proxy)", () => {
    const data = {
      tenant_id: "tenant_x",
      month: "2026-05",
      availability_pct: 99.9,
      api_p99_ms: 920,
      loop_simple_p99_ms: 1500, // → 1.5s (< 2s target → ok)
      loop_medium_p99_ms: null,
      loop_complex_p99_ms: null,
      hitl_queue_notif_p99_ms: null,
      violations_count: 0,
    };
    render(<SLOStatusCard data={data} />);
    const row0 = screen.getByTestId("sla-slo-current-0");
    expect(row0.textContent).toContain("1.5");
  });
});
