/**
 * File: frontend/src/features/sla-dashboard/__fixtures__/latencyChart24h.ts
 * Purpose: 24h LatencyChart 3-series fixture (Sprint 57.25 Day 1 US-B3).
 * Category: Frontend / sla-dashboard / __fixtures__
 * Scope: Phase 57 / Sprint 57.25 Day 1 US-B3
 *
 * Description:
 *   Mockup-direct port of mockup `page-admin.jsx:159-167` LatencyChart
 *   data generation. 48 time points (every 30min over 24h); each point
 *   has p50 / p95 / p99 values derived from a sinusoidal base + noise +
 *   tail spike on p99 to reflect mockup's intentional outlier signal.
 *
 *   Deterministic precomputed array (no Math.random at render time) so
 *   Vitest snapshots are stable. Values mirror mockup algorithm with
 *   seeded pseudo-random (i / 47 based).
 *
 *   Backend 24h aggregation endpoint pending Phase 58+
 *   AD-SLA-Dashboard-Backend-Extensions-Phase58; AP-2 banner under chart.
 *
 * Modification History:
 *   - 2026-05-19: Initial creation (Sprint 57.25 Day 1 US-B3)
 */

export interface LatencyDataPoint {
  p50: number;
  p95: number;
  p99: number;
}

// Precomputed 48-point fixture (deterministic). Algorithm mirrors mockup
// page-admin.jsx:159-167 but with seeded noise instead of Math.random()
// so unit-test snapshots remain stable.
//
// base = 280 + sin(x * 6) * 30; x = i / 47
// p50 = base + seededNoise(i, 20)
// p95 = base * 5.2 + seededNoise(i, 200) + sin(x * 8) * 100
// p99 = base * 11 + seededNoise(i, 500) + (i > 35 ? 800 : 0)
function seededNoise(i: number, scale: number): number {
  // Deterministic pseudo-random in [0, scale) based on integer i.
  const r = Math.sin(i * 12.9898 + 78.233) * 43758.5453;
  return (r - Math.floor(r)) * scale;
}

function computePoint(i: number): LatencyDataPoint {
  const x = i / 47;
  const base = 280 + Math.sin(x * 6) * 30;
  const p50 = base + seededNoise(i, 20);
  const p95 = base * 5.2 + seededNoise(i + 1, 200) + Math.sin(x * 8) * 100;
  const p99 = base * 11 + seededNoise(i + 2, 500) + (i > 35 ? 800 : 0);
  return {
    p50: Math.round(p50),
    p95: Math.round(p95),
    p99: Math.round(p99),
  };
}

export const LATENCY_24H: LatencyDataPoint[] = Array.from({ length: 48 }, (_, i) =>
  computePoint(i),
);
