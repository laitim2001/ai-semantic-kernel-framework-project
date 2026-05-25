/**
 * File: frontend/src/features/governance/components/ApprovalsFilterTabs.tsx
 * Purpose: 5-tab navigation for HITL Approvals page (Active / Approved / Rejected / Expired / Policies).
 * Category: Frontend / governance / components
 * Scope: Phase 57 / Sprint 57.40 Day 1 (mockup-fidelity rebuild)
 *
 * Description:
 *   Verbatim port of `reference/design-mockups/page-governance.jsx:310-320`
 *   (`<Tabs>` section). Wraps mockup-ui `<Tabs>` primitive with 5-tab items.
 *   "Active" tab count is REAL (derived from `approvalsCount` prop). The other
 *   tab counts (Approved 184 / Rejected 6 / Expired 2) are fixture pending
 *   backend filter endpoints — visible via the AP-2 banner inside
 *   ApprovalsEmptyTab when those tabs are selected.
 *
 * Key Components:
 *   - ApprovalsFilterTabs: stateless; controlled component (value/onChange)
 *   - TabId: exported union type for parent's state shape
 *
 * Created: 2026-05-25 (Sprint 57.40 Day 1)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Sprint 57.40 — initial creation (5-tab nav controlled component)
 *
 * Related:
 *   - reference/design-mockups/page-governance.jsx L310-320
 *   - ../../../components/mockup-ui.tsx (Tabs primitive + TabItem type)
 *   - ./ApprovalsEmptyTab.tsx (renders AP-2 banner for non-active tabs)
 */

import { Tabs } from "../../../components/mockup-ui";

export type TabId = "active" | "approved" | "rejected" | "expired" | "policies";

interface Props {
  value: TabId;
  onChange: (id: TabId) => void;
  approvalsCount: number;
}

export function ApprovalsFilterTabs({ value, onChange, approvalsCount }: Props) {
  return (
    <Tabs
      value={value}
      onChange={(id) => onChange(id as TabId)}
      items={[
        { id: "active", label: "Active", count: approvalsCount },
        { id: "approved", label: "Approved", count: 184 },
        { id: "rejected", label: "Rejected", count: 6 },
        { id: "expired", label: "Expired", count: 2 },
        { id: "policies", label: "Policies" },
      ]}
    />
  );
}
