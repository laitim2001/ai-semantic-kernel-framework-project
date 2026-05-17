/**
 * File: frontend/tests/unit/components/AppShellV2.test.tsx
 * Purpose: Vitest tests for AppShellV2 layout (sidebar + main + page title + slots).
 * Category: Frontend / tests / unit / components
 * Scope: Phase 57 / Sprint 57.8 US-1.3 Day 1
 *
 * Created: 2026-05-10 (Sprint 57.8 Day 1)
 * Last Modified: 2026-05-10
 *
 * Modification History:
 *   - 2026-05-10: Initial creation (Sprint 57.8 US-1.3 — AppShellV2 Vitest)
 */

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, test } from "vitest";

import { AppShellV2 } from "@/components/AppShellV2";
import { ThemeProvider } from "@/components/ThemeProvider";
import { useUIStore } from "@/store/uiStore";

const renderShell = (
  props: Partial<Parameters<typeof AppShellV2>[0]> = {},
  initialPath = "/cost-dashboard",
) =>
  render(
    <MemoryRouter initialEntries={[initialPath]}>
      <ThemeProvider>
        <AppShellV2 pageTitle="Test Page" {...props}>
          <p>page body content</p>
        </AppShellV2>
      </ThemeProvider>
    </MemoryRouter>,
  );

describe("AppShellV2", () => {
  beforeEach(() => {
    useUIStore.setState({ sidebarCollapsed: false });
    localStorage.removeItem("ipa-ui-state");
  });

  test("renders Sidebar + main column with children", () => {
    renderShell();
    // Sidebar is present (aria-label)
    expect(screen.getByRole("complementary", { name: "Primary navigation" })).toBeInTheDocument();
    // Page body content rendered
    expect(screen.getByText("page body content")).toBeInTheDocument();
  });

  test("renders pageTitle as <h1> in header", () => {
    renderShell({ pageTitle: "My Custom Title" });
    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading).toHaveTextContent("My Custom Title");
  });

  test("renders headerActions slot when provided", () => {
    renderShell({ headerActions: <button>Export CSV</button> });
    expect(screen.getByRole("button", { name: "Export CSV" })).toBeInTheDocument();
  });

  test("renders userMenu slot when provided (Day 2 US-2 integration)", () => {
    renderShell({ userMenu: <span data-testid="user-menu-slot">USER</span> });
    expect(screen.getByTestId("user-menu-slot")).toHaveTextContent("USER");
  });
});
