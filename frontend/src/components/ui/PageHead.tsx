/**
 * File: frontend/src/components/ui/PageHead.tsx
 * Purpose: Reusable page-head primitive (title + subtitle + route-pill + badges slot + actions slot) for mockup-fidelity rebuilds.
 * Category: Frontend / components / ui (design-system layer)
 * Scope: Phase 57 / Sprint 57.24 Day 1 US-B1 (1st consumer: /cost-dashboard rebuild)
 *
 * Description:
 *   Mockup-direct port of `page-head` pattern per reference/design-mockups/page-admin.jsx:202-216
 *   (and identical pattern across page-overview / page-extras / page-auth-extras mockups).
 *
 *   API:
 *   - `title`: required main heading (string or ReactNode for icon flexibility)
 *   - `subtitle`: required descriptor line; route-pill + badges render inline within subtitle row
 *   - `routePath`: optional inline route-pill (e.g. "/cost-dashboard") shown after subtitle text
 *   - `badges`: optional slot for tone badges (e.g. admin scope) shown after route-pill
 *   - `actions`: optional slot for page-actions row (typically Button row aligned right)
 *
 *   Caller is responsible for passing Badge components with their own tone styling
 *   (matches Sprint 57.20 inline-tone pattern; no tone system coupling here).
 *
 *   Used by Sprint 57.24 /cost-dashboard rebuild; planned reuse by Sprint
 *   57.25-57.28 (/sla-dashboard / /admin/tenants / /verification /
 *   /tenant-settings rebuilds — see sprint-57-24-plan.md §Carryover).
 *
 * Created: 2026-05-19 (Sprint 57.24 Day 1 US-B1)
 * Last Modified: 2026-05-19
 *
 * Modification History (newest-first):
 *   - 2026-05-19: Initial creation (Sprint 57.24 Day 1 US-B1) — cost-dashboard rebuild 1st consumer
 *
 * Related:
 *   - reference/design-mockups/page-admin.jsx:202-216 (CostPage page-head canonical mockup)
 *   - frontend/src/pages/overview/OverviewPage.tsx (Sprint 57.20 inline Card/Badge pattern reference)
 *   - sprint-57-24-plan.md §Technical Specifications §CostOverview rewrite
 */

import type { FC, ReactNode } from "react";

export interface PageHeadProps {
  title: ReactNode;
  subtitle: ReactNode;
  routePath?: string;
  badges?: ReactNode;
  actions?: ReactNode;
}

export const PageHead: FC<PageHeadProps> = ({
  title,
  subtitle,
  routePath,
  badges,
  actions,
}) => (
  <div className="flex items-start justify-between gap-4">
    <div className="min-w-0 flex-1">
      <div className="text-lg font-semibold leading-tight">{title}</div>
      <div className="mt-1 flex flex-wrap items-center gap-2 text-[12.5px] text-fg-muted">
        <span>{subtitle}</span>
        {routePath && (
          <span className="inline-flex items-center rounded-md bg-bg-2 px-1.5 py-0.5 font-mono text-[10.5px] text-fg-subtle">
            {routePath}
          </span>
        )}
        {badges}
      </div>
    </div>
    {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
  </div>
);
