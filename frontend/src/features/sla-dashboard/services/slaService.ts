/**
 * File: frontend/src/features/sla-dashboard/services/slaService.ts
 * Purpose: REST client for 56.3 admin sla-report endpoint.
 * Category: Frontend / sla-dashboard / services
 * Scope: Phase 57 / Sprint 57.1 US-3
 *
 * Description:
 *   Wraps GET /api/v1/admin/tenants/{tenant_id}/sla-report?month=YYYY-MM.
 *   Mirrors plain-fetch + _handleResponse<T> pattern from cost-dashboard /
 *   53.5 governanceService (per Day 0 D6). Backend enforces
 *   require_admin_platform_role per D8.
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 2)
 * Last Modified: 2026-05-06
 *
 * Modification History:
 *   - 2026-05-06: Initial creation (Sprint 57.1 Day 2 / US-3 — SLA Dashboard service)
 *
 * Related:
 *   - backend/src/api/v1/admin/sla_reports.py (endpoint)
 *   - ../types.ts (SLAReportResponse)
 *   - frontend/src/features/cost-dashboard/services/costService.ts (pattern reference)
 */

import type { SLAReportResponse } from "../types";

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

export async function fetchSLAReport(
  tenantId: string,
  month: string,
): Promise<SLAReportResponse> {
  const response = await fetch(
    `${API_BASE}/tenants/${tenantId}/sla-report?month=${encodeURIComponent(month)}`,
    { credentials: "include" },
  );
  return _handleResponse<SLAReportResponse>(response);
}
