/**
 * File: frontend/tests/unit/verification/VerificationRunsTable.test.tsx
 * Purpose: Vitest coverage for VerificationRunsTable — empty / loading / error / data states.
 * Category: Frontend / Tests / verification / unit
 * Scope: Phase 57 / Sprint 57.41 Day 2 (verification full mockup-fidelity rebuild)
 *
 * Description:
 *   - Card title "Recent verification runs" + subtitle render
 *   - Empty items array renders "No verification runs yet." subtle row
 *   - 2 data items (1 passed score=0.94 + 1 failed score=0.42) render 2 data rows
 *     with verifier_name + adapted claim + Kind Badge + tone-tiered score
 *   - isError state renders "Failed to load verification runs." danger row
 *
 * Created: 2026-05-25 (Sprint 57.41 Day 2)
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.41 Day 2)
 */

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { VerificationRunsTable } from "@/features/verification/components/VerificationRunsTable";
import type { VerificationLogItem } from "@/features/verification/types";

function makeItem(
  id: number,
  verifier_name: string,
  passed: boolean,
  score: number | null,
  reason: string | null,
): VerificationLogItem {
  return {
    id,
    tenant_id: "11111111-1111-4111-8111-111111111111",
    session_id: "22222222-2222-4222-8222-222222222222",
    turn_index: 0,
    verifier_name,
    verifier_type: passed ? "llm_judge" : "rules_based",
    passed,
    score,
    reason,
    suggested_correction: null,
    correction_attempt: 0,
    created_at_ms: Date.now() - 60_000,
  };
}

describe("VerificationRunsTable (Sprint 57.41)", () => {
  it("renders Card title + empty-state row when items is empty", () => {
    render(<VerificationRunsTable items={[]} />);
    expect(screen.getByText("Recent verification runs")).toBeInTheDocument();
    expect(screen.getByText("No verification runs yet.")).toBeInTheDocument();
  });

  it("renders 2 data rows for 2 items (passed + failed) with verifier_name", () => {
    const items = [
      makeItem(1, "salesforce_query", true, 0.94, null),
      makeItem(2, "patrol_get_results", false, 0.42, "verifier.check failed: 1 of 5 items has no owner"),
    ];
    render(<VerificationRunsTable items={items} />);

    // Both verifier names appear (as agent cell + adapted claim cell)
    expect(screen.getAllByText("salesforce_query").length).toBeGreaterThan(0);
    expect(screen.getAllByText("patrol_get_results").length).toBeGreaterThan(0);

    // Passed row → adapted claim "<verifier> check passed"
    expect(screen.getByText(/salesforce_query check passed/i)).toBeInTheDocument();

    // Failed row → adapted claim is the reason string (also appears in evidence
    // sub-cell sliced to 80 chars; both occurrences are expected).
    expect(
      screen.getAllByText(/verifier\.check failed: 1 of 5 items has no owner/i).length,
    ).toBeGreaterThan(0);

    // Score formatted to 2 dp (0.94 success tier; 0.42 danger tier)
    expect(screen.getByText("0.94")).toBeInTheDocument();
    expect(screen.getByText("0.42")).toBeInTheDocument();
  });

  it("renders danger-tier error row when isError=true", () => {
    render(<VerificationRunsTable items={[]} isError />);
    expect(screen.getByText(/Failed to load verification runs\./i)).toBeInTheDocument();
  });
});
