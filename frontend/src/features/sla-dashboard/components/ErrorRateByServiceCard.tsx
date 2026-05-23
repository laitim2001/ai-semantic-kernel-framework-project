/**
 * File: frontend/src/features/sla-dashboard/components/ErrorRateByServiceCard.tsx
 * Purpose: Per-service error rate card (Sprint 57.25 Day 2 US-C3; Sprint 57.32 Day 3 US-D2 verbatim re-point).
 * Category: Frontend / sla-dashboard / components (feature-scoped)
 * Scope: Phase 57 / Sprint 57.32 Day 3 US-D2 (Phase-2 verbatim re-point on Sprint 57.25 strict-rebuild scaffolding)
 *
 * Description:
 *   Verbatim port of reference/design-mockups/page-admin.jsx:131-152.
 *   6 rows × service + rate% + .bar-track; rate > 0.5 triggers warning tone.
 *
 *   Sprint 57.32 Day 3 US-D2: Phase-2 verbatim CSS re-point. CardShell →
 *   mockup-ui Card. Outer flex container Tailwind 'flex flex-col gap-2.5'
 *   → mockup `.col` + inline style={{ gap: 10 }}. Per-row header Tailwind
 *   'mb-1 flex items-center justify-between' → mockup `.spread` + inline
 *   style={{ marginBottom: 3 }}. Service name Tailwind 'font-mono text-[11.5px]'
 *   → mockup `.mono` + inline style={{ fontSize: 11.5 }}. Rate % uses
 *   Hybrid Tailwind+inline color bridge (text-warning/text-fg-muted Tailwind
 *   classes preserved alongside inline style color verbatim per Sprint 57.31
 *   TenantTopTable precedent for Vitest contract continuity); mockup `.mono
 *   .tnum` added; inline style for fontSize + color. <BarTrack pct={...}
 *   tone={...}> → verbatim <div className="bar-track"><span style={{ width:
 *   min(100, rate * 50)%, background: warn ? warning : success }} /></div>.
 *
 *   BarTrack width = rate × 50 (mockup line 147 algorithm — scales 0-2%
 *   range to full bar width); tone warning when > 0.5, success otherwise.
 *
 *   Backend per-service error rate aggregation pending Phase 58+
 *   AD-SLA-Dashboard-Backend-Extensions; BackendGapBanner preserved per
 *   AP-2 honesty.
 *
 * Created: 2026-05-19 (Sprint 57.25 Day 2 US-C3)
 * Last Modified: 2026-05-24
 *
 * Modification History:
 *   - 2026-05-24: Sprint 57.32 Day 3 US-D2 — verbatim re-point: Card + .col + .spread + .mono .tnum + .bar-track + Hybrid Tailwind+inline color bridge (drop CardShell + BarTrack + cn util)
 *   - 2026-05-19: Initial creation (Sprint 57.25 Day 2 US-C3)
 *
 * Related:
 *   - reference/design-mockups/page-admin.jsx:131-152 (canonical mockup)
 *   - frontend/src/styles-mockup.css (.col / .spread / .mono .tnum / .bar-track)
 *   - frontend/src/components/mockup-ui.tsx (Card primitive)
 */

/* eslint-disable no-restricted-syntax -- verbatim re-point: inline style literals (gap, marginBottom, fontSize, color, width, background) are copied byte-for-byte from mockup page-admin.jsx:131-152 escape-hatch. */

import { useTranslation } from "react-i18next";

import { Card } from "../../../components/mockup-ui";
import { BackendGapBanner } from "../../../components/ui/BackendGapBanner";
import { ERROR_RATE_BY_SERVICE } from "../__fixtures__/errorRateByService";

const WARNING_THRESHOLD_PCT = 0.5;
const BAR_WIDTH_SCALE = 50; // mockup line 147: width = rate * 50

export function ErrorRateByServiceCard() {
  const { t } = useTranslation("common");

  return (
    <div data-testid="sla-error-rate-card-wrap">
      <Card title={t("sla.errorRate.title")} subtitle={t("sla.errorRate.subtitle")}>
        <div className="col" style={{ gap: 10 }} data-testid="sla-error-rate-card">
          {ERROR_RATE_BY_SERVICE.map((row, idx) => {
            const warn = row.rate > WARNING_THRESHOLD_PCT;
            return (
              <div key={row.name} data-testid={`sla-error-rate-row-${idx}`}>
                <div className="spread" style={{ marginBottom: 3 }}>
                  <span className="mono" style={{ fontSize: 11.5 }}>{row.name}</span>
                  <span
                    className={`mono tnum ${warn ? "text-warning" : "text-fg-muted"}`}
                    style={{
                      fontSize: 11,
                      color: warn ? "var(--warning)" : "var(--fg-muted)",
                    }}
                    data-testid={`sla-error-rate-pct-${idx}`}
                  >
                    {row.rate.toFixed(2)}%
                  </span>
                </div>
                <div className="bar-track">
                  <span
                    style={{
                      width: Math.min(100, row.rate * BAR_WIDTH_SCALE) + "%",
                      background: warn ? "var(--warning)" : "var(--success)",
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </Card>
      <BackendGapBanner reason={t("sla.banner.perServiceErrorRate")} />
    </div>
  );
}
