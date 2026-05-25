/**
 * File: frontend/src/pages/memory/index.tsx
 * Purpose: Memory page (real ship) — auth gate + AppShellV2 wrap + single MemoryView (mockup-fidelity rebuild) + backward-compat redirects.
 * Category: Frontend / pages / memory
 * Scope: Phase 57 / Sprint 57.42 Day 1 (mockup-fidelity rebuild)
 *
 * Description:
 *   Sprint 57.42 rebuild: drops outer 2-tab nav (Recent / By Scope) per
 *   §1.4 Option B decision (closes drift audit 2026-05-25 #2 priority
 *   CATASTROPHIC verdict — mockup ships 5×3 matrix, NOT 2-tab navigation).
 *
 *   Single mount: <MemoryView /> renders the dual-axis 5 scope × 3 time scale
 *   matrix with time-travel scrubber + Recent ops + GDPR erasure Cards.
 *
 *   Backward-compat redirects: /memory/recent + /memory/by-scope (legacy URLs
 *   from Sprint 57.12) redirect to /memory so existing bookmarks / links keep
 *   working.
 *
 *   Auth gate via <RequireAuth>; AppShellV2 pageTitle "Memory".
 *
 * Created: 2026-05-10 (Sprint 57.12 Day 2-3 / US-5)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Sprint 57.42 Day 1 — outer 2-tab DROP per §1.4 Option B; single MemoryView + redirects
 *   - 2026-05-10: Sprint 57.13 US-A1 — gate via <RequireAuth> (was inline isAuthenticated() check)
 *   - 2026-05-10: Initial creation (Sprint 57.12 US-5 Day 2-3 — real ship)
 *
 * Related:
 *   - frontend/src/features/auth/components/RequireAuth.tsx (route gate)
 *   - frontend/src/components/AppShellV2.tsx (page-level shell)
 *   - frontend/src/features/memory/components/MemoryView.tsx (Sprint 57.42 rebuild)
 *   - reference/design-mockups/page-governance.jsx L462-597 (MemoryPage source)
 */

import { Navigate, Route, Routes } from "react-router-dom";

import { AppShellV2 } from "@/components/AppShellV2";
import { RequireAuth } from "@/features/auth/components/RequireAuth";
import { MemoryView } from "@/features/memory/components/MemoryView";

export default function MemoryPage(): JSX.Element {
  return (
    <RequireAuth>
      <AppShellV2 pageTitle="Memory">
        <Routes>
          <Route index element={<MemoryView />} />
          <Route path="recent" element={<Navigate to="/memory" replace />} />
          <Route path="by-scope" element={<Navigate to="/memory" replace />} />
          <Route path="*" element={<Navigate to="/memory" replace />} />
        </Routes>
      </AppShellV2>
    </RequireAuth>
  );
}
