/**
 * File: frontend/tests/unit/sla-dashboard/LatencyChart.test.tsx
 * Purpose: Vitest spec for <LatencyChart> (Sprint 57.25 Day 1 US-B3).
 * Category: Frontend / tests / unit / sla-dashboard
 * Scope: Phase 57 / Sprint 57.25 Day 1 US-B3
 *
 * Modification History:
 *   - 2026-05-19: Initial creation (Sprint 57.25 Day 1 US-B3)
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LatencyChart } from "@/features/sla-dashboard/components/LatencyChart";

describe("<LatencyChart>", () => {
  it("renders an SVG with 3 series paths (p50 / p95 / p99)", () => {
    render(<LatencyChart />);
    const svg = screen.getByTestId("sla-latency-chart");
    expect(svg.tagName.toLowerCase()).toBe("svg");
    expect(screen.getByTestId("sla-latency-chart-series-p50")).toBeInTheDocument();
    expect(screen.getByTestId("sla-latency-chart-series-p95")).toBeInTheDocument();
    expect(screen.getByTestId("sla-latency-chart-series-p99")).toBeInTheDocument();
  });

  it("renders 5 x-axis tick labels (every 6h over 24h)", () => {
    render(<LatencyChart />);
    [0, 12, 24, 36, 47].forEach((i) => {
      expect(screen.getByTestId(`sla-latency-chart-x-tick-${i}`)).toBeInTheDocument();
    });
  });

  it("renders 4 y-axis tick labels (0 / 0.25 / 0.5 / 0.75 normalized)", () => {
    render(<LatencyChart />);
    [0, 0.25, 0.5, 0.75].forEach((t) => {
      expect(screen.getByTestId(`sla-latency-chart-y-tick-${t}`)).toBeInTheDocument();
    });
  });

  it("renders p50 with stronger stroke (1.8) than p95/p99 (1.4) per mockup hierarchy", () => {
    render(<LatencyChart />);
    const p50 = screen.getByTestId("sla-latency-chart-series-p50");
    const p95 = screen.getByTestId("sla-latency-chart-series-p95");
    const p99 = screen.getByTestId("sla-latency-chart-series-p99");
    expect(p50.getAttribute("stroke-width")).toBe("1.8");
    expect(p95.getAttribute("stroke-width")).toBe("1.4");
    expect(p99.getAttribute("stroke-width")).toBe("1.4");
  });

  it("p99 series has reduced opacity 0.9 per mockup", () => {
    render(<LatencyChart />);
    const p99 = screen.getByTestId("sla-latency-chart-series-p99");
    expect(p99.getAttribute("opacity")).toBe("0.9");
  });
});
