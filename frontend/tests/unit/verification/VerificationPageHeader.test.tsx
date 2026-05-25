/**
 * File: frontend/tests/unit/verification/VerificationPageHeader.test.tsx
 * Purpose: Vitest coverage for VerificationPageHeader — title / sub / route-pill / 2 action buttons.
 * Category: Frontend / Tests / verification / unit
 * Scope: Phase 57 / Sprint 57.41 Day 2 (verification full mockup-fidelity rebuild)
 *
 * Description:
 *   - Renders "Verification" page-title
 *   - Renders sub-text containing "Range 7"
 *   - Renders `.route-pill` containing "/verification"
 *   - Renders both AP-2 visual-only action buttons ("All kinds" + "Export")
 *
 * Created: 2026-05-25 (Sprint 57.41 Day 2)
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.41 Day 2)
 */

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { VerificationPageHeader } from "@/features/verification/components/VerificationPageHeader";

describe("VerificationPageHeader (Sprint 57.41)", () => {
  it("renders page title, sub-text with Range 7, and /verification route pill", () => {
    render(<VerificationPageHeader />);
    expect(screen.getByText("Verification")).toBeInTheDocument();
    expect(screen.getByText(/Range 7/)).toBeInTheDocument();
    expect(screen.getByText("/verification")).toBeInTheDocument();
  });

  it("renders both AP-2 action buttons (All kinds + Export)", () => {
    render(<VerificationPageHeader />);
    expect(screen.getByRole("button", { name: /all kinds/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /export/i })).toBeInTheDocument();
  });
});
