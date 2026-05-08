/**
 * File: frontend/src/pages/cost-dashboard/index.tsx
 * Purpose: Cost Dashboard page — wraps Routes in AppShellV2 (page-level layout per Day 0 A1).
 * Category: Frontend / pages / cost-dashboard
 * Scope: Phase 57 / Sprint 57.1 US-2 → 57.8 US-4 (page-level AppShellV2 migration)
 *
 * Modification History:
 *   - 2026-05-10: Sprint 57.8 US-4 — page-level AppShellV2 wrap + MonthPickerSlot
 *     hoist (Day 0 A1: unwind CostOverview AppShell to here)
 *   - 2026-05-06: Initial creation (Sprint 57.1 Day 1 / US-2)
 */

import type { FC } from "react";
import { Route, Routes } from "react-router-dom";

import { AppShellV2 } from "../../components/AppShellV2";
import { CostOverview } from "../../features/cost-dashboard/components/CostOverview";
import { MonthPicker } from "../../features/cost-dashboard/components/MonthPicker";
import { useCostStore } from "../../features/cost-dashboard/store/costStore";

const MonthPickerSlot: FC = () => {
  const { currentMonth, setMonth, loading } = useCostStore();
  return <MonthPicker value={currentMonth} onChange={setMonth} disabled={loading} />;
};

export default function CostDashboardPage() {
  return (
    <AppShellV2 pageTitle="Cost Dashboard" headerActions={<MonthPickerSlot />}>
      <Routes>
        <Route index element={<CostOverview />} />
      </Routes>
    </AppShellV2>
  );
}
