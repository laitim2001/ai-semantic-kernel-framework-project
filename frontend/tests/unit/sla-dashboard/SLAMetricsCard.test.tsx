/**
 * File: frontend/tests/unit/sla-dashboard/SLAMetricsCard.test.tsx
 * Purpose: Unit test for SLAMetricsCard — pass-fail color rule + null value.
 * Category: Frontend / tests / unit / sla-dashboard
 * Scope: Phase 57 / Sprint 57.1 US-3
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 2)
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SLAMetricsCard } from "../../../src/features/sla-dashboard/components/SLAMetricsCard";

describe("SLAMetricsCard", () => {
  it("renders PASS when gte mode value >= threshold (availability 99.7% ≥ 99.5%)", () => {
    render(<SLAMetricsCard label="Availability" value={99.7} threshold={99.5} unit="%" mode="gte" />);
    expect(screen.getByText(/PASS/)).toBeInTheDocument();
    expect(screen.getByText("99.7%")).toBeInTheDocument();
  });

  it("renders FAIL when gte mode value < threshold (availability 99.0% < 99.5%)", () => {
    render(<SLAMetricsCard label="Availability" value={99.0} threshold={99.5} unit="%" mode="gte" />);
    expect(screen.getByText(/FAIL/)).toBeInTheDocument();
  });

  it("renders PASS when lte mode value <= threshold (latency 850 ≤ 1000)", () => {
    render(<SLAMetricsCard label="API p99" value={850} threshold={1000} unit="ms" mode="lte" />);
    expect(screen.getByText(/PASS/)).toBeInTheDocument();
  });

  it("renders FAIL when lte mode value > threshold (latency 1500 > 1000)", () => {
    render(<SLAMetricsCard label="API p99" value={1500} threshold={1000} unit="ms" mode="lte" />);
    expect(screen.getByText(/FAIL/)).toBeInTheDocument();
  });

  it("renders 'no data' when value is null", () => {
    render(<SLAMetricsCard label="API p99" value={null} threshold={1000} unit="ms" mode="lte" />);
    expect(screen.getByText(/no data/)).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
