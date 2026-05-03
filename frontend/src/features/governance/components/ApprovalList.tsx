/**
 * File: frontend/src/features/governance/components/ApprovalList.tsx
 * Purpose: Tabular list of pending approvals; row click → DecisionModal.
 * Category: Frontend / governance / components
 * Scope: Phase 53 / Sprint 53.5 US-1
 *
 * Created: 2026-05-04 (Sprint 53.5 Day 3)
 *
 * Related:
 *   - ./ApprovalsPage.tsx (parent owns state + fetch)
 */

import type { ApprovalSummary, RiskLevelLabel } from "../types";

type Props = {
  approvals: ApprovalSummary[];
  onSelect: (approval: ApprovalSummary) => void;
};

const RISK_COLOR: Record<RiskLevelLabel, string> = {
  LOW: "#2e7d32",
  MEDIUM: "#ed6c02",
  HIGH: "#d84315",
  CRITICAL: "#b71c1c",
};

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontFamily: "system-ui, sans-serif",
  fontSize: "0.92rem",
};

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "0.6rem 0.5rem",
  borderBottom: "2px solid #ccc",
  background: "#fafafa",
};

const tdStyle: React.CSSProperties = {
  padding: "0.5rem 0.5rem",
  borderBottom: "1px solid #eee",
};

function formatAge(sla: string): string {
  const ms = new Date(sla).getTime() - Date.now();
  if (Number.isNaN(ms)) return "—";
  const minutes = Math.round(ms / 60_000);
  if (minutes < 0) return "expired";
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.round(minutes / 60);
  return `${hours}h`;
}

export function ApprovalList({ approvals, onSelect }: Props) {
  if (approvals.length === 0) {
    return (
      <p style={{ color: "#666", fontStyle: "italic", margin: "1rem 0" }}>
        No pending approvals.
      </p>
    );
  }
  return (
    <table style={tableStyle}>
      <thead>
        <tr>
          <th style={thStyle}>Tool</th>
          <th style={thStyle}>Risk</th>
          <th style={thStyle}>Requester</th>
          <th style={thStyle}>Reason</th>
          <th style={thStyle}>Time left</th>
          <th style={thStyle}>Action</th>
        </tr>
      </thead>
      <tbody>
        {approvals.map((approval) => {
          const toolName = approval.payload.tool_name ?? "(unknown)";
          const reason = approval.payload.reason ?? "";
          return (
            <tr key={approval.request_id}>
              <td style={tdStyle}>{toolName}</td>
              <td style={tdStyle}>
                <span style={{ color: RISK_COLOR[approval.risk_level], fontWeight: 600 }}>
                  {approval.risk_level}
                </span>
              </td>
              <td style={tdStyle}>{approval.requester}</td>
              <td style={tdStyle}>{reason}</td>
              <td style={tdStyle}>{formatAge(approval.sla_deadline)}</td>
              <td style={tdStyle}>
                <button
                  type="button"
                  onClick={() => onSelect(approval)}
                  style={{
                    padding: "0.35rem 0.85rem",
                    border: "1px solid #1976d2",
                    background: "white",
                    color: "#1976d2",
                    borderRadius: 4,
                    cursor: "pointer",
                    fontSize: "0.9rem",
                    fontWeight: 600,
                  }}
                >
                  Review
                </button>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
