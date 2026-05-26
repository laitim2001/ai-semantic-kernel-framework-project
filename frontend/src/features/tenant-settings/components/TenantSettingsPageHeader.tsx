/**
 * File: frontend/src/features/tenant-settings/components/TenantSettingsPageHeader.tsx
 * Purpose: Verbatim port of mockup tenant-settings page header (title + sub line w/ mono + route-pill + plan badge).
 * Category: Frontend / tenant-settings / components
 * Scope: Phase 57 / Sprint 57.44 Day 1 (mockup-fidelity rebuild) → Sprint 57.49 (seats from real backend)
 *
 * Description:
 *   Verbatim port of mockup `page-admin.jsx` L416-425. Renders title "Tenant
 *   Settings" + sub line with mono display_name + route-pill code + plan badge
 *   "{plan} · {N} seats". `displayName` / `code` / `plan` / `seats` are live
 *   from backend (Sprint 57.46 schema extension; Sprint 57.49 frontend wire).
 *
 * Key Components:
 *   - TenantSettingsPageHeader: stateless visual header
 *
 * Created: 2026-05-26 (Sprint 57.44 Day 1)
 * Last Modified: 2026-05-26
 *
 * Modification History (newest-first):
 *   - 2026-05-26: Sprint 57.49 — replace SEATS_FIXTURE with seats prop from real backend
 *   - 2026-05-26: Initial creation (Sprint 57.44 Day 1)
 *
 * Related:
 *   - reference/design-mockups/page-admin.jsx L416-425
 *   - frontend/src/components/mockup-ui.tsx (Badge primitive)
 */

import { Badge } from "../../../components/mockup-ui";

export interface TenantSettingsPageHeaderProps {
  displayName: string;
  code: string;
  plan: string;
  /** Sprint 57.49 — real backend tenant.seats (Sprint 57.46 schema). Optional for back-compat with existing tests; defaults to 0. */
  seats?: number;
}

export function TenantSettingsPageHeader({
  displayName,
  code,
  plan,
  seats = 0,
}: TenantSettingsPageHeaderProps): JSX.Element {
  return (
    <div className="page-head">
      <div>
        <div className="page-title">Tenant Settings</div>
        <div className="page-sub">
          {/* eslint-disable-next-line no-restricted-syntax -- verbatim port: mockup uses inline style for mono color/weight */}
          <span className="mono" style={{ color: "var(--fg)", fontWeight: 500 }}>{displayName}</span>
          <span className="route-pill">{code}</span>
          <Badge tone="primary">{plan} · {seats} seats</Badge>
        </div>
      </div>
    </div>
  );
}
