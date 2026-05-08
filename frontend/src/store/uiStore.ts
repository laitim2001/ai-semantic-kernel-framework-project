/**
 * File: frontend/src/store/uiStore.ts
 * Purpose: Module-level Zustand store for cross-page UI state (sidebar collapse, etc).
 * Category: Frontend / store / global UI state
 * Scope: Phase 57 / Sprint 57.8 US-1.1 Day 1
 *
 * Description:
 *   Holds whole-app UI state that survives route changes and page refreshes.
 *   Uses zustand/middleware `persist` to localStorage key `ipa-ui-state`.
 *
 *   Initial scope (Sprint 57.8):
 *     - sidebarCollapsed: AppShellV2 sidebar expanded (false) vs icon-only (true)
 *
 *   Future expansion candidates (kept here intentionally, NOT pre-built per
 *   YAGNI / `.claude/rules/RULES.md`):
 *     - theme: "light" | "dark" (currently fixed via ThemeProvider)
 *     - sidebarMobileDrawerOpen: drawer open state for <768px
 *
 * Created: 2026-05-10 (Sprint 57.8 Day 1)
 * Last Modified: 2026-05-10
 *
 * Modification History:
 *   - 2026-05-10: Initial creation (Sprint 57.8 US-1.1)
 *
 * Related:
 *   - frontend/src/components/AppShellV2.tsx (consumes sidebarCollapsed via useUIStore)
 *   - frontend/src/components/Sidebar.tsx (toggle button writes via setSidebarCollapsed)
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UIState {
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebar: () => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      sidebarCollapsed: false,
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      toggleSidebar: () => set({ sidebarCollapsed: !get().sidebarCollapsed }),
    }),
    {
      name: "ipa-ui-state",
    },
  ),
);
