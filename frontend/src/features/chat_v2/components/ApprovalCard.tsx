/**
 * File: frontend/src/features/chat_v2/components/ApprovalCard.tsx
 * Purpose: Inline HITL approval card rendered in chat (Sprint 53.5 US-2).
 * Category: Frontend / chat_v2 / components
 * Scope: Phase 53 / Sprint 53.5 US-2
 *
 * Description:
 *   Displays an in-conversation card when the loop emits ApprovalRequested.
 *   Renders Approve / Reject quick buttons (calls governanceService.decide
 *   and optimistically updates the chat store) plus a deep link to the
 *   governance approvals page.
 *
 *   When ApprovalReceived arrives, the card transitions to a readonly view
 *   showing the reviewer outcome.
 *
 * Created: 2026-05-04 (Sprint 53.5 Day 4 US-2)
 *
 * Related:
 *   - ../store/chatStore.ts (approvals slice)
 *   - ../../governance/services/governanceService.ts (decide call)
 */

import { useState } from "react";

import { governanceService } from "../../governance/services/governanceService";
import type { DecisionLabel } from "../../governance/types";
import { useChatStore } from "../store/chatStore";

const RISK_COLOR: Record<string, string> = {
  LOW: "#2e7d32",
  MEDIUM: "#ed6c02",
  HIGH: "#d84315",
  CRITICAL: "#b71c1c",
};

const cardStyle: React.CSSProperties = {
  border: "1px solid #ed6c02",
  background: "#fff8e1",
  borderRadius: 6,
  padding: "0.75rem 1rem",
  margin: "0.5rem 0",
  fontFamily: "system-ui, sans-serif",
  fontSize: "0.95rem",
};

const headerStyle: React.CSSProperties = {
  fontWeight: 600,
  marginBottom: "0.4rem",
};

const buttonRow: React.CSSProperties = {
  display: "flex",
  gap: "0.4rem",
  marginTop: "0.5rem",
};

function buttonStyle(kind: "approve" | "reject" | "link"): React.CSSProperties {
  const base: React.CSSProperties = {
    padding: "0.3rem 0.7rem",
    border: "none",
    borderRadius: 4,
    fontSize: "0.85rem",
    fontWeight: 600,
    cursor: "pointer",
  };
  switch (kind) {
    case "approve":
      return { ...base, background: "#2e7d32", color: "white" };
    case "reject":
      return { ...base, background: "#c62828", color: "white" };
    case "link":
      return { ...base, background: "transparent", color: "#1976d2", textDecoration: "underline" };
  }
}

function decisionBadgeStyle(decision: string): React.CSSProperties {
  const palette: Record<string, { bg: string; fg: string }> = {
    APPROVED: { bg: "#2e7d32", fg: "white" },
    REJECTED: { bg: "#c62828", fg: "white" },
    ESCALATED: { bg: "#ed6c02", fg: "white" },
  };
  const colors = palette[decision] ?? { bg: "#666", fg: "white" };
  return {
    display: "inline-block",
    padding: "0.15rem 0.55rem",
    borderRadius: 12,
    fontSize: "0.8rem",
    fontWeight: 700,
    background: colors.bg,
    color: colors.fg,
  };
}

type Props = {
  approvalRequestId: string;
};

export function ApprovalCard({ approvalRequestId }: Props) {
  const entry = useChatStore((s) => s.approvals[approvalRequestId]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!entry) return null;

  const submit = async (decision: DecisionLabel) => {
    setBusy(true);
    setError(null);
    try {
      await governanceService.decide(approvalRequestId, decision);
      // Optimistic: mark decision locally so UI updates even before
      // ApprovalReceived SSE arrives. The SSE event will overwrite if needed.
      useChatStore.setState((s) => ({
        approvals: {
          ...s.approvals,
          [approvalRequestId]: {
            ...s.approvals[approvalRequestId],
            decision: decision.toUpperCase(),
          },
        },
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const riskColor = RISK_COLOR[entry.riskLevel] ?? "#666";
  const isPending = entry.decision === null;

  return (
    <div style={cardStyle} role="region" aria-label="HITL approval">
      <div style={headerStyle}>
        🔔 Approval requested —{" "}
        <span style={{ color: riskColor, fontWeight: 700 }}>{entry.riskLevel}</span> risk
      </div>
      <div style={{ fontSize: "0.85rem", color: "#666" }}>
        Request ID: <code>{approvalRequestId}</code>
      </div>

      {!isPending && (
        <div style={{ marginTop: "0.5rem" }}>
          Decision:{" "}
          <span style={decisionBadgeStyle(entry.decision ?? "")}>{entry.decision}</span>
        </div>
      )}

      {error && (
        <div role="alert" style={{ color: "#c62828", marginTop: "0.4rem", fontSize: "0.85rem" }}>
          {error}
        </div>
      )}

      {isPending && (
        <div style={buttonRow}>
          <button
            type="button"
            style={buttonStyle("approve")}
            onClick={() => void submit("approved")}
            disabled={busy}
          >
            {busy ? "…" : "Approve"}
          </button>
          <button
            type="button"
            style={buttonStyle("reject")}
            onClick={() => void submit("rejected")}
            disabled={busy}
          >
            {busy ? "…" : "Reject"}
          </button>
          <a href="/governance/approvals" style={buttonStyle("link")}>
            Open governance page →
          </a>
        </div>
      )}
    </div>
  );
}
