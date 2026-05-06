/**
 * File: frontend/src/features/sla-dashboard/components/SLAOverview.tsx
 * Purpose: SLA Dashboard top-level container — month picker + 6 metric cards + violations badge.
 * Category: Frontend / sla-dashboard / components
 * Scope: Phase 57 / Sprint 57.1 US-3
 *
 * Description:
 *   Reads tenant_id from URL query string (admin-driven per D8).
 *   Tier threshold: fallback to Standard 99.5% per Day 0 D10 (frontend has
 *   no tenant.plan accessible). Latency thresholds use sensible defaults
 *   (api 1000ms / loop simple 5000ms / loop medium 30000ms / loop complex
 *   120000ms / hitl_queue_notif 60000ms).
 *   Imports MonthPicker from cost-dashboard (Day 0 D — features/shared
 *   does not exist).
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 2)
 * Last Modified: 2026-05-06
 *
 * Modification History:
 *   - 2026-05-06: Initial creation (Sprint 57.1 Day 2 / US-3 — SLA overview)
 */

import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";

import { MonthPicker } from "../../cost-dashboard/components/MonthPicker";
import { useSLAStore } from "../store/slaStore";
import { SLAMetricsCard } from "./SLAMetricsCard";

const AVAILABILITY_THRESHOLD_STANDARD = 99.5; // Standard tier; Enterprise=99.9% (per 16-frontend-design.md / 15-saas-readiness.md)

// Latency thresholds (sensible defaults; not per-tier yet)
const API_P99_MAX_MS = 1000;
const LOOP_SIMPLE_P99_MAX_MS = 5000;
const LOOP_MEDIUM_P99_MAX_MS = 30000;
const LOOP_COMPLEX_P99_MAX_MS = 120000;
const HITL_QUEUE_NOTIF_P99_MAX_MS = 60000;

export function SLAOverview() {
  const [searchParams] = useSearchParams();
  const tenantId = searchParams.get("tenant_id") ?? "";

  const { currentMonth, data, loading, error, setMonth, loadData } = useSLAStore();

  useEffect(() => {
    if (tenantId) {
      void loadData(tenantId);
    }
  }, [tenantId, currentMonth, loadData]);

  return (
    <div style={{ padding: "2rem", fontFamily: "system-ui, sans-serif" }}>
      <h1>SLA Dashboard</h1>
      <p style={{ color: "#666", fontSize: "0.9rem" }}>
        Per-tenant SLA report. Backend enforces admin-platform role
        (Sprint 56.3 endpoint). Threshold fallback to Standard 99.5%
        availability — Enterprise tier display deferred (Day 0 D — frontend
        has no tenant.plan access).
      </p>

      {!tenantId && (
        <p style={{ color: "#a00" }}>
          Missing <code>?tenant_id=...</code> query parameter.
        </p>
      )}

      <div style={{ marginTop: "1rem", marginBottom: "1rem" }}>
        <MonthPicker value={currentMonth} onChange={setMonth} disabled={loading} />
      </div>

      {loading && <p style={{ fontStyle: "italic" }}>Loading SLA report…</p>}

      {error && (
        <div style={{ marginTop: "1rem", padding: "1rem", border: "1px solid #a00", color: "#a00" }}>
          <p>Error: {error}</p>
          <button onClick={() => tenantId && void loadData(tenantId)}>Retry</button>
        </div>
      )}

      {data && !loading && !error && (
        <>
          <div style={{ marginTop: "1rem", marginBottom: "1rem" }}>
            <span
              style={{
                display: "inline-block",
                padding: "0.5rem 1rem",
                borderRadius: "1rem",
                backgroundColor: data.violations_count > 0 ? "#fce8e6" : "#e6f4ea",
                color: data.violations_count > 0 ? "#a00" : "#1a7f37",
                fontWeight: "bold",
              }}
              data-testid="violations-badge"
            >
              Violations: {data.violations_count}
            </span>
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem", marginTop: "1rem" }}>
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
