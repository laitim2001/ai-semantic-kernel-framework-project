/**
 * Expert Selection Store — manages roster preview state.
 *
 * Populated by EXPERT_ROSTER_PREVIEW SSE event. Toggle is UI-only
 * in Sprint 165 (enforcement deferred to Sprint 166).
 *
 * Sprint 165 — Phase 46 Agent Expert Registry.
 */

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

export interface RosterExpert {
  role: string;
  taskId: string;
  taskTitle: string;
  expertName: string;
  displayNameZh: string;
  domain: string;
  capabilities: string[];
}

interface ExpertSelectionState {
  rosterPreview: RosterExpert[];
  disabledExperts: Set<string>;
  isRosterVisible: boolean;
}

interface ExpertSelectionActions {
  setRosterPreview: (roster: RosterExpert[]) => void;
  toggleExpert: (role: string) => void;
  enableAll: () => void;
  disableAll: () => void;
  showRoster: () => void;
  hideRoster: () => void;
  reset: () => void;
}

export const useExpertSelectionStore = create<ExpertSelectionState & ExpertSelectionActions>()(
  immer((set) => ({
    rosterPreview: [],
    disabledExperts: new Set<string>(),
    isRosterVisible: false,

    setRosterPreview: (roster) =>
      set((state) => {
        state.rosterPreview = roster;
        state.disabledExperts = new Set();
      }),

    toggleExpert: (role) =>
      set((state) => {
        if (state.disabledExperts.has(role)) {
          state.disabledExperts.delete(role);
        } else {
          state.disabledExperts.add(role);
        }
      }),

    enableAll: () =>
      set((state) => {
        state.disabledExperts = new Set();
      }),

    disableAll: () =>
      set((state) => {
        state.disabledExperts = new Set(state.rosterPreview.map((e) => e.role));
      }),

    showRoster: () =>
      set((state) => {
        state.isRosterVisible = true;
      }),

    hideRoster: () =>
      set((state) => {
        state.isRosterVisible = false;
      }),

    reset: () =>
      set((state) => {
        state.rosterPreview = [];
        state.disabledExperts = new Set();
        state.isRosterVisible = false;
      }),
  }))
);
