/**
 * File: frontend/tests/unit/components/StatCard.test.tsx
 * Purpose: Vitest spec for <StatCard> primitive (Sprint 57.24 US-B2).
 * Category: Frontend / tests / unit / components
 * Scope: Phase 57 / Sprint 57.24 Day 1 US-B2
 *
 * Modification History:
 *   - 2026-05-19: Initial creation (Sprint 57.24 Day 1 US-B2)
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatCard } from "@/components/charts/StatCard";

describe("<StatCard>", () => {
  it("renders required label + value", () => {
    render(<StatCard label="Spend · MTD" value="$2,847" />);
    expect(screen.getByText("Spend · MTD")).toBeInTheDocument();
    expect(screen.getByText("$2,847")).toBeInTheDocument();
  });

  it("renders optional unit alongside value", () => {
    render(<StatCard label="Tokens · MTD" value="14.2" unit="M" />);
    expect(screen.getByText("14.2")).toBeInTheDocument();
    expect(screen.getByText("M")).toBeInTheDocument();
  });

  it("renders delta with success tone when deltaDir='up'", () => {
    render(
      <StatCard label="Cache hit" value="38" unit="%" delta="+4pp" deltaDir="up" />,
    );
    const delta = screen.getByTestId("stat-delta");
    expect(delta).toBeInTheDocument();
    expect(delta).toHaveTextContent("+4pp");
    expect(delta.getAttribute("data-direction")).toBe("up");
    expect(delta.className).toContain("text-success");
  });

  it("renders delta with danger tone when deltaDir='down'", () => {
    render(
      <StatCard label="Spend" value="$2,847" delta="+8.4%" deltaDir="down" />,
    );
    const delta = screen.getByTestId("stat-delta");
    expect(delta.getAttribute("data-direction")).toBe("down");
    expect(delta.className).toContain("text-danger");
  });

  it("renders spark slot when provided", () => {
    render(
      <StatCard
        label="Spend"
        value="$2,847"
        spark={<span data-testid="custom-spark">spark</span>}
      />,
    );
    expect(screen.getByTestId("custom-spark")).toBeInTheDocument();
  });

  it("omits delta + spark when not provided", () => {
    render(<StatCard label="Plain" value="42" />);
    expect(screen.queryByTestId("stat-delta")).toBeNull();
    expect(screen.queryByTestId("spark")).toBeNull();
  });
});
