/**
 * File: frontend/src/features/governance/components/ApprovalsStatsStrip.tsx
 * Purpose: 4-KPI stat strip for HITL Approvals page (mockup .grid-stats section).
 * Category: Frontend / governance / components
 * Scope: Phase 57 / Sprint 57.40 Day 1 (mockup-fidelity rebuild)
 *
 * Description:
 *   Verbatim port of `reference/design-mockups/page-governance.jsx:303-308`
 *   (`.grid-stats` section). Renders 4 KPI cards:
 *     1. Active queue — REAL data via `approvals.length` (count of pending)
 *     2. p50 approval time — fixture (backend stats endpoint pending)
 *     3. Approved · 24h — fixture (backend stats endpoint pending)
 *     4. Rejected · 24h — fixture (backend stats endpoint pending)
 *   A BackendGapBanner above the strip declares the AP-2 fixture status per
 *   `.claude/rules/anti-patterns-checklist.md` AP-2 (no Potemkin).
 *
 * Key Components:
 *   - ApprovalsStatsStrip: stateless; props pass `approvals` for Card 1 real count
 *
 * Created: 2026-05-25 (Sprint 57.40 Day 1)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Sprint 57.40 — initial creation (4-KPI strip; 1 real + 3 fixture + AP-2 banner)
 *
 * Related:
 *   - reference/design-mockups/page-governance.jsx L303-308
 *   - ../../../components/mockup-ui.tsx (Stat primitive)
 *   - ../../../components/ui/BackendGapBanner.tsx (AP-2 fixture declaration)
 */

import { Stat } from "../../../components/mockup-ui";
import { BackendGapBanner } from "../../../components/ui/BackendGapBanner";
import type { ApprovalSummary } from "../types";

interface Props {
  approvals: ApprovalSummary[] | undefined;
}

export function ApprovalsStatsStrip({ approvals }: Props) {
  const activeCount = approvals?.length ?? 0;
  return (
    <>
      <BackendGapBanner reason="p50 approval time / Approved 24h / Rejected 24h are demo data pending backend stats endpoint" />
      <div className="grid-stats">
        <Stat label="Active queue" value={String(activeCount)} delta="+2" deltaDir="down" />
        <Stat label="p50 approval time" value="2m 18s" delta="-12s" deltaDir="up" />
        <Stat label="Approved · 24h" value="184" delta="+11" deltaDir="up" />
        <Stat label="Rejected · 24h" value="6" delta="+2" deltaDir="down" />
      </div>
    </>
  );
}
