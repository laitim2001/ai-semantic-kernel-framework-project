/* eslint-disable no-restricted-syntax -- mockup verbatim CSS literals + cursor-aware inline visibility filter; mockup-fidelity (Sprint 57.42). See reference/design-mockups/page-governance.jsx L501-552. */
/**
 * File: frontend/src/features/memory/components/MemoryMatrix.tsx
 * Purpose: 5×3 dual-axis Memory Layers matrix — header row + 5 scope rows × 3 time-scale entry cells with cursor-aware visibility filter + AP-2 banner.
 * Category: Frontend / memory / components
 * Scope: Phase 57 / Sprint 57.42 Day 1 (mockup-fidelity rebuild)
 *
 * Description:
 *   Verbatim port of `reference/design-mockups/page-governance.jsx:501-552`
 *   (the `.memory-matrix` grid). 4-column × 6-row grid:
 *     - Row 1: empty corner cell + 3 header cells with colored dot + scale name
 *       + TTL subtitle (TTL ∞ / TTL 90d / TTL 24h)
 *     - Rows 2-6: scope label cell (name + sub + entry count) + 3 entry cells
 *       per scope (up to 4 entries + "+N more" + count footer)
 *
 *   Cursor-aware visibility filter per mockup logic:
 *     - cursor < 0 && t==="day" && scope==="session"
 *       → cursor > -10 ? first entry : []
 *     - cursor < -120 && t==="day" → []
 *     - else → all entries
 *   Hidden count appended to footer in warning color.
 *
 *   Hover bg toggle via local React useState (key string format
 *   `${scope.id}|${t}`).
 *
 *   AP-2 BackendGapBanner declared after grid for the deferred matrix endpoint.
 *
 * Key Components:
 *   - MemoryMatrix: stateful (local hover); props { cursor }
 *
 * Created: 2026-05-25 (Sprint 57.42 Day 1)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.42 Day 1) — memory matrix full mockup-fidelity rebuild
 *
 * Related:
 *   - reference/design-mockups/page-governance.jsx L501-552
 *   - ./MemoryView.tsx (parent — owns cursor state)
 *   - ../_fixtures.ts (SCOPES + TIME_SCALES + MEMORY_ENTRIES)
 *   - ../../../components/mockup-ui.tsx (Icon primitive)
 *   - ../../../components/ui/BackendGapBanner.tsx (AP-2 declaration)
 */

import React, { useState } from "react";

import { Icon } from "../../../components/mockup-ui";
import { BackendGapBanner } from "../../../components/ui/BackendGapBanner";
import {
  MEMORY_ENTRIES,
  SCOPES,
  TIME_SCALES,
  type MemoryEntryMockup,
  type TimeScaleMockup,
} from "../_fixtures";

export interface MemoryMatrixProps {
  cursor: number;
}

function scaleDotColor(t: TimeScaleMockup): string {
  return t === "permanent" ? "var(--memory)" : t === "quarter" ? "var(--info)" : "var(--tool)";
}

function scaleTtl(t: TimeScaleMockup): string {
  return t === "permanent" ? "TTL ∞" : t === "quarter" ? "TTL 90d" : "TTL 24h";
}

function filterVisible(
  entries: MemoryEntryMockup[],
  scopeId: string,
  t: TimeScaleMockup,
  cursor: number,
): MemoryEntryMockup[] {
  if (cursor < 0 && t === "day" && scopeId === "session") {
    return cursor > -10 ? entries.slice(0, 1) : [];
  }
  if (cursor < -120 && t === "day") {
    return [];
  }
  return entries;
}

export function MemoryMatrix({ cursor }: MemoryMatrixProps): JSX.Element {
  const [hovered, setHovered] = useState<string | null>(null);

  return (
    <>
      <div
        className="memory-matrix"
        style={{ opacity: cursor < 0 ? 0.95 : 1, transition: "opacity 0.2s" }}
      >
        <div className="mm-cell mm-header"></div>
        {TIME_SCALES.map((t) => (
          <div key={t} className="mm-cell mm-header">
            <div className="row" style={{ gap: 6 }}>
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: scaleDotColor(t),
                }}
              />
              <span>{t}</span>
              <span className="subtle">·</span>
              <span className="subtle">{scaleTtl(t)}</span>
            </div>
          </div>
        ))}

        {SCOPES.map((scope) => (
          <React.Fragment key={scope.id}>
            <div className="mm-cell mm-scope">
              <div className="name">{scope.name}</div>
              <div className="sub">{scope.sub}</div>
              <div className="row" style={{ gap: 6, marginTop: "auto", paddingTop: 8 }}>
                <Icon name="memory" size={12} style={{ color: "var(--memory)" }} />
                <span className="mono" style={{ fontSize: 10.5, color: "var(--fg-muted)" }}>
                  {scope.count.toLocaleString()}
                </span>
              </div>
            </div>
            {TIME_SCALES.map((t) => {
              const key = `${scope.id}|${t}`;
              const entries = MEMORY_ENTRIES[key] || [];
              const visible = filterVisible(entries, scope.id, t, cursor);
              const isHover = hovered === key;
              return (
                <div
                  key={key}
                  className="mm-cell"
                  onMouseEnter={() => setHovered(key)}
                  onMouseLeave={() => setHovered(null)}
                  style={{
                    background: isHover ? "var(--bg-2)" : undefined,
                    transition: "background 0.12s",
                    cursor: "pointer",
                  }}
                >
                  {visible.length === 0 && (
                    <div className="subtle" style={{ fontSize: 11, fontStyle: "italic" }}>
                      — empty
                    </div>
                  )}
                  {visible.slice(0, 4).map((e, i) => (
                    <div
                      key={i}
                      className="mm-entry"
                      style={{ animation: cursor < 0 ? "fade-up 0.25s" : "none" }}
                    >
                      <span className="k">{e.k}</span>{" "}
                      <span className="subtle">= {e.v}</span>
                    </div>
                  ))}
                  {visible.length > 4 && (
                    <div className="subtle mono" style={{ fontSize: 10, marginTop: 4 }}>
                      +{visible.length - 4} more
                    </div>
                  )}
                  <div className="count">
                    {visible.length} {visible.length === 1 ? "entry" : "entries"}
                    {cursor < 0 && entries.length !== visible.length && (
                      <span style={{ color: "var(--warning)" }}>
                        {" "}
                        · {entries.length - visible.length} hidden
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </React.Fragment>
        ))}
      </div>
      <BackendGapBanner reason="Memory matrix query endpoint pending (Phase 58+) — GET /api/v1/memory/matrix?scope=*&time_scale=*&cursor=*" />
    </>
  );
}
