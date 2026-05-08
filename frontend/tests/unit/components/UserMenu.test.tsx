/**
 * File: frontend/tests/unit/components/UserMenu.test.tsx
 * Purpose: Vitest tests for UserMenu (auth-aware avatar dropdown).
 * Category: Frontend / tests / unit / components
 * Scope: Phase 57 / Sprint 57.8 US-2 Day 2
 *
 * Created: 2026-05-10 (Sprint 57.8 Day 2)
 * Last Modified: 2026-05-10
 *
 * Modification History:
 *   - 2026-05-10: Initial creation (Sprint 57.8 US-2 — UserMenu Vitest)
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, test } from "vitest";

import { UserMenu } from "@/components/UserMenu";

const JWT_KEY = "v2_jwt";

// Helper to forge JWT with email claim (signature ignored — UserMenu is
// browser-display only; backend re-verifies on every request).
function forgeJwt(email: string): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = btoa(JSON.stringify({ sub: "u1", email }));
  const sig = "ignored";
  return `${header}.${payload}.${sig}`;
}

const renderMenu = () =>
  render(
    <MemoryRouter>
      <UserMenu />
    </MemoryRouter>,
  );

describe("UserMenu", () => {
  beforeEach(() => {
    localStorage.removeItem(JWT_KEY);
  });

  afterEach(() => {
    localStorage.removeItem(JWT_KEY);
  });

  test("renders nothing when not authenticated", () => {
    const { container } = renderMenu();
    expect(container.firstChild).toBeNull();
  });

  test("renders avatar with email initial when authed", () => {
    localStorage.setItem(JWT_KEY, forgeJwt("alice@example.com"));
    renderMenu();
    const button = screen.getByRole("button", { name: "User menu" });
    expect(button).toHaveTextContent("A"); // first char uppercase
    expect(button).toHaveAttribute("aria-haspopup", "menu");
    expect(button).toHaveAttribute("aria-expanded", "false");
  });

  test("clicking avatar opens dropdown showing email + Sign out button", () => {
    localStorage.setItem(JWT_KEY, forgeJwt("bob@workos.com"));
    renderMenu();
    const button = screen.getByRole("button", { name: "User menu" });
    fireEvent.click(button);

    expect(screen.getByText("Signed in as")).toBeInTheDocument();
    expect(screen.getByText("bob@workos.com")).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /Sign out/ })).toBeInTheDocument();
    expect(button).toHaveAttribute("aria-expanded", "true");
  });

  test("clicking Sign out clears localStorage JWT (redirect tested via integration)", () => {
    localStorage.setItem(JWT_KEY, forgeJwt("charlie@test.com"));
    renderMenu();

    fireEvent.click(screen.getByRole("button", { name: "User menu" }));
    fireEvent.click(screen.getByRole("menuitem", { name: /Sign out/ }));

    expect(localStorage.getItem(JWT_KEY)).toBeNull();
  });
});
