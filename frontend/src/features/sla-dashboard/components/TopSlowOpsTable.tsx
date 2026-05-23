/**
 * File: frontend/src/features/sla-dashboard/components/TopSlowOpsTable.tsx
 * Purpose: Top slow operations table (Sprint 57.25 Day 2 US-C2; Sprint 57.32 Day 3 US-D1 verbatim re-point).
 * Category: Frontend / sla-dashboard / components (feature-scoped)
 * Scope: Phase 57 / Sprint 57.32 Day 3 US-D1 (Phase-2 verbatim re-point on Sprint 57.25 strict-rebuild scaffolding)
 *
 * Description:
 *   Verbatim port of reference/design-mockups/page-admin.jsx:104-129.
 *   6-row table × Operation + Kind Badge + p50/p95/p99 + Calls.
 *
 *   Sprint 57.32 Day 3 US-D1: Phase-2 verbatim CSS re-point. CardShell →
 *   mockup-ui Card with bodyClass='flush'. Table Tailwind 'w-full border-
 *   collapse text-left text-[12px]' → mockup `.table` class (styles-mockup.css
 *   cascade supplies layout). Per-row td translations:
 *   - Operation: 'px-4 py-2 font-mono text-[11.5px]' → `.mono` + inline
 *     style={{ fontSize: 11.5 }}
 *   - Kind: shadcn-style Badge ('inline-flex items-center rounded-md ...' +
 *     KIND_TONE_CLASS map) → mockup-ui <Badge tone={KIND_TONE_MAP[kind]}>
 *   - p50/p95: 'px-4 py-2 text-right font-mono tabular-nums' → `.mono .tnum`
 *     + inline style={{ textAlign: 'right' }}
 *   - p99: Hybrid Tailwind+inline color bridge (text-warning/text-fg-muted
 *     Tailwind classes preserved alongside inline style color verbatim per
 *     Sprint 57.31 TenantTopTable precedent for Vitest contract continuity);
 *     mockup `.mono .tnum` added; inline style for textAlign + color.
 *   - Calls: 'px-4 py-2 text-right font-mono tabular-nums text-fg-subtle' →
 *     `.mono .tnum .subtle` + inline style={{ textAlign: 'right' }}.
 *
 *   Kind Badge tone mapping (mockup page-admin.jsx:120 inline conditional):
 *   - tool → 'tool' / loop → 'primary' / subagent → 'thinking' /
 *     verify → 'success' / memory → 'memory'.
 *
 *   p99 column color: > 3000ms → warning; else fg-muted.
 *
 *   Backend cross-operation p99 aggregation pending Phase 58+
 *   AD-SLA-Dashboard-Backend-Extensions; BackendGapBanner preserved
 *   per AP-2 honesty.
 *
 * Created: 2026-05-19 (Sprint 57.25 Day 2 US-C2)
 * Last Modified: 2026-05-24
 *
 * Modification History:
 *   - 2026-05-24: Sprint 57.32 Day 3 US-D1 — verbatim re-point: Card bodyClass=flush + .table + .mono + .tnum + .subtle + mockup-ui Badge tone dispatch + Hybrid Tailwind+inline color bridge (drop CardShell + cn util + shadcn badge class map)
 *   - 2026-05-19: Initial creation (Sprint 57.25 Day 2 US-C2)
 *
 * Related:
 *   - reference/design-mockups/page-admin.jsx:104-129 (canonical mockup)
 *   - frontend/src/styles-mockup.css (.table / .mono / .tnum / .subtle)
 *   - frontend/src/components/mockup-ui.tsx (Card + Badge primitives)
 */

/* eslint-disable no-restricted-syntax -- verbatim re-point: inline style literals (fontSize, textAlign, color) are copied byte-for-byte from mockup page-admin.jsx:104-129 escape-hatch. */

import { useTranslation } from "react-i18next";

import { Badge, Card } from "../../../components/mockup-ui";
import { BackendGapBanner } from "../../../components/ui/BackendGapBanner";
import { SLOW_OPS, type OpKind } from "../__fixtures__/slowOps";

const KIND_TONE_MAP: Record<OpKind, string> = {
  tool: "tool",
  loop: "primary",
  subagent: "thinking",
  verify: "success",
  memory: "memory",
};

const P99_WARNING_THRESHOLD_MS = 3000;

export function TopSlowOpsTable() {
  const { t } = useTranslation("common");

  return (
    <div data-testid="sla-slow-ops-table-wrap">
      <Card
        title={t("sla.slowOps.title")}
        subtitle={t("sla.slowOps.subtitle")}
        bodyClass="flush"
      >
        <table className="table" data-testid="sla-slow-ops-table">
          <thead>
            <tr>
              <th>{t("sla.slowOps.col.operation")}</th>
              <th>{t("sla.slowOps.col.kind")}</th>
              <th style={{ textAlign: "right" }}>{t("sla.slowOps.col.p50")}</th>
              <th style={{ textAlign: "right" }}>{t("sla.slowOps.col.p95")}</th>
              <th style={{ textAlign: "right" }}>{t("sla.slowOps.col.p99")}</th>
              <th style={{ textAlign: "right" }}>{t("sla.slowOps.col.calls")}</th>
            </tr>
          </thead>
          <tbody>
            {SLOW_OPS.map((row, idx) => {
              const p99Warning = row.p99 > P99_WARNING_THRESHOLD_MS;
              return (
                <tr key={row.name} data-testid={`sla-slow-ops-row-${idx}`}>
                  <td className="mono" style={{ fontSize: 11.5 }}>{row.name}</td>
                  <td>
                    <Badge tone={KIND_TONE_MAP[row.kind]}>
                      <span data-testid={`sla-slow-ops-kind-${idx}`} data-kind={row.kind}>
                        {row.kind}
                      </span>
                    </Badge>
                  </td>
                  <td className="mono tnum" style={{ textAlign: "right" }}>{row.p50}ms</td>
                  <td className="mono tnum" style={{ textAlign: "right" }}>{row.p95}ms</td>
                  <td
                    className={`mono tnum ${p99Warning ? "text-warning" : "text-fg-muted"}`}
                    style={{
                      textAlign: "right",
                      color: p99Warning ? "var(--warning)" : "var(--fg-muted)",
                    }}
                    data-testid={`sla-slow-ops-p99-${idx}`}
                  >
                    {row.p99}ms
                  </td>
                  <td className="mono tnum subtle" style={{ textAlign: "right" }}>
                    {row.calls.toLocaleString()}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
      <BackendGapBanner reason={t("sla.banner.crossOperationP99")} />
    </div>
  );
}
