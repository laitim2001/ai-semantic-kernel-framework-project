/**
 * File: frontend/tests/unit/sla-dashboard/ErrorRateByServiceCard.test.tsx
 * Purpose: Vitest spec for <ErrorRateByServiceCard> (Sprint 57.25 Day 2 US-C3).
 * Category: Frontend / tests / unit / sla-dashboard
 * Scope: Phase 57 / Sprint 57.25 Day 2 US-C3
 *
 * Modification History:
 *   - 2026-05-19: Initial creation (Sprint 57.25 Day 2 US-C3)
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ErrorRateByServiceCard } from "@/features/sla-dashboard/components/ErrorRateByServiceCard";

describe("<ErrorRateByServiceCard>", () => {
  it("renders 6 fixture service rows mockup-faithful", () => {
    render(<ErrorRateByServiceCard />);
    expect(screen.getByTestId("sla-error-rate-card")).toBeInTheDocument();
    [0, 1, 2, 3, 4, 5].forEach((idx) => {
      expect(screen.getByTestId(`sla-error-rate-row-${idx}`)).toBeInTheDocument();
    });
  });

  it("renders warning tone on rate > 0.5 (tool.runner 0.6)", () => {
    render(<ErrorRateByServiceCard />);
    // Row 1 = tool.runner with rate 0.6 → warning text
    expect(screen.getByTestId("sla-error-rate-pct-1").className).toContain("text-warning");
  });

  it("renders muted tone when rate <= 0.5", () => {
    render(<ErrorRateByServiceCard />);
    // Row 0 = inference.adapter rate 0.04 → muted
    expect(screen.getByTestId("sla-error-rate-pct-0").className).toContain("text-fg-muted");
    // Row 5 = webhook.dispatcher rate 0.4 → still <= 0.5 → muted
    expect(screen.getByTestId("sla-error-rate-pct-5").className).toContain("text-fg-muted");
  });

  it("renders BackendGapBanner declaring per-service error rate gap (AP-2 honesty)", () => {
    render(<ErrorRateByServiceCard />);
    const banner = screen.getByTestId("backend-gap-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(/per-service/i);
  });
});
