/**
 * File: frontend/src/features/sla-dashboard/components/TopSlowOpsTable.tsx
 * Purpose: Top slow operations table (Sprint 57.25 Day 2 US-C2).
 * Category: Frontend / sla-dashboard / components (feature-scoped)
 * Scope: Phase 57 / Sprint 57.25 Day 2 US-C2
 *
 * Description:
 *   Mockup-direct port of reference/design-mockups/page-admin.jsx:104-129.
 *   6-row table × Operation + Kind Badge + p50/p95/p99 + Calls.
 *
 *   Kind Badge tone mapping (mockup line 120):
 *   - tool → tool / loop → primary / subagent → thinking / verify → success / memory → memory
 *
 *   p99 column color: > 3000ms → warning; else fg-muted.
 *
 *   Backend cross-operation p99 aggregation pending Phase 58+
 *   AD-SLA-Dashboard-Backend-Extensions; BackendGapBanner rendered below.
 *
 * Created: 2026-05-19 (Sprint 57.25 Day 2 US-C2)
 *
 * Modification History:
 *   - 2026-05-19: Initial creation (Sprint 57.25 Day 2 US-C2)
 *
 * Related:
 *   - reference/design-mockups/page-admin.jsx:104-129 (canonical mockup)
 *   - sprint-57-25-plan.md §Technical Spec §TopSlowOpsTable structure
 */

import { useTranslation } from "react-i18next";

import { BackendGapBanner } from "../../../components/ui/BackendGapBanner";
import { CardShell } from "../../../components/ui/CardShell";
import { cn } from "../../../lib/utils";
import { SLOW_OPS, type OpKind } from "../__fixtures__/slowOps";

const KIND_TONE_CLASS: Record<OpKind, string> = {
  tool: "bg-tool/15 text-tool",
  loop: "bg-primary/15 text-primary",
  subagent: "bg-thinking/15 text-thinking",
  verify: "bg-success/15 text-success",
  memory: "bg-memory/15 text-memory",
};

const P99_WARNING_THRESHOLD_MS = 3000;

export function TopSlowOpsTable() {
  const { t } = useTranslation("common");

  return (
    <div data-testid="sla-slow-ops-table-wrap">
      <CardShell
        title={t("sla.slowOps.title")}
        subtitle={t("sla.slowOps.subtitle")}
        bodyClass="p-0"
      >
        <table
          className="w-full border-collapse text-left text-[12px]"
          data-testid="sla-slow-ops-table"
        >
          <thead>
            <tr className="text-[11px] text-fg-subtle">
              <th className="border-b border-border px-4 py-2 font-medium">
                {t("sla.slowOps.col.operation")}
              </th>
              <th className="border-b border-border px-4 py-2 font-medium">
                {t("sla.slowOps.col.kind")}
              </th>
              <th className="border-b border-border px-4 py-2 text-right font-medium">
                {t("sla.slowOps.col.p50")}
              </th>
              <th className="border-b border-border px-4 py-2 text-right font-medium">
                {t("sla.slowOps.col.p95")}
              </th>
              <th className="border-b border-border px-4 py-2 text-right font-medium">
                {t("sla.slowOps.col.p99")}
              </th>
              <th className="border-b border-border px-4 py-2 text-right font-medium">
                {t("sla.slowOps.col.calls")}
              </th>
            </tr>
          </thead>
          <tbody>
            {SLOW_OPS.map((row, idx) => {
              const p99Warning = row.p99 > P99_WARNING_THRESHOLD_MS;
              return (
                <tr
                  key={row.name}
                  data-testid={`sla-slow-ops-row-${idx}`}
                  className="hover:bg-bg-hover/30"
                >
                  <td className="px-4 py-2 font-mono text-[11.5px]">{row.name}</td>
                  <td className="px-4 py-2">
                    <span
                      className={cn(
                        "inline-flex items-center rounded-md px-2 py-0.5 text-[10.5px] font-medium",
                        KIND_TONE_CLASS[row.kind],
                      )}
                      data-testid={`sla-slow-ops-kind-${idx}`}
                      data-kind={row.kind}
                    >
                      {row.kind}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">{row.p50}ms</td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">{row.p95}ms</td>
                  <td
                    className={cn(
                      "px-4 py-2 text-right font-mono tabular-nums",
                      p99Warning ? "text-warning" : "text-fg-muted",
                    )}
                    data-testid={`sla-slow-ops-p99-${idx}`}
                  >
                    {row.p99}ms
                  </td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums text-fg-subtle">
                    {row.calls.toLocaleString()}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </CardShell>
      <BackendGapBanner reason={t("sla.banner.crossOperationP99")} />
    </div>
  );
}
