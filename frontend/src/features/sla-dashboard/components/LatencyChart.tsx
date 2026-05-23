/**
 * File: frontend/src/features/sla-dashboard/components/LatencyChart.tsx
 * Purpose: 24h LatencyChart 3-series multi-line SVG (Sprint 57.25 Day 1 US-B3; Sprint 57.32 Day 2 US-C1 verbatim re-point).
 * Category: Frontend / sla-dashboard / components (feature-scoped; NOT extracted to components/charts/)
 * Scope: Phase 57 / Sprint 57.32 Day 2 US-C1 (Phase-2 verbatim re-point on Sprint 57.25 strict-rebuild scaffolding)
 *
 * Description:
 *   Verbatim port of `reference/design-mockups/page-admin.jsx:157-198`
 *   LatencyChart helper. 3-series multi-line SVG (p50 / p95 / p99) over 48
 *   time points (24h sliding window @ 30min intervals). Axis labels: x at
 *   i=0,12,24,36,47 (-23h / -17h / -11h / -5h / -0h); y at 4 ticks
 *   normalized to max.
 *
 *   Sprint 57.32 Day 2 US-C1: Phase-2 verbatim CSS re-point. svg root
 *   className `w-full` → mockup `chart` class (styles-mockup.css:1077
 *   provides width 100% + height 180px; inline style={{ height: 220 }}
 *   overrides height per mockup page-admin.jsx:174). <g> for grid lines:
 *   explicit stroke/strokeWidth/opacity attrs → className="grid" (styles-
 *   mockup.css:1078 .chart .grid line). <g> for axis text: explicit
 *   fill/fontSize/fontFamily → className="axis" (styles-mockup.css:1079
 *   .chart .axis text supplies fill var(--fg-subtle) + font-size 10px +
 *   font-family var(--font-mono)). 3-series paths preserved verbatim
 *   (stroke colors + widths + p99 opacity).
 *
 *   Per Karpathy §2 "extract on 2nd consumer" — this component is KEPT
 *   inline in features/sla-dashboard/ (only 1 consumer this sprint).
 *   Sprint 58+ may extract to components/charts/ if 2nd consumer
 *   arises (carryover: AD-LatencyChart-Extraction-Phase58).
 *
 *   Color tones (mockup-faithful):
 *   - p50 → var(--primary) stroke 1.8 (most prominent)
 *   - p95 → var(--info)   stroke 1.4
 *   - p99 → var(--warning) stroke 1.4 opacity 0.9
 *
 *   Backend 24h time-series aggregation pending Phase 58+
 *   AD-SLA-Dashboard-Backend-Extensions-Phase58; AP-2 banner rendered by
 *   parent Card wrapper in SLAOverview.
 *
 * Created: 2026-05-19 (Sprint 57.25 Day 1 US-B3)
 * Last Modified: 2026-05-23
 *
 * Modification History:
 *   - 2026-05-23: Sprint 57.32 Day 2 US-C1 — verbatim re-point: .chart class + inline height 220 + .grid + .axis (drop explicit attrs per styles-mockup.css)
 *   - 2026-05-19: Initial creation (Sprint 57.25 Day 1 US-B3)
 *
 * Related:
 *   - reference/design-mockups/page-admin.jsx:157-198 (canonical mockup)
 *   - frontend/src/styles-mockup.css:1077-1079 (.chart .grid line / .chart .axis text)
 *   - frontend/src/features/sla-dashboard/__fixtures__/latencyChart24h.ts (fixture)
 */

/* eslint-disable no-restricted-syntax -- verbatim re-point: inline style={{ height: 220 }} matches mockup page-admin.jsx:174 escape-hatch override of .chart default 180px. */

import { LATENCY_24H, type LatencyDataPoint } from "../__fixtures__/latencyChart24h";

const WIDTH = 760;
const HEIGHT = 220;
const PAD = 30;
const SERIES: Array<{ key: keyof LatencyDataPoint; stroke: string; width: number; opacity: number }> = [
  { key: "p50", stroke: "var(--primary)", width: 1.8, opacity: 1 },
  { key: "p95", stroke: "var(--info)", width: 1.4, opacity: 1 },
  { key: "p99", stroke: "var(--warning)", width: 1.4, opacity: 0.9 },
];

export function LatencyChart() {
  if (LATENCY_24H.length === 0) return null;
  const max = Math.max(...LATENCY_24H.map((d) => d.p99)) * 1.1;
  const step = (WIDTH - PAD * 2) / (LATENCY_24H.length - 1);

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      preserveAspectRatio="none"
      style={{ height: HEIGHT }}
      className="chart"
      data-testid="sla-latency-chart"
      aria-label="24h latency distribution chart"
    >
      {/* horizontal grid lines at 25/50/75% — verbatim: styles via .chart .grid line */}
      <g className="grid">
        {[0.25, 0.5, 0.75].map((t) => {
          const y = PAD + (HEIGHT - PAD * 2) * t;
          return <line key={t} x1={PAD} x2={WIDTH - PAD} y1={y} y2={y} />;
        })}
      </g>

      {/* axis labels — verbatim: styles via .chart .axis text */}
      <g className="axis">
        {[0, 12, 24, 36, 47].map((i) => (
          <text
            key={`x-${i}`}
            x={PAD + i * step}
            y={HEIGHT - 8}
            textAnchor="middle"
            data-testid={`sla-latency-chart-x-tick-${i}`}
          >
            -{Math.round((47 - i) / 2)}h
          </text>
        ))}
        {[0, 0.25, 0.5, 0.75].map((t) => (
          <text
            key={`y-${t}`}
            x={PAD - 6}
            y={PAD + (HEIGHT - PAD * 2) * t + 3}
            textAnchor="end"
            data-testid={`sla-latency-chart-y-tick-${t}`}
          >
            {Math.round(max * (1 - t))}ms
          </text>
        ))}
      </g>

      {/* 3 series multi-line paths */}
      {SERIES.map(({ key, stroke, width, opacity }) => {
        const d = LATENCY_24H.map((dp, i) => {
          const x = PAD + i * step;
          const y = HEIGHT - PAD - (dp[key] / max) * (HEIGHT - PAD * 2);
          return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
        }).join(" ");
        return (
          <path
            key={key}
            d={d}
            fill="none"
            stroke={stroke}
            strokeWidth={width}
            opacity={opacity}
            data-testid={`sla-latency-chart-series-${key}`}
          />
        );
      })}
    </svg>
  );
}
