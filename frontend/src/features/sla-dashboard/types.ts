/**
 * File: frontend/src/features/sla-dashboard/types.ts
 * Purpose: TypeScript interfaces mirroring 56.3 backend SLAReportResponse.
 * Category: Frontend / sla-dashboard / types
 * Scope: Phase 57 / Sprint 57.1 US-3 (Day 2 implementation)
 *
 * Description:
 *   Mirrors backend Pydantic schemas at backend/src/api/v1/admin/sla_reports.py.
 *   Flat fields per Day 0 verify (NOT nested like CostSummary by_type).
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 1 — skeleton; Day 2 fills)
 * Last Modified: 2026-05-06
 *
 * Modification History:
 *   - 2026-05-06: Initial creation as skeleton (Sprint 57.1 Day 1 / US-1 shared)
 */

export interface SLAReportResponse {
  tenant_id: string;
  month: string; // YYYY-MM
  availability_pct: number;
  api_p99_ms: number | null;
  loop_simple_p99_ms: number | null;
  loop_medium_p99_ms: number | null;
  loop_complex_p99_ms: number | null;
  hitl_queue_notif_p99_ms: number | null;
  violations_count: number;
}
