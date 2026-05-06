/**
 * File: frontend/src/features/cost-dashboard/types.ts
 * Purpose: TypeScript interfaces mirroring 56.3 backend CostSummaryResponse.
 * Category: Frontend / cost-dashboard / types
 * Scope: Phase 57 / Sprint 57.1 US-2
 *
 * Description:
 *   Mirrors backend Pydantic schemas at backend/src/api/v1/admin/cost_summary.py.
 *   `by_type` is a 2-level nested dict (cost_type → sub_type → AggregatedSlice)
 *   per Day 0 D9 finding (NOT a flat breakdown).
 *
 * Created: 2026-05-06 (Sprint 57.1 Day 1)
 * Last Modified: 2026-05-06
 *
 * Modification History:
 *   - 2026-05-06: Initial creation (Sprint 57.1 Day 1 / US-2 — Cost Dashboard types)
 *
 * Related:
 *   - backend/src/api/v1/admin/cost_summary.py (CostSummaryResponse + AggregatedSliceResponse)
 *   - ./services/costService.ts (consumer)
 *   - ./store/costStore.ts (consumer)
 */

export interface AggregatedSlice {
  quantity: string; // Decimal serialized as string
  total_cost_usd: string;
  entry_count: number;
}

export interface CostSummaryResponse {
  tenant_id: string;
  month: string; // YYYY-MM
  total_cost_usd: string; // Decimal serialized as string
  by_type: Record<string, Record<string, AggregatedSlice>>;
}
