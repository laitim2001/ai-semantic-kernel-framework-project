/**
 * File: frontend/src/features/sla-dashboard/__fixtures__/statSparklines.ts
 * Purpose: Sparkline fixtures for SLA Dashboard 4-stat grid (Sprint 57.25 Day 1 US-B2).
 * Category: Frontend / sla-dashboard / __fixtures__
 * Scope: Phase 57 / Sprint 57.25 Day 1 US-B2
 *
 * Description:
 *   Mirror mockup `reference/design-mockups/page-admin.jsx:55-58` Spark
 *   demo arrays. All 4 sparklines are fixture-driven this sprint —
 *   `useSLAReport` returns only `api_p99_ms | _p99` fields (no p50/p95
 *   split; no error_budget). AD-SLA-Dashboard-Backend-Extensions-Phase58
 *   carries time-series fields.
 *
 * Modification History:
 *   - 2026-05-19: Initial creation (Sprint 57.25 Day 1 US-B2)
 */

export const SPARK_P50 = [320, 310, 300, 295, 290, 288, 290, 286, 284, 282, 284];
export const SPARK_P95 = [2.1, 2.0, 2.0, 1.9, 1.92, 1.88, 1.85, 1.84, 1.83, 1.84];
export const SPARK_P99 = [3.6, 3.7, 3.8, 3.9, 4.0, 4.1, 4.0, 4.2, 4.21];
export const SPARK_ERROR_BUDGET = [100, 99, 98, 97, 96, 95, 94, 93, 92.4];
