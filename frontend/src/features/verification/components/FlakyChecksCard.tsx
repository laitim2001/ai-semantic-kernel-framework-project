/* eslint-disable no-restricted-syntax -- mockup verbatim CSS literals; mockup-fidelity (Sprint 57.41). See reference/design-mockups/page-extras.jsx L905-921. */
/**
 * File: frontend/src/features/verification/components/FlakyChecksCard.tsx
 * Purpose: Flaky checks sidebar Card — 3-row check/agent/rate with warning Badge + AP-2 banner.
 * Category: Frontend / verification / components
 * Scope: Phase 57 / Sprint 57.41 Day 1 (mockup-fidelity rebuild)
 *
 * Description:
 *   Verbatim port of `reference/design-mockups/page-extras.jsx:905-921`
 *   ("Flaky checks" Card in the .col sidebar). Renders 3 fixture rows:
 *     - claim_pii_redacted · 18% · compliance-auditor
 *     - source_in_allowlist · 12% · lead-enricher
 *     - schema.action_items_have_owner · 8% · meeting-notetaker
 *   Each row: check name (mono) + agent (subtle mono) on left + warning Badge
 *   rate on right.
 *
 *   AP-2 fixture: backend aggregation endpoint not yet built. BackendGapBanner
 *   appended at bottom of Card per `.claude/rules/anti-patterns-checklist.md`
 *   AP-2 (no Potemkin) — Sprint 57.40 / 57.24-25 precedent.
 *
 * Key Components:
 *   - FlakyChecksCard: stateless functional component, no props (pure fixture)
 *
 * Created: 2026-05-25 (Sprint 57.41 Day 1)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.41 Day 1) — verification view full mockup-fidelity rebuild
 *
 * Related:
 *   - reference/design-mockups/page-extras.jsx L905-921
 *   - ../../../components/mockup-ui.tsx (Card, Badge primitives)
 *   - ../../../components/ui/BackendGapBanner.tsx (AP-2 fixture declaration)
 */

import { Badge, Card } from "../../../components/mockup-ui";
import { BackendGapBanner } from "../../../components/ui/BackendGapBanner";

const FLAKY_CHECKS: Array<{ check: string; rate: string; agent: string }> = [
  { check: "claim_pii_redacted", rate: "18%", agent: "compliance-auditor" },
  { check: "source_in_allowlist", rate: "12%", agent: "lead-enricher" },
  { check: "schema.action_items_have_owner", rate: "8%", agent: "meeting-notetaker" },
];

export function FlakyChecksCard() {
  return (
    <Card title="Flaky checks" subtitle={`Failing > 5%, last 24h`}>
      <div className="col" style={{ gap: 6, fontSize: 12 }}>
        {FLAKY_CHECKS.map((f) => (
          <div key={f.check} className="spread">
            <div>
              <div className="mono" style={{ fontSize: 11.5 }}>
                {f.check}
              </div>
              <div className="subtle mono" style={{ fontSize: 10.5 }}>
                {f.agent}
              </div>
            </div>
            <Badge tone="warning">{f.rate}</Badge>
          </div>
        ))}
      </div>
      <BackendGapBanner reason="Flaky checks aggregation endpoint pending (Phase 58+)" />
    </Card>
  );
}
