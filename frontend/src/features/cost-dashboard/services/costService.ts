/**
 * File: frontend/src/features/cost-dashboard/services/costService.ts
 * Purpose: REST client for 56.3 admin cost-summary endpoint.
 * Category: Frontend / cost-dashboard / services
 * Scope: Phase 57 / Sprint 57.1 US-2
 *
 * Description:
 *   Wraps GET /api/v1/admin/tenants/{tenant_id}/cost-summary?month=YYYY-MM.
 *   Mirrors plain-fetch + _handleResponse<T> pattern from 53.5
 *   governanceService.ts (per Day 0 D6 — no axios / no React Query in V2 frontend).
 *   Auth: backend enforces require_admin_platform_role; frontend lets 401/403
 *   surface as Error and UI shows retry / permission message (per D10 Option C).
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 1)
 * Last Modified: 2026-05-06
 *
 * Modification History:
 *   - 2026-05-06: Initial creation (Sprint 57.1 Day 1 / US-2 — Cost Dashboard service)
 *
 * Related:
 *   - backend/src/api/v1/admin/cost_summary.py (endpoint)
 *   - ../types.ts (CostSummaryResponse)
 *   - frontend/src/features/governance/services/governanceService.ts (pattern reference)
 */

import type { CostSummaryResponse } from "../types";

const API_BASE = "/api/v1/admin";

async function _handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // ignore JSON parse failure; use status only
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export async function fetchCostSummary(
  tenantId: string,
  month: string,
): Promise<CostSummaryResponse> {
  const response = await fetch(
    `${API_BASE}/tenants/${tenantId}/cost-summary?month=${encodeURIComponent(month)}`,
    { credentials: "include" },
  );
  return _handleResponse<CostSummaryResponse>(response);
}
