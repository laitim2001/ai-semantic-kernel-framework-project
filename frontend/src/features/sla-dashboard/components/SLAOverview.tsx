/**
 * File: frontend/src/features/sla-dashboard/components/SLAOverview.tsx
 * Purpose: SLA Dashboard top-level container — mockup-fidelity rebuild (Sprint 57.25).
 * Category: Frontend / sla-dashboard / components
 * Scope: Phase 57 / Sprint 57.25 Day 1 US-B1+B2+B3 (subsequent USs replace legacy MetricsCard block with SLO + slow ops + error rate cards)
 *
 * Description:
 *   Sprint 57.25 incremental rebuild from Sprint 57.16 6-MetricsCard layout
 *   toward 6-widget-group mockup-fidelity layout per
 *   reference/design-mockups/page-admin.jsx:31-199 (SlaPage).
 *
 *   Day 1 (this state): + §1 page-head (PageHead + TimeRangeTabs + Refresh
 *   + Export stubs; US-B1) + §2 4-stat sparkline grid (StatCard + Spark
 *   reused; US-B2) + §3 24h LatencyChart 3-series SVG inside CardShell +
 *   BackendGapBanner (US-B3). Legacy MonthPicker preserved as auxiliary
 *   per user Q1 alignment with sibling note. Legacy violations Badge +
 *   6-SLAMetricsCard block kept transitionally at bottom; Day 2 deletes
 *   them and replaces with SLO status card + slow ops table + error rate
 *   card.
 *
 *   Backend reused: useSLAReport TanStack hook + GET /api/v1/sla-report
 *   (Sprint 57.9 US-6 Day 4 stable). 3 of 4 stat cards fixture-driven per
 *   D-PRE-2 (useSLAReport returns only _p99 fields; no p50/p95 split, no
 *   error_budget). LatencyChart 24h time-series fully fixture pending
 *   Phase 58+ backend (AD-SLA-Dashboard-Backend-Extensions).
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 2)
 * Last Modified: 2026-05-19
 *
 * Modification History (newest-first):
 *   - 2026-05-19: Sprint 57.25 Day 1 US-B1+B2+B3 — PageHead + TimeRangeTabs + 4-stat sparkline + LatencyChart card (mockup rebuild start)
 *   - 2026-05-11: Sprint 57.16 — inline styles → Tailwind utility classes (AD-Inline-Style-Cleanup-Sweep-Round2)
 *   - 2026-05-10: Sprint 57.13 US-B2 — loading → <CardSkeleton>; error → <ErrorRetry> (components/ui)
 *   - 2026-05-10: Sprint 57.13 US-A2 — tenant_id from authStore.tenant.id (was URL ?tenant_id=)
 *   - 2026-05-09: Sprint 57.9 US-6 Day 4 — migrate to useSLAReport TanStack hook + Tailwind utilities (drop inline styles)
 *   - 2026-05-06: Initial creation (Sprint 57.1 Day 2 / US-3 — SLA overview)
 *
 * Related:
 *   - reference/design-mockups/page-admin.jsx:31-199 (SlaPage canonical mockup)
 *   - frontend/src/components/ui/PageHead.tsx (US-B1 reuse)
 *   - frontend/src/components/charts/{Spark, StatCard, AreaChart, BarTrack}.tsx (US-B2/B3 reuse)
 *   - frontend/src/components/ui/{CardShell, BackendGapBanner}.tsx (US-B3 reuse)
 *   - frontend/src/features/sla-dashboard/components/{TimeRangeTabs, LatencyChart}.tsx (US-B1/B3 NEW feature-scoped)
 *   - sprint-57-25-plan.md §Technical Specifications
 */

import { useTranslation } from "react-i18next";

