/**
 * File: frontend/src/features/sla-dashboard/__fixtures__/errorRateByService.ts
 * Purpose: Per-service error rate fixture (Sprint 57.25 Day 2 US-C3).
 * Category: Frontend / sla-dashboard / __fixtures__
 * Scope: Phase 57 / Sprint 57.25 Day 2 US-C3
 *
 * Description:
 *   Mockup-direct port of reference/design-mockups/page-admin.jsx:134-140.
 *   6 rows × {name, rate%}; rate > 0.5 triggers warning tone (mockup line
 *   144 + 147). Backend per-service error rate aggregation pending Phase
 *   58+ AD-SLA-Dashboard-Backend-Extensions.
 *
 * Modification History:
 *   - 2026-05-19: Initial creation (Sprint 57.25 Day 2 US-C3)
 */

export interface ErrorRateRow {
  name: string;
  rate: number; // percent (0-100); usually < 1 in practice
}

export const ERROR_RATE_BY_SERVICE: ErrorRateRow[] = [
  { name: "inference.adapter", rate: 0.04 },
  { name: "tool.runner", rate: 0.6 },
  { name: "memory.store", rate: 0.0 },
  { name: "audit.writer", rate: 0.0 },
  { name: "subagent.scheduler", rate: 0.12 },
  { name: "webhook.dispatcher", rate: 0.4 },
];
