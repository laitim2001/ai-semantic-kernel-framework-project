/**
 * File: frontend/src/features/cost-dashboard/components/CostOverview.tsx
 * Purpose: Cost Dashboard top-level container — mockup-fidelity rebuild (Sprint 57.24 v2).
 * Category: Frontend / cost-dashboard / components
 * Scope: Phase 57 / Sprint 57.24 Day 1 US-B1 (page-head + page-actions; subsequent USs add stat grid / area chart / category bars / tenant table / provider mix)
 *
 * Description:
 *   Sprint 57.24 v2 incremental rebuild from 68-line MVP toward 6-widget-group
 *   mockup-fidelity layout per reference/design-mockups/page-admin.jsx:200-321 (CostPage).
 *
 *   Day 1.1 US-B1 (this state): PageHead added at top with title + subtitle +
 *   route-pill + admin scope Badge (gated on isPlatformAdmin via authStore.roles)
 *   + page-actions row (By tenant + CSV stubs disabled with tooltip pending
 *   backend API per AP-2 honesty). Existing Total cost + CostBreakdownTable
 *   preserved below temporarily; Day 2 US-C1 supersedes with CategoryBarsCard.
 *
 *   Backend reused: useCostSummary TanStack hook + GET /api/v1/cost-summary
 *   (Sprint 57.9 US-6 Day 4 stable).
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 1)
 * Last Modified: 2026-05-19
 *
 * Modification History (newest-first):
 *   - 2026-05-19: Sprint 57.24 Day 1 US-B1 — PageHead + admin scope gate + page-actions stubs (rebuild start)
 *   - 2026-05-11: Sprint 57.15 — inline styles → Tailwind utility classes (AD-Inline-Style-Cleanup-Sweep)
 *   - 2026-05-10: Sprint 57.13 US-B2 — loading → <CardSkeleton>; error → <ErrorRetry> (components/ui)
 *   - 2026-05-10: Sprint 57.13 US-A2 — tenant_id from authStore.tenant.id (was URL ?tenant_id=)
 *   - 2026-05-09: Sprint 57.9 US-6 Day 4 — migrate to useCostSummary TanStack hook (drop store loadData/data/loading/error)
 *   - 2026-05-10: Sprint 57.7 US-B3 — migrate to AppShell + Tailwind utility classes
 *   - 2026-05-06: Initial creation (Sprint 57.1 Day 1 / US-2 — Cost overview)
 *
 * Related:
 *   - reference/design-mockups/page-admin.jsx:200-321 (CostPage canonical mockup)
 *   - frontend/src/components/ui/PageHead.tsx (US-B1 NEW primitive)
 *   - sprint-57-24-plan.md v2 §Technical Specifications
 */

import { useTranslation } from "react-i18next";

import { Button } from "../../../components/ui/button";
import { CardSkeleton, ErrorRetry } from "../../../components/ui";
import { PageHead } from "../../../components/ui/PageHead";
import { useAuthStore } from "../../auth/store/authStore";
import { useCostSummary } from "../hooks/useCostSummary";
import { useCostStore } from "../store/costStore";
import { CostBreakdownTable } from "./CostBreakdownTable";

// Mirrors backend _ADMIN_PLATFORM_ROLES (platform_layer/identity/auth.py); same
// pattern as AdminTenantsPage. Used to gate the admin-only scope Badge in the
// page-head and (Day 1.4-Day 2) the cross-tenant + cross-provider widgets.
const PLATFORM_ADMIN_ROLES = ["admin", "platform_admin"];

export function CostOverview() {
  const { t } = useTranslation("common");
  const tenantId = useAuthStore((s) => s.tenant?.id ?? "");
  const roles = useAuthStore((s) => s.roles);
  const isPlatformAdmin = roles.some((r) => PLATFORM_ADMIN_ROLES.includes(r));
  const currentMonth = useCostStore((s) => s.currentMonth);

  const { data, isLoading, error, refetch } = useCostSummary(tenantId, currentMonth);

  return (
    <div className="space-y-4">
      <PageHead
        title={t("cost.pageTitle")}
        subtitle={t("cost.pageSub")}
        routePath="/cost-dashboard"
        badges={
          isPlatformAdmin && (
            <span
              data-testid="cost-admin-scope-badge"
              className="inline-flex items-center rounded-full bg-warning/15 px-2 py-[2px] text-[10.5px] font-medium uppercase tracking-wide text-warning"
            >
              {t("cost.adminScope")}
            </span>
          )
        }
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              disabled
              title={t("cost.action.filterPending")}
              data-testid="cost-action-by-tenant"
            >
              {t("cost.action.byTenant")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled
              title={t("cost.action.csvPending")}
              data-testid="cost-action-csv"
            >
              {t("cost.action.csv")}
            </Button>
          </>
        }
      />

      {!tenantId && (
        <p className="text-sm text-destructive">No tenant in your session.</p>
      )}

      {isLoading && tenantId && <CardSkeleton count={3} />}

      {error && (
        <div role="alert">
          <ErrorRetry error={error} onRetry={() => void refetch()} />
        </div>
      )}

      {data && !isLoading && !error && (
        <>
          <p className="text-lg">
            <strong>Total cost ({data.month}):</strong> ${data.total_cost_usd}
          </p>
          <CostBreakdownTable data={data} />
        </>
      )}
    </div>
  );
}
