/**
 * File: frontend/src/features/cost-dashboard/store/costStore.ts
 * Purpose: Zustand store for Cost Dashboard state (current month + data + loading/error).
 * Category: Frontend / cost-dashboard / store
 * Scope: Phase 57 / Sprint 57.1 US-2
 *
 * Description:
 *   Mirrors chat_v2/chatStore.ts Zustand pattern (per Day 0 D4 — no React Query
 *   in V2 frontend). State: currentMonth (YYYY-MM) / data / loading / error.
 *   Actions: setMonth (clears stale data) / loadData (calls service) / reset.
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 1)
 * Last Modified: 2026-05-06
 *
 * Modification History:
 *   - 2026-05-06: Initial creation (Sprint 57.1 Day 1 / US-2 — Cost Dashboard store)
 *
 * Related:
 *   - ../services/costService.ts (fetchCostSummary)
 *   - ../types.ts (CostSummaryResponse)
 *   - frontend/src/features/chat_v2/store/chatStore.ts (pattern reference)
 */

import { create } from "zustand";

import { fetchCostSummary } from "../services/costService";
import type { CostSummaryResponse } from "../types";

function defaultMonth(): string {
  return new Date().toISOString().substring(0, 7);
}

interface CostState {
  currentMonth: string;
  data: CostSummaryResponse | null;
  loading: boolean;
  error: string | null;
  setMonth: (month: string) => void;
  loadData: (tenantId: string) => Promise<void>;
  reset: () => void;
}

export const useCostStore = create<CostState>((set, get) => ({
  currentMonth: defaultMonth(),
  data: null,
  loading: false,
  error: null,
  setMonth: (month) => set({ currentMonth: month, data: null, error: null }),
  loadData: async (tenantId) => {
    set({ loading: true, error: null });
    try {
      const data = await fetchCostSummary(tenantId, get().currentMonth);
      set({ data, loading: false });
    } catch (err) {
      set({ error: (err as Error).message, loading: false });
    }
  },
  reset: () => set({ data: null, loading: false, error: null, currentMonth: defaultMonth() }),
}));
