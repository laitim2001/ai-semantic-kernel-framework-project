/**
 * File: frontend/tests/unit/store/uiStore.test.ts
 * Purpose: Vitest unit tests for global UI Zustand store (sidebar collapse + persist).
 * Category: Frontend / tests / unit / store
 * Scope: Phase 57 / Sprint 57.8 US-1.1 Day 1
 *
 * Created: 2026-05-10 (Sprint 57.8 Day 1)
 * Last Modified: 2026-05-10
 *
 * Modification History:
 *   - 2026-05-10: Initial creation (Sprint 57.8 US-1.1 — uiStore Vitest)
 */

import { beforeEach, describe, expect, test } from "vitest";

import { useUIStore } from "@/store/uiStore";

describe("uiStore", () => {
  beforeEach(() => {
    // Reset store + clear persisted state between tests for isolation.
    useUIStore.setState({ sidebarCollapsed: false });
    localStorage.removeItem("ipa-ui-state");
  });

  test("default sidebarCollapsed is false (expanded)", () => {
    expect(useUIStore.getState().sidebarCollapsed).toBe(false);
  });

  test("setSidebarCollapsed(true) flips state to collapsed", () => {
    useUIStore.getState().setSidebarCollapsed(true);
    expect(useUIStore.getState().sidebarCollapsed).toBe(true);
  });

  test("toggleSidebar inverts current state", () => {
    expect(useUIStore.getState().sidebarCollapsed).toBe(false);
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarCollapsed).toBe(true);
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarCollapsed).toBe(false);
  });

  test("state persists to localStorage under key ipa-ui-state", () => {
    useUIStore.getState().setSidebarCollapsed(true);
    const raw = localStorage.getItem("ipa-ui-state");
    expect(raw).not.toBeNull();
    const parsed = JSON.parse(raw!);
    expect(parsed.state.sidebarCollapsed).toBe(true);
  });
});
