/**
 * File: frontend/tests/unit/components/PageHead.test.tsx
 * Purpose: Vitest spec for <PageHead> primitive (Sprint 57.24 US-B1).
 * Category: Frontend / tests / unit / components
 * Scope: Phase 57 / Sprint 57.24 Day 1 US-B1
 *
 * Modification History:
 *   - 2026-05-19: Initial creation (Sprint 57.24 Day 1 US-B1)
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PageHead } from "@/components/ui/PageHead";

describe("<PageHead>", () => {
  it("renders required title + subtitle", () => {
    render(<PageHead title="Cost Ledger" subtitle="Token + tool spend" />);
    expect(screen.getByText("Cost Ledger")).toBeInTheDocument();
    expect(screen.getByText("Token + tool spend")).toBeInTheDocument();
  });

  it("renders optional routePath inline as a pill", () => {
    render(
      <PageHead title="Cost Ledger" subtitle="sub" routePath="/cost-dashboard" />,
    );
    expect(screen.getByText("/cost-dashboard")).toBeInTheDocument();
  });

  it("renders optional badges slot for admin / scope markers", () => {
    render(
      <PageHead
        title="Cost Ledger"
        subtitle="sub"
        badges={<span data-testid="admin-badge">admin scope</span>}
      />,
    );
    expect(screen.getByTestId("admin-badge")).toBeInTheDocument();
  });

  it("renders optional actions slot (page-actions row)", () => {
    render(
      <PageHead
        title="Cost Ledger"
        subtitle="sub"
        actions={
          <>
            <button type="button">By tenant</button>
            <button type="button">CSV</button>
          </>
        }
      />,
    );
    expect(screen.getByRole("button", { name: "By tenant" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "CSV" })).toBeInTheDocument();
  });

  it("omits actions wrapper when actions prop is not provided", () => {
    const { container } = render(<PageHead title="t" subtitle="s" />);
    // Title section is always rendered; actions wrapper is a sibling div — verify only 1 direct child
    expect(container.firstElementChild?.children).toHaveLength(1);
  });
});
