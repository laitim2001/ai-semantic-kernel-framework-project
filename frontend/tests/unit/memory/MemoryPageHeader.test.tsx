/**
 * File: frontend/tests/unit/memory/MemoryPageHeader.test.tsx
 * Purpose: Vitest coverage for MemoryPageHeader — title / sub / route-pill / entries count / cursor-aware Badge + button label swap.
 * Category: Frontend / Tests / memory / unit
 * Scope: Phase 57 / Sprint 57.42 Day 2 (memory matrix full mockup-fidelity rebuild)
 *
 * Description:
 *   - Renders "Memory Layers" title + sub "Dual-axis · 5 scope × 3 time scale"
 *     + `.route-pill` "/memory" + formatted entries count
 *   - cursor < 0 renders conditional time-travel Badge + "Return to now" button
 *   - cursor === 0 hides Badge + shows "Time travel" button label
 *
 * Created: 2026-05-25 (Sprint 57.42 Day 2)
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.42 Day 2)
 */

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MemoryPageHeader } from "@/features/memory/components/MemoryPageHeader";

describe("MemoryPageHeader (Sprint 57.42)", () => {
  it("renders title, sub-text, /memory route pill, entries count, and 3 action buttons (cursor=0)", () => {
    render(<MemoryPageHeader cursor={0} onResetCursor={vi.fn()} entriesTotal={6514} />);
    expect(screen.getByText("Memory Layers")).toBeInTheDocument();
    expect(screen.getByText(/Dual-axis · 5 scope × 3 time scale/)).toBeInTheDocument();
    expect(screen.getByText("/memory")).toBeInTheDocument();
    expect(screen.getByText(/6,514 entries/)).toBeInTheDocument();

    // cursor=0 → "Time travel" button label (no "Return to now")
    expect(screen.getByRole("button", { name: /time travel/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /return to now/i })).not.toBeInTheDocument();
    // AP-2 visual-only stub buttons
    expect(screen.getByRole("button", { name: /export/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /new entry/i })).toBeInTheDocument();
  });

  it("cursor<0 swaps button to 'Return to now' and renders time-travel Badge with absolute minutes", () => {
    render(<MemoryPageHeader cursor={-42} onResetCursor={vi.fn()} entriesTotal={6514} />);
    // Button label swap
    expect(screen.getByRole("button", { name: /return to now/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^time travel$/i })).not.toBeInTheDocument();
    // Time-travel Badge text uses Math.abs(cursor)
    expect(screen.getByText(/time-travel · 42m ago/i)).toBeInTheDocument();
  });
});
