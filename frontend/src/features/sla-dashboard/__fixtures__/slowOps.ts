/**
 * File: frontend/src/features/sla-dashboard/__fixtures__/slowOps.ts
 * Purpose: Top slow operations fixture (Sprint 57.25 Day 2 US-C2).
 * Category: Frontend / sla-dashboard / __fixtures__
 * Scope: Phase 57 / Sprint 57.25 Day 2 US-C2
 *
 * Description:
 *   Mockup-direct port of reference/design-mockups/page-admin.jsx:111-116.
 *   6 rows × {name, kind, p50, p95, p99, calls}; p99 > 3000ms triggers
 *   warning color (mockup line 123). Backend cross-operation p99
 *   aggregation pending Phase 58+ AD-SLA-Dashboard-Backend-Extensions.
 *
 * Modification History:
 *   - 2026-05-19: Initial creation (Sprint 57.25 Day 2 US-C2)
 */

export type OpKind = "tool" | "loop" | "subagent" | "verify" | "memory";

export interface SlowOpRow {
  name: string;
  kind: OpKind;
  p50: number;
  p95: number;
  p99: number;
  calls: number;
}

export const SLOW_OPS: SlowOpRow[] = [
  { name: "tool.metrics.query", kind: "tool", p50: 180, p95: 1900, p99: 4400, calls: 2840 },
  { name: "tool.k8s.set_env", kind: "tool", p50: 920, p95: 2800, p99: 5200, calls: 18 },
  { name: "loop.iteration", kind: "loop", p50: 290, p95: 1820, p99: 4100, calls: 14820 },
  { name: "subagent.spawn", kind: "subagent", p50: 12, p95: 38, p99: 220, calls: 412 },
  { name: "verification.run", kind: "verify", p50: 18, p95: 84, p99: 180, calls: 9200 },
  { name: "memory.write", kind: "memory", p50: 4, p95: 12, p99: 38, calls: 7820 },
];
