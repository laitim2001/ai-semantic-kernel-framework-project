/**
 * File: frontend/src/features/sla-dashboard/store/slaStore.ts
 * Purpose: Zustand store for SLA Dashboard state.
 * Category: Frontend / sla-dashboard / store
 * Scope: Phase 57 / Sprint 57.1 US-3
 *
 * Description:
 *   Mirrors costStore Zustand pattern (per Day 0 D4 — no React Query).
 *   State: currentMonth (YYYY-MM) / data / loading / error.
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 2)
 * Last Modified: 2026-05-06
 *
 * Modification History:
 *   - 2026-05-06: Initial creation (Sprint 57.1 Day 2 / US-3 — SLA Dashboard store)
 *
 * Related:
 *   - ../services/slaService.ts (fetchSLAReport)
 *   - ../types.ts (SLAReportResponse)
 *   - frontend/src/features/cost-dashboard/store/costStore.ts (pattern reference)
 */

import { create } from "zustand";

import { fetchSLAReport } from "../services/slaService";
import type { SLAReportResponse } from "../types";

function defaultMonth(): string {
  return new Date().toISOString().substring(0, 7);
}

interface SLAState {
  currentMonth: string;
  data: SLAReportResponse | null;
  loading: boolean;
  error: string | null;
  setMonth: (month: string) => void;
  loadData: (tenantId: string) => Promise<void>;
  reset: () => void;
}

export const useSLAStore = create<SLAState>((set, get) => ({
  currentMonth: defaultMonth(),
  data: null,
  loading: false,
  error: null,
  setMonth: (month) => set({ currentMonth: month, data: null, error: null }),
  loadData: async (tenantId) => {
    set({ loading: true, error: null });
    try {
      const data = await fetchSLAReport(tenantId, get().currentMonth);
      set({ data, loading: false });
    } catch (err) {
      set({ error: (err as Error).message, loading: false });
    }
  },
  reset: () => set({ data: null, loading: false, error: null, currentMonth: defaultMonth() }),
}));
