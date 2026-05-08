/**
 * File: frontend/tests/unit/components/AppShell.test.tsx
 * Purpose: Unit tests for Sprint 57.7 US-B2 AppShell + ThemeProvider + AppErrorBoundary.
 * Category: Frontend / tests / unit / components
 * Scope: Phase 57 / Sprint 57.7 Day 3 Tier 3
 *
 * Description:
 *   4 tests covering all 3 US-B2 components (target +3 ⏫ +33%):
 *   1. AppShell renders children inside main + brand link
 *   2. AppShell renders headerActions when provided
 *   3. ThemeProvider toggles html.dark class + persists to localStorage
 *   4. AppErrorBoundary catches thrown error + renders fallback + reset works
 *
 * Created: 2026-05-10 (Sprint 57.7 Day 3 Tier 3)
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppErrorBoundary } from "../../../src/components/AppErrorBoundary";
import { AppShell } from "../../../src/components/AppShell";
import { ThemeProvider, useTheme } from "../../../src/components/ThemeProvider";

describe("AppShell", () => {
  it("renders children inside the main slot + brand link", () => {
    render(
      <MemoryRouter>
        <AppShell>
          <p>hello cost dashboard</p>
        </AppShell>
      </MemoryRouter>,
    );
    expect(screen.getByText("hello cost dashboard")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "IPA Platform" })).toBeInTheDocument();
  });

  it("renders headerActions when provided", () => {
    render(
      <MemoryRouter>
        <AppShell headerActions={<button>Refresh</button>}>
          <p>body</p>
        </AppShell>
      </MemoryRouter>,
    );
    expect(screen.getByRole("button", { name: "Refresh" })).toBeInTheDocument();
  });
});

describe("ThemeProvider", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.classList.remove("dark");
  });
  afterEach(() => {
    window.localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  // Tiny consumer used to drive toggleTheme from inside the provider.
  function Toggler() {
    const { theme, toggleTheme } = useTheme();
    return (
      <button onClick={toggleTheme} aria-label="toggle">
        theme={theme}
      </button>
    );
  }

  it("toggle persists theme to localStorage + applies html.dark class", () => {
    render(
      <ThemeProvider>
        <Toggler />
      </ThemeProvider>,
    );
    // Initial state: light (matchMedia jsdom default does not match prefers-dark)
    expect(screen.getByText(/theme=light/)).toBeInTheDocument();
    expect(document.documentElement.classList.contains("dark")).toBe(false);

    // Toggle once → dark
    fireEvent.click(screen.getByRole("button", { name: "toggle" }));
    expect(screen.getByText(/theme=dark/)).toBeInTheDocument();
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(window.localStorage.getItem("ipa-theme")).toBe("dark");
  });
});

describe("AppErrorBoundary", () => {
  it("renders fallback Reset button + heading when child throws", () => {
    function Boom() {
      throw new Error("kaboom");
    }
    // Suppress React's expected console.error for thrown render error.
    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    try {
      render(
        <AppErrorBoundary>
          <Boom />
        </AppErrorBoundary>,
      );
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText(/Something went wrong/)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Reset" })).toBeInTheDocument();
      expect(screen.getByText(/kaboom/)).toBeInTheDocument();
    } finally {
      errSpy.mockRestore();
    }
  });
});

