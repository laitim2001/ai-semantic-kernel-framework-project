/**
 * File: frontend/src/pages/cost-dashboard/index.tsx
 * Purpose: Cost Dashboard page wrapper — wildcard route per chat-v2 / governance pattern.
 * Category: Frontend / pages / cost-dashboard
 * Scope: Phase 57 / Sprint 57.1 US-2
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 1)
 * Last Modified: 2026-05-06
 *
 * Modification History:
 *   - 2026-05-06: Initial creation (Sprint 57.1 Day 1 / US-2)
 */

import { Route, Routes } from "react-router-dom";

import { CostOverview } from "../../features/cost-dashboard/components/CostOverview";

export default function CostDashboardPage() {
  return (
    <Routes>
      <Route index element={<CostOverview />} />
    </Routes>
  );
}
