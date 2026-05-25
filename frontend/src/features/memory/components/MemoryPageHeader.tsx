/**
 * File: frontend/src/features/memory/components/MemoryPageHeader.tsx
 * Purpose: Memory page header — title / sub / route pill / time-travel cursor badge / 3 action buttons.
 * Category: Frontend / memory / components
 * Scope: Phase 57 / Sprint 57.42 Day 1 (mockup-fidelity rebuild)
 *
 * Description:
 *   Verbatim port of `reference/design-mockups/page-governance.jsx:480-495`
 *   (`.page-head` section of MemoryPage). Title "Memory Layers" + sub
 *   "Dual-axis · 5 scope × 3 time scale" + `/memory` route pill + entries count
 *   + conditional time-travel info Badge when cursor<0 + 3 action buttons
 *   (Time travel / Return to now toggle + Export AP-2 + New entry AP-2).
 *
 *   The Time-travel button toggles variant outline ↔ warning based on cursor;
 *   onClick resets cursor to 0 (returns to "now"). Export + New entry are
 *   visual-only AP-2 stubs.
 *
 * Key Components:
 *   - MemoryPageHeader: stateless functional, props { cursor, onResetCursor, entriesTotal? }
 *
 * Created: 2026-05-25 (Sprint 57.42 Day 1)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.42 Day 1) — memory matrix full mockup-fidelity rebuild
 *
 * Related:
 *   - reference/design-mockups/page-governance.jsx L480-495
 *   - ./MemoryView.tsx (parent — owns cursor state)
 *   - ../../../components/mockup-ui.tsx (Button + Badge primitives)
 *   - ../_fixtures.ts (TOTAL_ENTRIES default)
 */

import { Badge, Button } from "../../../components/mockup-ui";
import { TOTAL_ENTRIES } from "../_fixtures";

export interface MemoryPageHeaderProps {
  cursor: number;
  onResetCursor: () => void;
  entriesTotal?: number;
}

export function MemoryPageHeader({
  cursor,
  onResetCursor,
  entriesTotal = TOTAL_ENTRIES,
}: MemoryPageHeaderProps): JSX.Element {
  const onExport = () => {
    window.alert("Export: backend gap (Phase 58+) — memory export endpoint pending");
  };
  const onNewEntry = () => {
    window.alert("New entry: backend gap (Phase 58+) — memory POST endpoint pending");
  };
  return (
    <div className="page-head">
      <div>
        <div className="page-title">Memory Layers</div>
        <div className="page-sub">
          Dual-axis · 5 scope × 3 time scale
          <span className="route-pill">/memory</span>
          <span className="mono subtle">· {entriesTotal.toLocaleString()} entries</span>
          {cursor < 0 && (
            <Badge tone="info" dot>
              time-travel · {Math.abs(cursor)}m ago
            </Badge>
          )}
        </div>
      </div>
      <div className="page-actions">
        <Button
          variant={cursor < 0 ? "warning" : "outline"}
          size="sm"
          icon="clock"
          onClick={onResetCursor}
        >
          {cursor < 0 ? "Return to now" : "Time travel"}
        </Button>
        <Button variant="outline" size="sm" icon="download" onClick={onExport}>
          Export
        </Button>
        <Button variant="primary" size="sm" icon="plus" onClick={onNewEntry}>
          New entry
        </Button>
      </div>
    </div>
  );
}
