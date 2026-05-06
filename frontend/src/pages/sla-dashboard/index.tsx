/**
 * File: frontend/src/pages/sla-dashboard/index.tsx
 * Purpose: SLA Dashboard page wrapper — wildcard route per chat-v2 / governance pattern.
 * Category: Frontend / pages / sla-dashboard
 * Scope: Phase 57 / Sprint 57.1 US-3
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 2)
 * Last Modified: 2026-05-06
 *
 * Modification History:
 *   - 2026-05-06: Initial creation (Sprint 57.1 Day 2 / US-3)
 */

import { Route, Routes } from "react-router-dom";

import { SLAOverview } from "../../features/sla-dashboard/components/SLAOverview";

export default function SLADashboardPage() {
  return (
    <Routes>
      <Route index element={<SLAOverview />} />
    </Routes>
  );
}
