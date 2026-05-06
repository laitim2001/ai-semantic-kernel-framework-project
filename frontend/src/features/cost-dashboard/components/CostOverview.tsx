/**
 * File: frontend/src/features/cost-dashboard/components/CostOverview.tsx
 * Purpose: Cost Dashboard top-level container — month picker + total + breakdown table.
 * Category: Frontend / cost-dashboard / components
 * Scope: Phase 57 / Sprint 57.1 US-2
 *
 * Description:
 *   Reads tenant_id from URL query string `?tenant_id=...` for now (admin-driven
 *   per D8 — backend enforces require_admin_platform_role; admin selects tenant).
 *   Auto-loads on mount + on month change. Loading skeleton + error retry UX.
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 1)
 * Last Modified: 2026-05-06
 *
 * Modification History:
 *   - 2026-05-06: Initial creation (Sprint 57.1 Day 1 / US-2 — Cost overview)
 */

import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";

import { useCostStore } from "../store/costStore";
import { CostBreakdownTable } from "./CostBreakdownTable";
import { MonthPicker } from "./MonthPicker";

export function CostOverview() {
  const [searchParams] = useSearchParams();
  const tenantId = searchParams.get("tenant_id") ?? "";

  const { currentMonth, data, loading, error, setMonth, loadData } = useCostStore();

  useEffect(() => {
    if (tenantId) {
      void loadData(tenantId);
    }
  }, [tenantId, currentMonth, loadData]);

  return (
    <div style={{ padding: "2rem", fontFamily: "system-ui, sans-serif" }}>
      <h1>Cost Dashboard</h1>
      <p style={{ color: "#666", fontSize: "0.9rem" }}>
        Per-tenant cost ledger summary. Backend enforces admin-platform role
        (Sprint 56.3 endpoint). 401/403 surfaces as error below.
      </p>

      {!tenantId && (
        <p style={{ color: "#a00" }}>
          Missing <code>?tenant_id=...</code> query parameter.
        </p>
      )}

      <div style={{ marginTop: "1rem", marginBottom: "1rem" }}>
        <MonthPicker value={currentMonth} onChange={setMonth} disabled={loading} />
      </div>

      {loading && <p style={{ fontStyle: "italic" }}>Loading cost summary…</p>}

      {error && (
        <div style={{ marginTop: "1rem", padding: "1rem", border: "1px solid #a00", color: "#a00" }}>
          <p>Error: {error}</p>
          <button onClick={() => tenantId && void loadData(tenantId)}>Retry</button>
        </div>
      )}

      {data && !loading && !error && (
        <>
          <p style={{ fontSize: "1.2rem", marginTop: "1rem" }}>
            <strong>Total cost ({data.month}):</strong> ${data.total_cost_usd}
          </p>
          <CostBreakdownTable data={data} />
        </>
      )}
    </div>
  );
}
