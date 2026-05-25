/**
 * File: frontend/src/features/verification/components/VerificationStatsStrip.tsx
 * Purpose: 4-KPI stat strip for Verification page (mockup .grid-stats section).
 * Category: Frontend / verification / components
 * Scope: Phase 57 / Sprint 57.41 Day 1 (mockup-fidelity rebuild)
 *
 * Description:
 *   Verbatim port of `reference/design-mockups/page-extras.jsx:847-852`
 *   (`.grid-stats` section). Renders 4 KPI cards:
 *     1. Pass rate · 1h — REAL data computed from items
 *        (items.filter(passed).length / total * 100, fallback 0 when empty)
 *     2. Claims · 1h — fixture (backend aggregation endpoint pending)
 *     3. Failed · 1h — fixture (backend aggregation endpoint pending)
 *     4. Median latency — fixture (backend aggregation endpoint pending)
 *   A BackendGapBanner above the strip declares the 3 fixture KPI status per
 *   `.claude/rules/anti-patterns-checklist.md` AP-2 (no Potemkin).
 *
 *   Mirrors Sprint 57.40 ApprovalsStatsStrip composition pattern (single
 *   <BackendGapBanner> + inner .grid-stats wrapper).
 *
 * Key Components:
 *   - VerificationStatsStrip: stateless; props pass items for Card 1 real pass rate
 *
 * Created: 2026-05-25 (Sprint 57.41 Day 1)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.41 Day 1) — verification view full mockup-fidelity rebuild
 *
 * Related:
 *   - reference/design-mockups/page-extras.jsx L847-852
 *   - ../../../components/mockup-ui.tsx (Stat primitive)
 *   - ../../../components/ui/BackendGapBanner.tsx (AP-2 fixture declaration)
 */

import { Stat } from "../../../components/mockup-ui";
import { BackendGapBanner } from "../../../components/ui/BackendGapBanner";
import type { VerificationLogItem } from "../types";

interface Props {
  items: VerificationLogItem[] | undefined;
}

export function VerificationStatsStrip({ items }: Props) {
  const total = items?.length ?? 0;
  const passed = items?.filter((c) => c.passed).length ?? 0;
  const passRate = total > 0 ? ((passed / total) * 100).toFixed(1) : "0.0";
  return (
    <>
      <BackendGapBanner reason="Claims · 1h / Failed · 1h / Median latency are demo data pending backend verification aggregation endpoint" />
      <div className="grid-stats">
        <Stat label="Pass rate · 1h" value={passRate} unit="%" delta="-1.4pp" deltaDir="down" />
        <Stat label="Claims · 1h" value="2,840" delta="+180" deltaDir="up" />
        <Stat label="Failed · 1h" value="22" delta="+4" deltaDir="down" />
        <Stat label="Median latency" value="24" unit="ms" delta="-3ms" deltaDir="up" />
      </div>
    </>
  );
}
