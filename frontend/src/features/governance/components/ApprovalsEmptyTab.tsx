/**
 * File: frontend/src/features/governance/components/ApprovalsEmptyTab.tsx
 * Purpose: AP-2 BackendGapBanner placeholder for the 4 non-active Approval tabs.
 * Category: Frontend / governance / components
 * Scope: Phase 57 / Sprint 57.40 Day 1 (mockup-fidelity rebuild)
 *
 * Description:
 *   Renders an AP-2 BackendGapBanner inside a Card placeholder when the user
 *   selects one of the four non-active tabs (Approved / Rejected / Expired /
 *   Policies). These tabs require backend list endpoints + filter parameters
 *   not yet implemented; Sprint 57.40 ships the Active tab functional + these
 *   four with an honest fixture-deferred placeholder per
 *   `.claude/rules/anti-patterns-checklist.md` AP-2.
 *
 * Key Components:
 *   - ApprovalsEmptyTab: stateless; props pass `tabId` for label dispatch
 *
 * Created: 2026-05-25 (Sprint 57.40 Day 1)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Sprint 57.40 — initial creation (4 tab × AP-2 banner placeholder)
 *
 * Related:
 *   - ./ApprovalsFilterTabs.tsx (parent dispatcher — when tab !== "active" → renders this)
 *   - ../../../components/mockup-ui.tsx (Card)
 *   - ../../../components/ui/BackendGapBanner.tsx (AP-2 banner)
 */

import { Card } from "../../../components/mockup-ui";
import { BackendGapBanner } from "../../../components/ui/BackendGapBanner";

type EmptyTabId = "approved" | "rejected" | "expired" | "policies";

const TAB_LABEL: Record<EmptyTabId, string> = {
  approved: "Approved",
  rejected: "Rejected",
  expired: "Expired",
  policies: "Policies",
};

interface Props {
  tabId: EmptyTabId;
}

export function ApprovalsEmptyTab({ tabId }: Props) {
  const label = TAB_LABEL[tabId];
  return (
    <Card title={label} subtitle="Pending backend list / filter endpoint">
      <BackendGapBanner
        reason={`Tab "${label}" is a Phase 58+ backend-pair feature — list endpoint pending`}
      />
    </Card>
  );
}
