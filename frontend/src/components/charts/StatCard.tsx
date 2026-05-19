/**
 * File: frontend/src/components/charts/StatCard.tsx
 * Purpose: Mockup-fidelity stat card — label + value + unit + delta + sparkline slot.
 * Category: Frontend / components / charts (design-system layer)
 * Scope: Phase 57 / Sprint 57.24 Day 1 US-B2 (1st consumer: /cost-dashboard 4-stat grid)
 *
 * Description:
 *   Mockup-direct port of reference/design-mockups/ui.jsx:99-113 (Stat helper)
 *   + styles.css:489-504 (.stat / .stat-label / .stat-value / .stat-delta /
 *   .stat-spark CSS rules).
 *
 *   `deltaDir` is INTERPRETATION tone, not arrow direction:
 *   - "up"   = positive interpretation (good change)   → text-success + ArrowUp
 *   - "down" = negative interpretation (bad change)    → text-danger  + ArrowDown
 *   Caller decides semantic meaning per metric (e.g. "Spend +8.4%" uses
 *   deltaDir="down" because spending more is bad).
 *
 *   Tailwind translation of mockup styles.css:489-504:
 *   - .stat → relative + flex-col + gap-2 + rounded-[10px] + border + bg-bg-1 + px-4 py-3.5
 *   - .stat-label → text-[11.5px] text-fg-muted flex justify-between items-center
 *   - .stat-value → text-2xl font-semibold tracking-[-0.02em] tabular-nums
 *   - .stat-value .unit → ml-1 text-[13px] font-normal text-fg-muted
 *   - .stat-delta → font-mono text-[10.5px] inline-flex gap-[3px] items-center
 *   - .stat-spark → absolute bottom-2.5 right-3 opacity-60
 *
 * Created: 2026-05-19 (Sprint 57.24 Day 1 US-B2)
 * Last Modified: 2026-05-19
 *
 * Modification History (newest-first):
 *   - 2026-05-19: Initial creation (Sprint 57.24 Day 1 US-B2) — 1st consumer cost-dashboard
 *
 * Related:
 *   - reference/design-mockups/ui.jsx:99-113 (Stat canonical mockup)
 *   - reference/design-mockups/styles.css:489-504 (.stat CSS rules)
 *   - frontend/src/components/charts/Spark.tsx (typical spark slot occupant)
 */

import { ArrowDown, ArrowUp } from "lucide-react";
import type { FC, ReactNode } from "react";

export interface StatCardProps {
  label: ReactNode;
  value: ReactNode;
  unit?: string;
  delta?: string;
  deltaDir?: "up" | "down";
  spark?: ReactNode;
}

export const StatCard: FC<StatCardProps> = ({
  label,
  value,
  unit,
  delta,
  deltaDir = "up",
  spark,
}) => (
  <div
    data-testid="stat-card"
    className="relative flex flex-col gap-2 rounded-[10px] border border-border bg-bg-1 px-4 py-3.5"
  >
    <div className="flex items-center justify-between text-[11.5px] text-fg-muted">
      <span>{label}</span>
      {delta && (
        <span
          data-testid="stat-delta"
          data-direction={deltaDir}
          className={`inline-flex items-center gap-[3px] font-mono text-[10.5px] ${
            deltaDir === "up" ? "text-success" : "text-danger"
          }`}
        >
          {deltaDir === "up" ? <ArrowUp size={10} /> : <ArrowDown size={10} />}
          {delta}
        </span>
      )}
    </div>
    <div className="text-2xl font-semibold tracking-[-0.02em] tabular-nums">
      {value}
      {unit && (
        <span className="ml-1 text-[13px] font-normal text-fg-muted">{unit}</span>
      )}
    </div>
    {spark && <div className="absolute bottom-2.5 right-3 opacity-60">{spark}</div>}
  </div>
);
