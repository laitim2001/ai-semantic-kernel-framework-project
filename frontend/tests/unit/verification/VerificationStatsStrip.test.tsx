/**
 * File: frontend/tests/unit/verification/VerificationStatsStrip.test.tsx
 * Purpose: Vitest coverage for VerificationStatsStrip — 4 KPI cards + Pass rate computation + AP-2 banner.
 * Category: Frontend / Tests / verification / unit
 * Scope: Phase 57 / Sprint 57.41 Day 2 (verification full mockup-fidelity rebuild)
 *
 * Description:
 *   - 4 KPI labels render in mockup order
 *     ("Pass rate · 1h" / "Claims · 1h" / "Failed · 1h" / "Median latency")
 *   - Pass rate falls back to "0.0" when items array is empty
 *   - Pass rate ≈ "66.7" when 2 of 3 items passed (real computation from items)
 *   - BackendGapBanner declares 3 fixture KPI status (AP-2)
 *
 * Created: 2026-05-25 (Sprint 57.41 Day 2)
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.41 Day 2)
 */

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { VerificationStatsStrip } from "@/features/verification/components/VerificationStatsStrip";
import type { VerificationLogItem } from "@/features/verification/types";

function makeItem(id: number, passed: boolean): VerificationLogItem {
  return {
    id,
    tenant_id: "11111111-1111-4111-8111-111111111111",
    session_id: "22222222-2222-4222-8222-222222222222",
    turn_index: 0,
    verifier_name: `verifier_${id}`,
    verifier_type: "rules_based",
    passed,
    score: passed ? 0.95 : 0.4,
    reason: passed ? null : "fail reason",
    suggested_correction: null,
    correction_attempt: 0,
    created_at_ms: Date.now() - id * 1000,
  };
}

describe("VerificationStatsStrip (Sprint 57.41)", () => {
  it("renders 4 KPI labels in mockup order and shows 0.0 Pass rate when empty", () => {
    render(<VerificationStatsStrip items={[]} />);
    expect(screen.getByText("Pass rate · 1h")).toBeInTheDocument();
    expect(screen.getByText("Claims · 1h")).toBeInTheDocument();
    expect(screen.getByText("Failed · 1h")).toBeInTheDocument();
    expect(screen.getByText("Median latency")).toBeInTheDocument();
    // Empty items → Pass rate fallback "0.0"
    expect(screen.getByText("0.0")).toBeInTheDocument();
  });

  it("computes Pass rate from 2 of 3 passed (≈ 66.7) and renders AP-2 banner", () => {
    render(
      <VerificationStatsStrip
        items={[makeItem(1, true), makeItem(2, true), makeItem(3, false)]}
      />,
    );
    expect(screen.getByText("66.7")).toBeInTheDocument();

    const banner = screen.getByTestId("backend-gap-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(/verification aggregation endpoint/i);
  });
});
