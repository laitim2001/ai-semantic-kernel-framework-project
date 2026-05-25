/**
 * File: frontend/tests/unit/verification/FailureKindsCard.test.tsx
 * Purpose: Vitest coverage for FailureKindsCard — 5 fixture rows + AP-2 banner.
 * Category: Frontend / Tests / verification / unit
 * Scope: Phase 57 / Sprint 57.41 Day 2 (verification full mockup-fidelity rebuild)
 *
 * Description:
 *   - Card title "Failure kinds" renders
 *   - 5 fixture failure-kind names render in mockup order
 *     (source_allowlist / schema_completeness / metric_threshold / evidence_chain / doc_match)
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

import { FailureKindsCard } from "@/features/verification/components/FailureKindsCard";

describe("FailureKindsCard (Sprint 57.41)", () => {
  it("renders Card title + 5 fixture rows + AP-2 BackendGapBanner", () => {
    render(<FailureKindsCard />);

    expect(screen.getByText("Failure kinds")).toBeInTheDocument();

    expect(screen.getByText("source_allowlist")).toBeInTheDocument();
    expect(screen.getByText("schema_completeness")).toBeInTheDocument();
    expect(screen.getByText("metric_threshold")).toBeInTheDocument();
    expect(screen.getByText("evidence_chain")).toBeInTheDocument();
    expect(screen.getByText("doc_match")).toBeInTheDocument();

    const banner = screen.getByTestId("backend-gap-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(/Failure kinds aggregation endpoint pending/i);
  });
});
