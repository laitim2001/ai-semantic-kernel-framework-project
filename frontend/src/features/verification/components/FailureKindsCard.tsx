/* eslint-disable no-restricted-syntax -- mockup verbatim CSS literals; mockup-fidelity (Sprint 57.41). See reference/design-mockups/page-extras.jsx L881-904. */
/**
 * File: frontend/src/features/verification/components/FailureKindsCard.tsx
 * Purpose: Failure kinds sidebar Card — 5-row breakdown with bar-track + count + AP-2 banner.
 * Category: Frontend / verification / components
 * Scope: Phase 57 / Sprint 57.41 Day 1 (mockup-fidelity rebuild)
 *
 * Description:
 *   Verbatim port of `reference/design-mockups/page-extras.jsx:881-904`
 *   ("Failure kinds" Card in the .col sidebar). Renders 5 fixture rows:
 *     - source_allowlist · 18 · danger
 *     - schema_completeness · 12 · warning
 *     - metric_threshold · 8 · warning
 *     - evidence_chain · 3 · memory
 *     - doc_match · 2 · info
 *   Each row: dot + mono name on left + tnum count on right + bar-track below
 *   at width (n / 22 * 100)%. max = 22 verbatim from mockup hardcode.
 *
 *   AP-2 fixture: backend aggregation endpoint not yet built. BackendGapBanner
 *   appended at bottom of Card per `.claude/rules/anti-patterns-checklist.md`
 *   AP-2 (no Potemkin) — Sprint 57.40 ApprovalsStatsStrip / Sprint 57.24-25
 *   precedent.
 *
 * Key Components:
 *   - FailureKindsCard: stateless functional component, no props (pure fixture)
 *
 * Created: 2026-05-25 (Sprint 57.41 Day 1)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.41 Day 1) — verification view full mockup-fidelity rebuild
 *
 * Related:
 *   - reference/design-mockups/page-extras.jsx L881-904
 *   - ../../../components/mockup-ui.tsx (Card primitive)
 *   - ../../../components/ui/BackendGapBanner.tsx (AP-2 fixture declaration)
 */

import { Card } from "../../../components/mockup-ui";
import { BackendGapBanner } from "../../../components/ui/BackendGapBanner";

const FAILURE_KINDS: Array<{ k: string; n: number; c: string }> = [
  { k: "source_allowlist", n: 18, c: "var(--danger)" },
  { k: "schema_completeness", n: 12, c: "var(--warning)" },
  { k: "metric_threshold", n: 8, c: "var(--warning)" },
  { k: "evidence_chain", n: 3, c: "var(--memory)" },
  { k: "doc_match", n: 2, c: "var(--info)" },
];

const FAILURE_MAX = 22;

export function FailureKindsCard() {
  return (
    <Card title="Failure kinds" subtitle="What's breaking">
      <div className="col" style={{ gap: 8, fontSize: 12 }}>
        {FAILURE_KINDS.map((f) => (
          <div key={f.k}>
            <div className="spread" style={{ marginBottom: 3 }}>
              <span className="row" style={{ gap: 6 }}>
                <span
                  style={{
                    width: 5,
                    height: 5,
                    borderRadius: "50%",
                    background: f.c,
                  }}
                />
                <span className="mono" style={{ fontSize: 11.5 }}>
                  {f.k}
                </span>
              </span>
              <span className="mono tnum" style={{ fontSize: 11 }}>
                {f.n}
              </span>
            </div>
            <div className="bar-track">
              <span
                style={{
                  width: `${(f.n / FAILURE_MAX) * 100}%`,
                  background: f.c,
                }}
              />
            </div>
          </div>
        ))}
      </div>
      <BackendGapBanner reason="Failure kinds aggregation endpoint pending (Phase 58+)" />
    </Card>
  );
}
