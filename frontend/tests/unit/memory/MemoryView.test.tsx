/**
 * File: frontend/tests/unit/memory/MemoryView.test.tsx
 * Purpose: Vitest integration coverage for MemoryView — assembles all 5 children with initial cursor=0 state.
 * Category: Frontend / Tests / memory / unit
 * Scope: Phase 57 / Sprint 57.42 Day 2 (memory matrix full mockup-fidelity rebuild)
 *
 * Description:
 *   - Renders MemoryPageHeader (title "Memory Layers")
 *   - Renders TimeTravelScrubber (slider role + "Replay 24h" button)
 *   - Renders MemoryMatrix (5×3 grid headers — "permanent" / "quarter" / "day")
 *   - Renders RecentMemoryOpsCard (title "Recent memory ops")
 *   - Renders GdprErasureCard (title "GDPR right-to-erasure")
 *   - Initial state cursor=0 → MemoryPageHeader shows "Time travel" button (not "Return to now")
 *
 * Created: 2026-05-25 (Sprint 57.42 Day 2)
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.42 Day 2)
 */

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MemoryView } from "@/features/memory/components/MemoryView";

describe("MemoryView (Sprint 57.42)", () => {
  it("integrates all 5 child components with cursor=0 initial state", () => {
    render(<MemoryView />);

    // 1. MemoryPageHeader
    expect(screen.getByText("Memory Layers")).toBeInTheDocument();
    expect(screen.getByText("/memory")).toBeInTheDocument();
    // cursor=0 initial → "Time travel" button (NOT "Return to now")
    expect(screen.getByRole("button", { name: /^time travel$/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /return to now/i })).not.toBeInTheDocument();

    // 2. TimeTravelScrubber
    expect(screen.getByRole("slider", { name: /time travel scrubber/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /replay 24h/i })).toBeInTheDocument();

    // 3. MemoryMatrix (5x3 grid headers)
    expect(screen.getByText("permanent")).toBeInTheDocument();
    expect(screen.getByText("quarter")).toBeInTheDocument();
    expect(screen.getByText("day")).toBeInTheDocument();

    // 4. RecentMemoryOpsCard
    expect(screen.getByText("Recent memory ops")).toBeInTheDocument();

    // 5. GdprErasureCard
    expect(screen.getByText("GDPR right-to-erasure")).toBeInTheDocument();
  });
});
