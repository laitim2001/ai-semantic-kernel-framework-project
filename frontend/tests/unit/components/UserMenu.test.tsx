/**
 * File: frontend/tests/unit/components/UserMenu.test.tsx
 * Purpose: Vitest tests for UserMenu (auth-aware avatar dropdown).
 * Category: Frontend / tests / unit / components
 * Scope: Phase 57 / Sprint 57.8 US-2 (Sprint 57.13 US-A1 — authStore-driven)
 *
 * Created: 2026-05-10 (Sprint 57.8 Day 2)
 * Last Modified: 2026-05-10
 *
 * Modification History:
 *   - 2026-05-10: Sprint 57.13 US-A1 — drive from authStore.user instead of a localStorage JWT; sign out → logout()
 *   - 2026-05-10: Initial creation (Sprint 57.8 US-2 — UserMenu Vitest)
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { UserMenu } from "@/components/UserMenu";
import { logout } from "@/features/auth/services/authService";
import { useAuthStore } from "@/features/auth/store/authStore";

vi.mock("@/features/auth/services/authService", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/features/auth/services/authService")>();
  return { ...actual, logout: vi.fn() };
});

function setAuthed(user: { id: string; email: string; display_name: string | null }): void {
  useAuthStore.setState({
    status: "authenticated",
    user,
    tenant: { id: "t-1", name: "Acme", code: "ACME" },
    roles: ["user"],
  });
}

function setAnonymous(): void {
  useAuthStore.setState({ status: "anonymous", user: null, tenant: null, roles: [] });
}

const renderMenu = () =>
  render(
    <MemoryRouter>
      <UserMenu />
    </MemoryRouter>,
  );

describe("UserMenu", () => {
  beforeEach(() => {
    setAnonymous();
    vi.mocked(logout).mockClear();
  });

  afterEach(() => {
    useAuthStore.setState({ status: "unknown", user: null, tenant: null, roles: [] });
  });

  test("renders nothing when not authenticated", () => {
    const { container } = renderMenu();
    expect(container.firstChild).toBeNull();
  });

  test("renders avatar with display-name initial when authed", () => {
    setAuthed({ id: "u-1", email: "alice@example.com", display_name: "Alice Smith" });
    renderMenu();
    const button = screen.getByRole("button", { name: "User menu" });
    expect(button).toHaveTextContent("A"); // first char of display name, uppercase
    expect(button).toHaveAttribute("aria-haspopup", "menu");
    expect(button).toHaveAttribute("aria-expanded", "false");
  });

  test("falls back to email when display_name is null", () => {
    setAuthed({ id: "u-1", email: "bob@workos.com", display_name: null });
    renderMenu();
    expect(screen.getByRole("button", { name: "User menu" })).toHaveTextContent("B");
  });

  test("clicking avatar opens dropdown showing user + Sign out button", () => {
    setAuthed({ id: "u-1", email: "bob@workos.com", display_name: "Bob" });
    renderMenu();
    const button = screen.getByRole("button", { name: "User menu" });
    fireEvent.click(button);

    expect(screen.getByText("Signed in as")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText("bob@workos.com")).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /Sign out/ })).toBeInTheDocument();
    expect(button).toHaveAttribute("aria-expanded", "true");
  });

  test("clicking Sign out calls logout() and closes the menu", () => {
    setAuthed({ id: "u-1", email: "charlie@test.com", display_name: "Charlie" });
    renderMenu();

    const button = screen.getByRole("button", { name: "User menu" });
    fireEvent.click(button);
    fireEvent.click(screen.getByRole("menuitem", { name: /Sign out/ }));

    expect(vi.mocked(logout)).toHaveBeenCalledTimes(1);
    expect(button).toHaveAttribute("aria-expanded", "false");
  });
});