import { Spark, StatCard } from "../../../components/charts";
import { CardSkeleton, ErrorRetry } from "../../../components/ui";
import { BackendGapBanner } from "../../../components/ui/BackendGapBanner";
import { Button } from "../../../components/ui/button";
import { CardShell } from "../../../components/ui/CardShell";
import { PageHead } from "../../../components/ui/PageHead";
import { cn } from "../../../lib/utils";
import { useAuthStore } from "../../auth/store/authStore";
import { MonthPicker } from "../../cost-dashboard/components/MonthPicker";
import {
  SPARK_ERROR_BUDGET,
  SPARK_P50,
  SPARK_P95,
  SPARK_P99,
} from "../__fixtures__/statSparklines";
import { useSLAReport } from "../hooks/useSLAReport";
import { useSLAStore } from "../store/slaStore";
import { LatencyChart } from "./LatencyChart";
import { SLAMetricsCard } from "./SLAMetricsCard";
import { TimeRangeTabs } from "./TimeRangeTabs";

const AVAILABILITY_THRESHOLD_STANDARD = 99.5;

const API_P99_MAX_MS = 1000;
const LOOP_SIMPLE_P99_MAX_MS = 5000;
const LOOP_MEDIUM_P99_MAX_MS = 30000;
const LOOP_COMPLEX_P99_MAX_MS = 120000;
const HITL_QUEUE_NOTIF_P99_MAX_MS = 60000;

