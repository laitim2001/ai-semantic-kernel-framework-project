/**
 * File: frontend/tests/unit/components/topbar/NotificationsPanel.test.tsx
 * Purpose: Vitest coverage for NotificationsPanel (US-D2) — render / tab switch / mark all / dismiss.
 * Category: Frontend / Tests / components / topbar
 * Scope: Phase 57 / Sprint 57.19 Day 5 / US-D2
 *
 * Created: 2026-05-17 (Sprint 57.19 Day 5 / US-D2)
 *
 * Modification History (newest-first):
 *   - 2026-05-17: Initial creation (Sprint 57.19 Day 5 / US-D2)
 */

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { NotificationsPanel } from "@/components/topbar/NotificationsPanel";

function wrap(open: boolean, onClose = vi.fn()) {
  return (
    <MemoryRouter>
      <NotificationsPanel open={open} onClose={onClose} />
    </MemoryRouter>
  );
}

describe("NotificationsPanel", () => {
  it("does not render when closed", () => {
    render(wrap(false));
    expect(screen.queryByText("Notifications")).not.toBeInTheDocument();
  });

  it("renders title + tabs + items when open", () => {
    render(wrap(true));
    expect(screen.getByText("Notifications")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /All/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Unread/ })).toBeInTheDocument();
  });

  it("renders all 6 fixture items by default (All tab)", () => {
    render(wrap(true));
    expect(screen.getByText("P1 escalation awaiting approval")).toBeInTheDocument();
    expect(screen.getByText(/p95 latency breach/)).toBeInTheDocument();
    expect(screen.getByText("Verification failed twice")).toBeInTheDocument();
  });

  it("shows unread count badge in header", () => {
    render(wrap(true));
    expect(screen.getByText(/^3 /)).toBeInTheDocument();
  });

  it("clicking Unread tab filters to 3 items", async () => {
    const user = userEvent.setup();
    render(wrap(true));
    await user.click(screen.getByRole("tab", { name: /Unread/ }));
    expect(screen.queryByText("PII redaction triggered")).not.toBeInTheDocument();
  });

  it("clicking Mark all read clears unread state badge", async () => {
    const user = userEvent.setup();
    render(wrap(true));
    await user.click(screen.getByText(/Mark all read/i));
    expect(screen.queryByText(/^3 new/)).not.toBeInTheDocument();
  });

  it("renders footer View all + Preferences buttons", () => {
    render(wrap(true));
    expect(screen.getByText(/view all/i)).toBeInTheDocument();
    expect(screen.getByText(/preferences/i)).toBeInTheDocument();
  });
});
