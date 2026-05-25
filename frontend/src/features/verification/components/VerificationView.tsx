/* eslint-disable no-restricted-syntax -- mockup verbatim CSS literals; mockup-fidelity (Sprint 57.41). See reference/design-mockups/page-extras.jsx L829-925. */
/**
 * File: frontend/src/features/verification/components/VerificationView.tsx
 * Purpose: Verification recent view — full mockup-fidelity rebuild composition.
 * Category: Frontend / verification / components
 * Scope: Phase 57 / Sprint 57.41 Day 1 (mockup-fidelity rebuild)
 *
 * Description:
 *   Sprint 57.41 rebuild: replaces legacy VerificationList.tsx (filter form +
 *   pagination + table) with mockup-faithful 5-component composition matching
 *   `reference/design-mockups/page-extras.jsx:829-925` VerificationPage:
 *     - VerificationPageHeader (.page-head + 2 AP-2 buttons)
 *     - VerificationStatsStrip (4 KPI; Pass rate = real, others fixture + AP-2)
 *     - 2-col layout: VerificationRunsTable (left main) + sidebar
 *       (FailureKindsCard + FlakyChecksCard in a .col gap-14)
 *
 *   Filter form retired (orphan-deleted VerificationList.tsx per Karpathy §3).
 *   Filter UX deferred to Phase 58+ "All kinds" button reintegration
 *   (carryover AD-Verification-Filter-Form-Phase58-Migrate).
 *
 *   Resolves drift audit 2026-05-25 #4 priority CATASTROPHIC verdict
 *   (production was filter form + bare table; mockup ships 4 KPI + table +
 *   2 sidebar Cards composition).
 *
 *   Mounts under outer 2-tab shell (pages/verification/index.tsx Tabs); this
 *   component is the "recent" tab content. "timeline" tab still renders
 *   CorrectionTraceView (out of scope this sprint).
 *
 * Key Components:
 *   - VerificationView: consumes useVerificationRecent (no filter — show all)
 *
 * Created: 2026-05-25 (Sprint 57.41 Day 1)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.41 Day 1) — verification view full mockup-fidelity rebuild
 *
 * Related:
 *   - reference/design-mockups/page-extras.jsx L829-925 (VerificationPage)
 *   - ../hooks/useVerificationRecent.ts
 *   - ./VerificationPageHeader.tsx ./VerificationStatsStrip.tsx
 *     ./VerificationRunsTable.tsx ./FailureKindsCard.tsx ./FlakyChecksCard.tsx
 *   - ../../../pages/verification/index.tsx (parent — outer 2-tab shell)
 */

import { useVerificationRecent } from "../hooks/useVerificationRecent";
import { FailureKindsCard } from "./FailureKindsCard";
import { FlakyChecksCard } from "./FlakyChecksCard";
import { VerificationPageHeader } from "./VerificationPageHeader";
import { VerificationRunsTable } from "./VerificationRunsTable";
import { VerificationStatsStrip } from "./VerificationStatsStrip";

const DEFAULT_FILTER = { limit: 50, offset: 0 } as const;

export function VerificationView() {
  const query = useVerificationRecent(DEFAULT_FILTER);
  const items = query.data?.items ?? [];

  return (
    <div>
      <VerificationPageHeader />
      <VerificationStatsStrip items={query.data?.items} />
      <div className="grid-main">
        <VerificationRunsTable
          items={items}
          isLoading={query.isLoading}
          isError={query.isError}
        />
        <div className="col" style={{ gap: 14 }}>
          <FailureKindsCard />
          <FlakyChecksCard />
        </div>
      </div>
    </div>
  );
}
