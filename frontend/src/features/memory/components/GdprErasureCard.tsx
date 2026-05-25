/* eslint-disable no-restricted-syntax -- mockup verbatim CSS literals + inline font-size on col wrap; mockup-fidelity (Sprint 57.42). See reference/design-mockups/page-governance.jsx L581-594. */
/**
 * File: frontend/src/features/memory/components/GdprErasureCard.tsx
 * Purpose: GDPR right-to-erasure sidebar Card — subject id input + reason select + tombstone Button + AP-2 banner.
 * Category: Frontend / memory / components
 * Scope: Phase 57 / Sprint 57.42 Day 1 (mockup-fidelity rebuild)
 *
 * Description:
 *   Verbatim port of `reference/design-mockups/page-governance.jsx:581-594`
 *   (GDPR right-to-erasure Card). Subtle subtitle "Tombstone subject across all
 *   memory scopes. WORM audit retains hash chain." + Field "Subject id" with
 *   mono input "u_…" + Field "Reason (audited)" with select defaultValue
 *   "gdpr" (3 options: GDPR Art. 17 / CCPA / Legal hold) + danger Button
 *   "Issue tombstone" with warn icon.
 *
 *   Button onClick = AP-2 stub alert (backend POST endpoint pending).
 *   BackendGapBanner declared inside Card declaring deferred erasure endpoint.
 *
 * Key Components:
 *   - GdprErasureCard: stateless functional, no props (pure fixture)
 *
 * Created: 2026-05-25 (Sprint 57.42 Day 1)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.42 Day 1) — memory matrix full mockup-fidelity rebuild
 *
 * Related:
 *   - reference/design-mockups/page-governance.jsx L581-594
 *   - ../../../components/mockup-ui.tsx (Card + Button + Field primitives)
 *   - ../../../components/ui/BackendGapBanner.tsx (AP-2 declaration)
 */

import { Button, Card, Field } from "../../../components/mockup-ui";
import { BackendGapBanner } from "../../../components/ui/BackendGapBanner";

export function GdprErasureCard(): JSX.Element {
  const onIssue = () => {
    window.alert("Issue tombstone: backend gap (Phase 58+) — memory erasure POST endpoint pending");
  };
  return (
    <Card title="GDPR right-to-erasure">
      <div className="col" style={{ gap: 10, fontSize: 12 }}>
        <div className="subtle">
          Tombstone subject across all memory scopes. WORM audit retains hash chain.
        </div>
        <Field label="Subject id">
          <input className="input mono" placeholder="u_…" />
        </Field>
        <Field label="Reason (audited)">
          <select className="select" defaultValue="gdpr">
            <option value="gdpr">GDPR Art. 17 erasure</option>
            <option value="ccpa">CCPA opt-out</option>
            <option value="legal">Legal hold release</option>
          </select>
        </Field>
        <Button variant="danger" size="sm" icon="warn" onClick={onIssue}>
          Issue tombstone
        </Button>
      </div>
      <BackendGapBanner reason="GDPR erasure endpoint pending (Phase 58+) — POST /api/v1/memory/erasure (tombstone + WORM audit append)" />
    </Card>
  );
}
