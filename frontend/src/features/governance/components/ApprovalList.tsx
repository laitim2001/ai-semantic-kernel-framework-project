/**
 * File: frontend/src/features/governance/components/ApprovalList.tsx
 * Purpose: Tabular list of pending approvals — 7-col mockup-fidelity, row click → in-place Detail pane.
 * Category: Frontend / governance / components
 * Scope: Phase 53 / Sprint 53.5 US-1 → Sprint 57.9 (Tailwind) → Sprint 57.40 (mockup rebuild)
 *
 * Description:
 *   Sprint 57.40 rebuild: 6-col table (Tool / Risk / Requester / Reason /
 *   Time left / Action) → 7-col mockup-fidelity table (SevDot / Session /
 *   Tool / Risk / Policy / Operator / SLA). Row click replaces the trailing
 *   Review button (DecisionModal popup) with inline selection — parent
 *   ApprovalsPage tracks selectedId and renders ApprovalDetailPane on the
 *   right column.
 *
 *   RISK_COLOR_CLASS map deleted: mockup-ui `<RiskBadge>` owns the
 *   `var(--risk-X)` tokens internally (Sprint 57.34 promotion). Risk-level
 *   case mapping (UPPERCASE → lowercase) handled inline.
 *
 *   Verbatim port of `reference/design-mockups/page-governance.jsx:329-362`
 *   (table inside Pending approvals Card).
 *
 * Created: 2026-05-04 (Sprint 53.5 Day 3)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Sprint 57.40 — 6-col → 7-col + SevDot + selected highlight + row onClick (replaces Review modal flow) + RiskBadge primitive; RISK_COLOR_CLASS deleted
 *   - 2026-05-25: FIX-017 — RISK_COLOR_CLASS hex sentinels (#2e7d32/#ed6c02/#d84315/#b71c1c) → var(--risk-X)
 *   - 2026-05-25: FIX-015 — re-point shadcn-utility tokens (bg-muted/border-border/etc.) → mockup verbatim classes/vars
 *   - 2026-05-09: Sprint 57.9 US-2 Day 1 — Tailwind migration (drop inline styles)
 *   - 2026-05-04: Initial creation (Sprint 53.5 Day 3)
 *
 * Related:
 *   - ./ApprovalsPage.tsx (parent owns state + selection)
 *   - ./ApprovalDetailPane.tsx (right-col pane re-rendered on row click)
 *   - ../../../components/mockup-ui.tsx (SevDot / RiskBadge / Badge primitives)
 *   - reference/design-mockups/page-governance.jsx L329-362
 */

/* eslint-disable no-restricted-syntax -- verbatim re-point: inline `style=` literals are mockup page-governance.jsx visual-layer copied byte-for-byte; re-expressing as Tailwind IS the drift bug this epic kills (STYLE.md §3 escape hatch + frontend-mockup-fidelity.md) */

import { Badge, RiskBadge, SevDot } from "../../../components/mockup-ui";
import type { ApprovalSummary, RiskLevelLabel } from "../types";

type Props = {
  approvals: ApprovalSummary[];
  selectedId: string | null;
  onSelect: (approval: ApprovalSummary) => void;
};

const RISK_MAP: Record<RiskLevelLabel, "low" | "medium" | "high" | "critical"> = {
  LOW: "low",
  MEDIUM: "medium",
  HIGH: "high",
  CRITICAL: "critical",
};

function formatSlaShort(iso: string): string {
  const ms = new Date(iso).getTime() - Date.now();
  if (Number.isNaN(ms)) return "—";
  if (ms < 0) return "expired";
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}m ${String(seconds).padStart(2, "0")}s`;
}

function slaMinutesLeft(iso: string): number {
  const ms = new Date(iso).getTime() - Date.now();
  if (Number.isNaN(ms) || ms < 0) return -1;
  return Math.floor(ms / 60_000);
}

export function ApprovalList({ approvals, selectedId, onSelect }: Props) {
  if (approvals.length === 0) {
    return <p className="subtle my-4 italic">No pending approvals.</p>;
  }
  return (
    <table className="table">
      <thead>
        <tr>
          <th style={{ width: 18 }}></th>
          <th>Session</th>
          <th>Tool</th>
          <th>Risk</th>
          <th>Policy</th>
          <th>Operator</th>
          <th style={{ textAlign: "right" }}>SLA</th>
        </tr>
      </thead>
      <tbody>
        {approvals.map((approval) => {
          const riskKey = RISK_MAP[approval.risk_level];
          const toolName = approval.payload.tool_name ?? "(unknown)";
          const sessionTitle =
            typeof approval.payload.summary === "string"
              ? approval.payload.summary.slice(0, 40)
              : typeof approval.payload.reason === "string"
                ? approval.payload.reason.slice(0, 40)
                : approval.session_id;
          const requestIdShort = approval.request_id.slice(0, 10);
          const isSelected = selectedId === approval.request_id;
          const slaText = formatSlaShort(approval.sla_deadline);
          const slaMins = slaMinutesLeft(approval.sla_deadline);
          const slaColor =
            slaMins >= 0 && slaMins < 10 ? "var(--warning)" : "var(--fg-muted)";
          return (
            <tr
              key={approval.request_id}
              onClick={() => onSelect(approval)}
              style={{
                background: isSelected
                  ? "oklch(from var(--primary) l c h / 0.08)"
                  : undefined,
                cursor: "pointer",
              }}
            >
              <td><SevDot level={riskKey} /></td>
              <td>
                <div style={{ fontSize: 12.5, fontWeight: 500 }}>{sessionTitle}</div>
                <div className="mono subtle" style={{ fontSize: 10.5 }}>
                  incident-responder · {requestIdShort}
                </div>
              </td>
              <td>
                <span className="mono" style={{ color: "var(--tool)", fontSize: 11.5 }}>
                  {toolName}
                </span>
              </td>
              <td><RiskBadge level={riskKey} /></td>
              <td><Badge>always_ask</Badge></td>
              <td className="subtle" style={{ fontSize: 11.5 }}>{approval.requester}</td>
              <td style={{ textAlign: "right" }}>
                <span className="mono" style={{ fontSize: 11, color: slaColor }}>
                  {slaText}
                </span>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
