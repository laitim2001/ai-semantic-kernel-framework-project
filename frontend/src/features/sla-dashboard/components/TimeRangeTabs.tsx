/**
 * File: frontend/src/features/sla-dashboard/components/TimeRangeTabs.tsx
 * Purpose: 4-button time-range tab group for SLA Dashboard page-actions (Sprint 57.25 Day 1 US-B1).
 * Category: Frontend / sla-dashboard / components
 * Scope: Phase 57 / Sprint 57.25 Day 1 US-B1
 *
 * Description:
 *   Mockup-direct port of `reference/design-mockups/page-admin.jsx:42-48`
 *   .btn-group with 4 range buttons (1h ghost / 24h outline-active /
 *   7d ghost / 30d ghost). Per user Q2 alignment (2026-05-19), this
 *   sprint ships visual-only with local React useState active tab; clicks
 *   change active highlight but do NOT refetch data (backend time-range
 *   aggregation endpoint pending Phase 58+
 *   AD-SLA-Dashboard-Backend-Extensions-Phase58).
 *
 *   AP-2 honesty: the broader LatencyChart 24h widget below carries the
 *   BackendGapBanner declaring time-range aggregation pending; this
 *   component itself stays minimal (4-button group with role="tablist").
 *
 * Created: 2026-05-19 (Sprint 57.25 Day 1 US-B1)
 * Last Modified: 2026-05-19
 *
 * Modification History:
 *   - 2026-05-19: Initial creation (Sprint 57.25 Day 1 US-B1)
 *
 * Related:
 *   - reference/design-mockups/page-admin.jsx:42-48 (canonical mockup)
 *   - sprint-57-25-plan.md §Technical Spec §TimeRangeTabs spec
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";

type Range = "1h" | "24h" | "7d" | "30d";
const RANGES: Range[] = ["1h", "24h", "7d", "30d"];

export function TimeRangeTabs() {
  const { t } = useTranslation("common");
  const [active, setActive] = useState<Range>("24h");
  return (
    <div
      role="tablist"
      aria-label={t("sla.range.label")}
      data-testid="sla-range-tabs"
      className="inline-flex items-center rounded-md border border-border bg-bg-1 p-0.5"
    >
      {RANGES.map((r) => {
        const isActive = active === r;
        return (
          <button
            key={r}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => setActive(r)}
            data-testid={`sla-range-tab-${r}`}
            className={
              isActive
                ? "rounded-sm bg-bg-2 px-3 py-1 text-xs font-medium text-foreground"
                : "rounded-sm px-3 py-1 text-xs text-fg-muted transition hover:text-foreground"
            }
          >
            {t(`sla.range.${r}`)}
          </button>
        );
      })}
    </div>
  );
}
