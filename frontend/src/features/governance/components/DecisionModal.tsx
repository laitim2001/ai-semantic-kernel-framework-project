/**
 * File: frontend/src/features/governance/components/DecisionModal.tsx
 * Purpose: Modal dialog with Approve / Reject / Escalate buttons + reason input.
 * Category: Frontend / governance / components
 * Scope: Phase 53 / Sprint 53.5 US-1
 *
 * Created: 2026-05-04 (Sprint 53.5 Day 3)
 *
 * Related:
 *   - ./ApprovalsPage.tsx (parent)
 *   - ../services/governanceService.ts (decide call)
 */

import { useState } from "react";
import type { ApprovalSummary, DecisionLabel } from "../types";

type Props = {
  approval: ApprovalSummary;
  onSubmit: (decision: DecisionLabel, reason?: string) => Promise<void>;
  onClose: () => void;
};

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.45)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 100,
};

const dialogStyle: React.CSSProperties = {
  background: "white",
  borderRadius: 8,
  padding: "1.5rem 2rem",
  minWidth: 480,
  maxWidth: 720,
  boxShadow: "0 8px 24px rgba(0,0,0,0.2)",
  fontFamily: "system-ui, sans-serif",
};

const headerStyle: React.CSSProperties = {
  margin: 0,
  marginBottom: "0.75rem",
  fontSize: "1.25rem",
};

const fieldRow: React.CSSProperties = {
  display: "flex",
  gap: "0.5rem",
  margin: "0.4rem 0",
  fontSize: "0.95rem",
};

const labelStyle: React.CSSProperties = {
  fontWeight: 600,
  color: "#444",
  minWidth: 110,
};

const reasonBox: React.CSSProperties = {
  width: "100%",
  marginTop: "0.5rem",
  padding: "0.5rem",
  fontSize: "0.95rem",
  fontFamily: "inherit",
  border: "1px solid #ccc",
  borderRadius: 4,
  resize: "vertical",
  minHeight: 80,
};

const buttonRow: React.CSSProperties = {
  display: "flex",
  gap: "0.5rem",
  justifyContent: "flex-end",
  marginTop: "1.25rem",
};

function buttonStyle(kind: "approve" | "reject" | "escalate" | "cancel"): React.CSSProperties {
  const base: React.CSSProperties = {
    padding: "0.5rem 1rem",
    border: "none",
    borderRadius: 4,
    fontSize: "0.95rem",
    fontWeight: 600,
    cursor: "pointer",
  };
  switch (kind) {
    case "approve":
      return { ...base, background: "#2e7d32", color: "white" };
    case "reject":
      return { ...base, background: "#c62828", color: "white" };
    case "escalate":
      return { ...base, background: "#ed6c02", color: "white" };
    case "cancel":
      return { ...base, background: "#e0e0e0", color: "#333" };
  }
}

export function DecisionModal({ approval, onSubmit, onClose }: Props) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (decision: DecisionLabel) => {
    setBusy(true);
    setError(null);
    try {
      await onSubmit(decision, reason.trim() || undefined);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const toolName = approval.payload.tool_name ?? "(unknown tool)";
  const summary = approval.payload.summary ?? approval.payload.reason ?? "";

  return (
    <div style={overlayStyle} onClick={onClose} role="presentation">
      <div style={dialogStyle} onClick={(e) => e.stopPropagation()} role="dialog">
        <h3 style={headerStyle}>Review approval — {toolName}</h3>
        <div style={fieldRow}>
          <span style={labelStyle}>Request ID:</span>
          <code>{approval.request_id}</code>
        </div>
        <div style={fieldRow}>
          <span style={labelStyle}>Risk:</span>
          <span>{approval.risk_level}</span>
        </div>
        <div style={fieldRow}>
          <span style={labelStyle}>Requester:</span>
          <span>{approval.requester}</span>
        </div>
        <div style={fieldRow}>
          <span style={labelStyle}>SLA deadline:</span>
          <span>{new Date(approval.sla_deadline).toLocaleString()}</span>
        </div>
        {summary && (
          <div style={fieldRow}>
            <span style={labelStyle}>Reason:</span>
            <span>{summary}</span>
          </div>
        )}
        {approval.payload.tool_arguments && (
          <div style={fieldRow}>
            <span style={labelStyle}>Arguments:</span>
            <pre style={{ margin: 0, fontSize: "0.85rem", background: "#f5f5f5", padding: "0.4rem", borderRadius: 4 }}>
              {JSON.stringify(approval.payload.tool_arguments, null, 2)}
            </pre>
          </div>
        )}

        <label style={{ display: "block", marginTop: "1rem", fontSize: "0.95rem", fontWeight: 600 }}>
          Reviewer reason (optional):
          <textarea
            style={reasonBox}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Optional context for the audit log"
            disabled={busy}
          />
        </label>

        {error && (
          <div role="alert" style={{ color: "#c62828", marginTop: "0.5rem", fontSize: "0.9rem" }}>
            {error}
          </div>
        )}

        <div style={buttonRow}>
          <button type="button" style={buttonStyle("cancel")} onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button type="button" style={buttonStyle("escalate")} onClick={() => submit("escalated")} disabled={busy}>
            Escalate
          </button>
          <button type="button" style={buttonStyle("reject")} onClick={() => submit("rejected")} disabled={busy}>
            Reject
          </button>
          <button type="button" style={buttonStyle("approve")} onClick={() => submit("approved")} disabled={busy}>
            Approve
          </button>
        </div>
      </div>
    </div>
  );
}
