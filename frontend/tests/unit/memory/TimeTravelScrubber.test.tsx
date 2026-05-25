/**
 * File: frontend/tests/unit/memory/TimeTravelScrubber.test.tsx
 * Purpose: Vitest coverage for TimeTravelScrubber — slider value mapping, onCursor / onPlay callbacks, cursor display, playing button label/icon.
 * Category: Frontend / Tests / memory / unit
 * Scope: Phase 57 / Sprint 57.42 Day 2 (memory matrix full mockup-fidelity rebuild)
 *
 * Description:
 *   - Slider mapping: cursor=0 → slider value 0; cursor=-1440 → slider value 100
 *   - Slider change fires onCursor with rounded value (range is multiples of 5)
 *   - playing=false renders "Replay 24h" + onPlay fires on click
 *   - playing=true renders "Pause" label (button variant warning)
 *   - "Now" ghost button calls onCursor(0)
 *   - Cursor display mono shows "now" when cursor=0 and "T-{n}m" when cursor<0
 *
 *   Note: setInterval auto-decrement lives in MemoryView (parent), NOT inside
 *   TimeTravelScrubber — verified by reading MemoryView.tsx. Component is pure
 *   controlled; no timer behaviour to test here.
 *
 * Created: 2026-05-25 (Sprint 57.42 Day 2)
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.42 Day 2)
 */

import "@testing-library/jest-dom/vitest";

import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { TimeTravelScrubber } from "@/features/memory/components/TimeTravelScrubber";

describe("TimeTravelScrubber (Sprint 57.42)", () => {
  it("maps cursor to slider value and fires onCursor with rounded value on slider change", () => {
    const onCursor = vi.fn();
    render(
      <TimeTravelScrubber cursor={0} onCursor={onCursor} playing={false} onPlay={vi.fn()} />,
    );
    const slider = screen.getByRole("slider", { name: /time travel scrubber/i }) as HTMLInputElement;
    // cursor=0 → sliderValue = 0
    expect(slider.value).toBe("0");

    // Simulate slider drag to 50% → expected cursor = round(-1440 * 0.5 / 5) * 5 = -720
    fireEvent.change(slider, { target: { value: "50" } });
    expect(onCursor).toHaveBeenCalledWith(-720);

    // cursor display when cursor=0 → "now" (also appears as a label mark; both
    // are expected — assert both occurrences exist)
    expect(screen.getAllByText("now").length).toBeGreaterThanOrEqual(2);
  });

  it("playing=false shows 'Replay 24h' + onPlay fires; cursor<0 shows T-Xm display", async () => {
    const onPlay = vi.fn();
    const onCursor = vi.fn();
    render(
      <TimeTravelScrubber cursor={-30} onCursor={onCursor} playing={false} onPlay={onPlay} />,
    );
    const replay = screen.getByRole("button", { name: /replay 24h/i });
    await userEvent.click(replay);
    expect(onPlay).toHaveBeenCalled();

    // cursor=-30 → T-30m display
    expect(screen.getByText("T-30m")).toBeInTheDocument();

    // "Now" ghost button resets cursor to 0
    await userEvent.click(screen.getByRole("button", { name: /^now$/i }));
    expect(onCursor).toHaveBeenCalledWith(0);
  });

  it("playing=true swaps button label to 'Pause'", () => {
    render(
      <TimeTravelScrubber cursor={-90} onCursor={vi.fn()} playing={true} onPlay={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: /^pause$/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /replay 24h/i })).not.toBeInTheDocument();
  });
});
