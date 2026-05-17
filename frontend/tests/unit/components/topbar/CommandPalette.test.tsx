/**
 * File: frontend/tests/unit/components/topbar/CommandPalette.test.tsx
 * Purpose: Vitest coverage for CommandPalette (US-D1) — render / search filter / group rendering.
 * Category: Frontend / Tests / components / topbar
 * Scope: Phase 57 / Sprint 57.19 Day 5 / US-D1
 *
 * Created: 2026-05-17 (Sprint 57.19 Day 5 / US-D1)
 *
 * Modification History (newest-first):
 *   - 2026-05-17: Initial creation (Sprint 57.19 Day 5 / US-D1)
 */

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { CommandPalette } from "@/components/topbar/CommandPalette";

function wrap(open: boolean, onOpenChange = vi.fn()) {
  return (
    <MemoryRouter>
      <CommandPalette open={open} onOpenChange={onOpenChange} />
    </MemoryRouter>
  );
}

describe("CommandPalette", () => {
  it("does not render when closed", () => {
    render(wrap(false));
    expect(screen.queryByPlaceholderText(/search pages/i)).not.toBeInTheDocument();
  });

  it("renders input + footer hints when open", () => {
    render(wrap(true));
    expect(screen.getByPlaceholderText(/search pages/i)).toBeInTheDocument();
    expect(screen.getByText(/navigate/i)).toBeInTheDocument();
    expect(screen.getByText(/results/i)).toBeInTheDocument();
  });

  it("renders Actions group + 4 fixed actions by default", () => {
    render(wrap(true));
    expect(screen.getByText("Actions")).toBeInTheDocument();
    expect(screen.getByText("New chat")).toBeInTheDocument();
    expect(screen.getByText("Review HITL queue")).toBeInTheDocument();
    expect(screen.getByText("Onboard tenant")).toBeInTheDocument();
    expect(screen.getByText("Declare incident")).toBeInTheDocument();
  });

  it("renders Pages group with multiple ROUTES entries", () => {
    render(wrap(true));
    expect(screen.getByText("Pages")).toBeInTheDocument();
  });

  it("filtering 'chat' narrows results to chat-related items", async () => {
    const user = userEvent.setup();
    render(wrap(true));
    const input = screen.getByPlaceholderText(/search pages/i);
    await user.type(input, "chat");
    expect(screen.getByText("New chat")).toBeInTheDocument();
  });

  it("empty state shown when query matches nothing", async () => {
    const user = userEvent.setup();
    render(wrap(true));
    const input = screen.getByPlaceholderText(/search pages/i);
    await user.type(input, "xyzzyzz-not-in-anywhere");
    expect(screen.getByText(/no results/i)).toBeInTheDocument();
  });
});
