/**
 * File: frontend/src/features/governance/components/ApprovalsPageHeader.tsx
 * Purpose: HITL Approvals page header — title / sub / route pill / action buttons.
 * Category: Frontend / governance / components
 * Scope: Phase 57 / Sprint 57.40 Day 1 (mockup-fidelity rebuild)
 *
 * Description:
 *   Verbatim port of `reference/design-mockups/page-governance.jsx:289-301`
 *   (`.page-head` section of the `Approvals` component). Renders the title
 *   "HITL Approvals", subtitle, `/governance/approvals` route pill, and Teams
 *   sync / Export action buttons. Action buttons are visual-only AP-2 stubs
 *   (no backend wiring this sprint).
 *
 * Key Components:
 *   - ApprovalsPageHeader: stateless functional component, no props
 *
 * Created: 2026-05-25 (Sprint 57.40 Day 1)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Sprint 57.40 — initial creation (mockup page-governance.jsx:289 .page-head port)
 *
 * Related:
 *   - reference/design-mockups/page-governance.jsx L289-301
 *   - ./ApprovalsPage.tsx (parent — renders this header at top of /governance/approvals)
 *   - ../../../components/mockup-ui.tsx (Button primitive)
 */

import { Button } from "../../../components/mockup-ui";

export function ApprovalsPageHeader() {
  return (
    <div className="page-head">
      <div>
        <div className="page-title">HITL Approvals</div>
        <div className="page-sub">
          Central queue · Approve/reject writes before agents commit
          <span className="route-pill">/governance/approvals</span>
        </div>
      </div>
      <div className="page-actions">
        <Button variant="outline" size="sm" icon="globe">Teams sync</Button>
        <Button variant="outline" size="sm" icon="download">Export</Button>
      </div>
    </div>
  );
}
