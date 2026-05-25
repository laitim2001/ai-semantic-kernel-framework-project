/**
 * File: frontend/src/features/verification/components/VerificationPageHeader.tsx
 * Purpose: Verification page header — title / sub / route pill / action buttons.
 * Category: Frontend / verification / components
 * Scope: Phase 57 / Sprint 57.41 Day 1 (mockup-fidelity rebuild)
 *
 * Description:
 *   Verbatim port of `reference/design-mockups/page-extras.jsx:833-845`
 *   (`.page-head` section of the `VerificationPage` component). Renders the
 *   title "Verification", subtitle, `/verification` route pill, and All-kinds /
 *   Export action buttons. Action buttons are visual-only AP-2 stubs (no
 *   backend wiring this sprint).
 *
 * Key Components:
 *   - VerificationPageHeader: stateless functional component, no props
 *
 * Created: 2026-05-25 (Sprint 57.41 Day 1)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.41 Day 1) — verification view full mockup-fidelity rebuild
 *
 * Related:
 *   - reference/design-mockups/page-extras.jsx L833-845
 *   - ./VerificationView.tsx (parent — renders this header at top of /verification/recent)
 *   - ../../../components/mockup-ui.tsx (Button primitive)
 */

import { Button } from "../../../components/mockup-ui";

export function VerificationPageHeader() {
  const onAllKinds = () => {
    window.alert("All-kinds filter: backend gap (Phase 58+) — verification kind aggregation endpoint pending");
  };
  const onExport = () => {
    window.alert("Export: backend gap (Phase 58+) — verification_log export endpoint pending");
  };
  return (
    <div className="page-head">
      <div>
        <div className="page-title">Verification</div>
        <div className="page-sub">
          Range 7 · Claim verification with evidence · failed claims block downstream actions
          <span className="route-pill">/verification</span>
        </div>
      </div>
      <div className="page-actions">
        <Button variant="outline" size="sm" icon="filter" onClick={onAllKinds}>All kinds</Button>
        <Button variant="outline" size="sm" icon="download" onClick={onExport}>Export</Button>
      </div>
    </div>
  );
}
