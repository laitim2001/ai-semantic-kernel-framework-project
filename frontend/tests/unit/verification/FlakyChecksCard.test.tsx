/**
 * File: frontend/tests/unit/verification/FlakyChecksCard.test.tsx
 * Purpose: Vitest coverage for FlakyChecksCard — 3 fixture rows + AP-2 banner.
 * Category: Frontend / Tests / verification / unit
 * Scope: Phase 57 / Sprint 57.41 Day 2 (verification full mockup-fidelity rebuild)
 *
 * Description:
 *   - Card title "Flaky checks" renders
 *   - 3 fixture check names render in mockup order
 *     (claim_pii_redacted / source_in_allowlist / schema.action_items_have_owner)
 *   - BackendGapBanner declares AP-2 fixture status (aggregation endpoint pending)
 *
 * Created: 2026-05-25 (Sprint 57.41 Day 2)
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.41 Day 2)
 */

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FlakyChecksCard } from "@/features/verification/components/FlakyChecksCard";

describe("FlakyChecksCard (Sprint 57.41)", () => {
  it("renders Card title + 3 fixture rows + AP-2 BackendGapBanner", () => {
    render(<FlakyChecksCard />);

    expect(screen.getByText("Flaky checks")).toBeInTheDocument();

    expect(screen.getByText("claim_pii_redacted")).toBeInTheDocument();
    expect(screen.getByText("source_in_allowlist")).toBeInTheDocument();
    expect(screen.getByText("schema.action_items_have_owner")).toBeInTheDocument();

    const banner = screen.getByTestId("backend-gap-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(/Flaky checks aggregation endpoint pending/i);
  });
});
