/**
 * File: frontend/tests/unit/components/Spark.test.tsx
 * Purpose: Vitest spec for <Spark> sparkline primitive (Sprint 57.24 US-B2).
 * Category: Frontend / tests / unit / components
 * Scope: Phase 57 / Sprint 57.24 Day 1 US-B2
 *
 * Modification History:
 *   - 2026-05-19: Initial creation (Sprint 57.24 Day 1 US-B2)
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Spark } from "@/components/charts/Spark";

describe("<Spark>", () => {
  it("renders an SVG with a single path when given multiple points", () => {
    render(<Spark points={[1, 2, 3, 4, 5]} />);
    const svg = screen.getByTestId("spark");
    expect(svg.tagName.toLowerCase()).toBe("svg");
    expect(svg.querySelectorAll("path")).toHaveLength(1);
  });

  it("applies the tone prop as the stroke color", () => {
    render(<Spark points={[1, 2, 3]} tone="hsl(var(--memory))" />);
    const path = screen.getByTestId("spark").querySelector("path");
    expect(path?.getAttribute("stroke")).toBe("hsl(var(--memory))");
  });

  it("applies default width and height when not provided", () => {
    render(<Spark points={[1, 2, 3]} />);
    const svg = screen.getByTestId("spark");
    expect(svg.getAttribute("width")).toBe("90");
    expect(svg.getAttribute("height")).toBe("26");
  });

  it("honours custom width and height", () => {
    render(<Spark points={[1, 2]} width={120} height={32} />);
    const svg = screen.getByTestId("spark");
    expect(svg.getAttribute("width")).toBe("120");
    expect(svg.getAttribute("height")).toBe("32");
  });

  it("returns null when given an empty points array", () => {
    const { container } = render(<Spark points={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
