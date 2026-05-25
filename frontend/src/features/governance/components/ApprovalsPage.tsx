/**
 * File: frontend/src/features/governance/components/ApprovalsPage.tsx
 * Purpose: HITL Approvals page — full mockup-fidelity rebuild (5-component composition).
 * Category: Frontend / governance / components
 * Scope: Phase 53 / Sprint 53.5 US-1 → Sprint 57.9 US-3 (TanStack) → Sprint 57.40 (mockup rebuild)
 *
 * Description:
 *   Sprint 57.40 rebuild: 1-col simple table + DecisionModal popup pattern
 *   replaced with mockup-faithful 5-component composition:
 *     - ApprovalsPageHeader (.page-head + actions)
 *     - ApprovalsStatsStrip (4 KPI; Active = real, others fixture + AP-2)
 *     - ApprovalsFilterTabs (5-tab nav: Active / Approved / Rejected / Expired / Policies)
 *     - 2-col layout under Active tab: ApprovalList (left) + ApprovalDetailPane (right)
 *     - ApprovalsEmptyTab (4 non-active tabs → AP-2 placeholder)
 *
 *   In-place Detail pane interaction replaces the legacy modal pop flow:
 *     - Click row in list → selectedId state updates → Detail pane re-renders
 *     - Approve/Reject buttons in Detail pane fire useApprovalDecide mutation
 *     - DecisionModal.tsx deleted as orphan per Karpathy §3
 *
 *   Resolves drift audit 2026-05-25 /governance CATASTROPHIC verdict (mockup
 *   ships 4 KPI + 5-tab + 2-col rich pane; production was 1-col simple table).
 *
 * Created: 2026-05-04 (Sprint 53.5 Day 3)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Sprint 57.40 — full mockup rebuild (page-governance.jsx:283 Approvals; 4 KPI + 5-tab + 2-col composition)
 *   - 2026-05-09: Sprint 57.9 US-3 Day 2 — drop manual polling/state, consume useApprovals hook
 *   - 2026-05-09: Sprint 57.9 US-2 Day 1 — Tailwind migration (drop inline styles)
 *   - 2026-05-04: Initial creation (Sprint 53.5 Day 3)
 *
 * Related:
 *   - reference/design-mockups/page-governance.jsx L283-407
 *   - ./ApprovalsPageHeader.tsx ./ApprovalsStatsStrip.tsx ./ApprovalsFilterTabs.tsx
 *     ./ApprovalList.tsx ./ApprovalDetailPane.tsx ./ApprovalsEmptyTab.tsx
 *   - ../hooks/useApprovals.ts (TanStack query, 30s refetchInterval)
 *   - ../hooks/useApprovalDecide.ts (decision mutation; invalidates query)
 */

import { useState } from "react";

import { Button, Card } from "../../../components/mockup-ui";
import { useApprovalDecide } from "../hooks/useApprovalDecide";
import { useApprovals } from "../hooks/useApprovals";
import type { ApprovalSummary } from "../types";
import { ApprovalDetailPane } from "./ApprovalDetailPane";
import { ApprovalList } from "./ApprovalList";
import { ApprovalsEmptyTab } from "./ApprovalsEmptyTab";
import { ApprovalsFilterTabs, type TabId } from "./ApprovalsFilterTabs";
import { ApprovalsPageHeader } from "./ApprovalsPageHeader";
import { ApprovalsStatsStrip } from "./ApprovalsStatsStrip";

export function ApprovalsPage() {
  const { data: items = [], error } = useApprovals();
  const decideMutation = useApprovalDecide();
  const [tab, setTab] = useState<TabId>("active");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selected: ApprovalSummary | null =
    items.find((i) => i.request_id === selectedId) ?? null;

  const onApprove = () => {
    if (selected) {
      decideMutation.mutate({ requestId: selected.request_id, decision: "approved" });
    }
  };
  const onReject = () => {
    if (selected) {
      decideMutation.mutate({ requestId: selected.request_id, decision: "rejected" });
    }
  };

  return (
    <div>
      <ApprovalsPageHeader />
      <ApprovalsStatsStrip approvals={items} />
      <ApprovalsFilterTabs value={tab} onChange={setTab} approvalsCount={items.length} />

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive"
        >
          Failed to load approvals: {error.message}
        </div>
      )}

      {tab === "active" ? (
        // eslint-disable-next-line no-restricted-syntax -- verbatim re-point: mockup page-governance.jsx:322 grid-template inline
        <div style={{ display: "grid", gridTemplateColumns: "1fr 420px", gap: 14 }}>
          <Card
            title="Pending approvals"
            subtitle="Sorted by SLA urgency"
            bodyClass="flush"
            actions={
              <div className="row">
                <Button variant="ghost" size="sm" icon="filter">Risk: all</Button>
                <Button variant="ghost" size="sm" icon="sliders">Sort: SLA</Button>
              </div>
            }
          >
            <ApprovalList
              approvals={items}
              selectedId={selectedId}
              onSelect={(a) => setSelectedId(a.request_id)}
            />
          </Card>
          <ApprovalDetailPane
            approval={selected}
            onApprove={onApprove}
            onReject={onReject}
          />
        </div>
      ) : (
        <ApprovalsEmptyTab tabId={tab} />
      )}
    </div>
  );
}