export function SLAOverview() {
  const { t } = useTranslation("common");
  const tenantId = useAuthStore((s) => s.tenant?.id ?? "");
  const currentMonth = useSLAStore((s) => s.currentMonth);
  const setMonth = useSLAStore((s) => s.setMonth);

  const { data, isLoading, isFetching, error, refetch } = useSLAReport(tenantId, currentMonth);

  // Sprint 57.25 Day 1 US-B2 — derive p99 stat value from real backend
  // when available, else fixture (matches mockup demo value 4.21s).
  const p99Seconds = data?.api_p99_ms != null ? (data.api_p99_ms / 1000).toFixed(2) : "4.21";

  return (
    <div className="space-y-4">
      {/* §1 page-head (US-B1). TimeRangeTabs visual-only; Refresh wires to
          useSLAReport.refetch; Export disabled stub per AP-2 honesty. */}
      <PageHead
        title={t("sla.pageTitle")}
        subtitle={t("sla.pageSub")}
        routePath="/sla-dashboard"
        actions={
          <>
            <TimeRangeTabs />
            <Button
              variant="outline"
              size="sm"
              onClick={() => void refetch()}
              disabled={isFetching || !tenantId}
              data-testid="sla-action-refresh"
            >
              {t("sla.action.refresh")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled
              title={t("sla.action.exportPending")}
              data-testid="sla-action-export"
            >
              {t("sla.action.export")}
            </Button>
          </>
        }
      />

      {/* MonthPicker auxiliary control (mockup doesn't show it; user Q1
          alignment keeps inline + sibling note). */}
      <div className="flex flex-wrap items-center gap-3">
        <MonthPicker value={currentMonth} onChange={setMonth} disabled={isFetching} />
        <span
          className="text-[11.5px] text-fg-muted"
          data-testid="sla-month-picker-aux-note"
        >
          {t("sla.monthPickerAuxiliary")}
        </span>
      </div>

      {!tenantId && (
        <p className="text-sm text-destructive">No tenant in your session.</p>
      )}

      {/* §2 4-stat sparkline grid (US-B2). p99 derives from real
          data.api_p99_ms when available; p50/p95/error_budget fully
          fixture per D-PRE-2 (backend doesn't expose those fields).
          AP-2 honesty: LatencyChart banner below covers the missing
          fields aggregate; per-card banners would be noisy. */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4" data-testid="sla-stat-grid">
        <StatCard
          label={t("sla.stat.p50")}
          value="284"
          unit="ms"
          delta="-18ms"
          deltaDir="up"
          spark={<Spark points={SPARK_P50} tone="hsl(var(--primary))" />}
        />
        <StatCard
          label={t("sla.stat.p95")}
          value="1.84"
          unit="s"
          delta="-180ms"
          deltaDir="up"
          spark={<Spark points={SPARK_P95} tone="hsl(var(--info))" />}
        />
        <StatCard
          label={t("sla.stat.p99")}
          value={p99Seconds}
          unit="s"
          delta="+0.30s"
          deltaDir="down"
          spark={<Spark points={SPARK_P99} tone="hsl(var(--warning))" />}
        />
        <StatCard
          label={t("sla.stat.errorBudget")}
          value="92.4"
          unit="%"
          delta="-1.2pp"
          deltaDir="down"
          spark={<Spark points={SPARK_ERROR_BUDGET} tone="hsl(var(--success))" />}
        />
      </div>

      {/* §3 24h LatencyChart 3-series (US-B3). NEW feature-scoped
          LatencyChart per Karpathy §2 inline rule. Backend 24h
          aggregation pending Phase 58+ — banner declares fixture. */}
      <CardShell
        title={t("sla.latencyChart.title")}
        subtitle={t("sla.latencyChart.subtitle")}
        actions={
          <div className="flex items-center gap-3 text-[11px]" data-testid="sla-latency-chart-kbar">
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-primary" />
              {t("sla.latencyChart.badge.p50")}
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-info" />
              {t("sla.latencyChart.badge.p95")}
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-warning" />
              {t("sla.latencyChart.badge.p99")}
            </span>
          </div>
        }
      >
        <LatencyChart />
        <BackendGapBanner reason={t("sla.banner.latencyChart24h")} />
      </CardShell>

      {/* Loading + error states (preserved from Sprint 57.13 baseline). */}
      {isLoading && tenantId && <CardSkeleton count={3} />}

      {error && (
        <div role="alert">
          <ErrorRetry error={error} onRetry={() => void refetch()} />
        </div>
      )}

      {/* §4-§6 legacy MetricsCard block — TRANSITIONAL (Sprint 57.25 Day 1).
          Replaced Day 2 by SLO status card + slow ops table + error rate
          card. Kept here so existing tests + behavior preserved during
          incremental Day 1+2 split. */}
      {data && !isLoading && !error && (
        <>
          <div>
            <span
              data-testid="violations-badge"
              className={cn(
                "inline-block rounded-full px-3 py-1.5 font-bold",
                data.violations_count > 0
                  ? "bg-destructive/10 text-destructive"
                  : "bg-[#e6f4ea] text-[#1a7f37]",
              )}
            >
              Violations: {data.violations_count}
            </span>
          </div>

          <div className="flex flex-wrap gap-4">
            <SLAMetricsCard
              label="Availability"
              value={data.availability_pct}
              threshold={AVAILABILITY_THRESHOLD_STANDARD}
              unit="%"
              mode="gte"
            />
            <SLAMetricsCard
              label="API p99"
              value={data.api_p99_ms}
              threshold={API_P99_MAX_MS}
              unit="ms"
              mode="lte"
            />
            <SLAMetricsCard
              label="Loop simple p99"
              value={data.loop_simple_p99_ms}
              threshold={LOOP_SIMPLE_P99_MAX_MS}
              unit="ms"
              mode="lte"
            />
            <SLAMetricsCard
              label="Loop medium p99"
              value={data.loop_medium_p99_ms}
              threshold={LOOP_MEDIUM_P99_MAX_MS}
              unit="ms"
              mode="lte"
            />
            <SLAMetricsCard
              label="Loop complex p99"
              value={data.loop_complex_p99_ms}
              threshold={LOOP_COMPLEX_P99_MAX_MS}
              unit="ms"
              mode="lte"
            />
            <SLAMetricsCard
              label="HITL queue notif p99"
              value={data.hitl_queue_notif_p99_ms}
              threshold={HITL_QUEUE_NOTIF_P99_MAX_MS}
              unit="ms"
              mode="lte"
            />
          </div>
        </>
      )}
    </div>
  );
}
