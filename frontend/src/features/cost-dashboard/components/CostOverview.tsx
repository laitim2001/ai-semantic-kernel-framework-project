/**
 * File: frontend/src/features/cost-dashboard/components/CostOverview.tsx
 * Purpose: Cost Dashboard top-level container — month picker + total + breakdown table.
 * Category: Frontend / cost-dashboard / components
 * Scope: Phase 57 / Sprint 57.1 US-2 (initial) → Sprint 57.7 US-B3 (migrate to AppShell + Tailwind)
 *
 * Description:
 *   Reads tenant_id from URL query string `?tenant_id=...` for now (admin-driven
 *   per D8 — backend enforces require_admin_platform_role; admin selects tenant).
 *   Auto-loads on mount + on month change. Loading skeleton + error retry UX.
 *
 *   Sprint 57.7 US-B3 migration: replaced inline `style={{}}` with Tailwind
 *   utility classes (per .claude/rules/frontend-react.md "no inline styles");
 *   wrapped in AppShell layout; MonthPicker hoisted into headerActions slot.
 *   useQuery TanStack migration deferred — store-based loadData pattern
 *   preserves existing 4 Vitest tests + 1 Playwright e2e (regression sentinel).
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 1)
 * Last Modified: 2026-05-10
 *
 * Modification History:
 *   - 2026-05-10: Sprint 57.7 US-B3 — migrate to AppShell + Tailwind utility classes
 *   - 2026-05-06: Initial creation (Sprint 57.1 Day 1 / US-2 — Cost overview)
 */

import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";

import { AppShell } from "../../../components/AppShell";
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
    <AppShell
      headerActions={
        <MonthPicker value={currentMonth} onChange={setMonth} disabled={loading} />
      }
    >
      <div className="space-y-4">
        <header>
          <h1 className="text-2xl font-semibold tracking-tight">Cost Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Per-tenant cost ledger summary. Backend enforces admin-platform role
            (Sprint 56.3 endpoint). 401/403 surfaces as error below.
          </p>
        </header>

        {!tenantId && (
          <p className="text-sm text-destructive">
            Missing <code className="rounded bg-muted px-1 py-0.5">?tenant_id=...</code> query parameter.
          </p>
        )}

        {loading && (
          <p className="text-sm italic text-muted-foreground">Loading cost summary…</p>
        )}

        {error && (
          <div
            role="alert"
            className="rounded-lg border border-destructive/40 bg-destructive/5 p-4"
          >
            <p className="text-sm text-destructive">Error: {error}</p>
            <button
              onClick={() => tenantId && void loadData(tenantId)}
              className="mt-3 inline-flex items-center rounded-md border border-border bg-background px-3 py-1.5 text-sm font-medium hover:bg-muted"
            >
              Retry
            </button>
          </div>
        )}

        {data && !loading && !error && (
          <>
            <p className="text-lg">
              <strong>Total cost ({data.month}):</strong> ${data.total_cost_usd}
            </p>
            <CostBreakdownTable data={data} />
          </>
        )}
      </div>
    </AppShell>
  );
}
