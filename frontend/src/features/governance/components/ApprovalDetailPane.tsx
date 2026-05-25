/**
 * File: frontend/src/features/governance/components/ApprovalDetailPane.tsx
 * Purpose: Rich detail pane for selected approval — KvRow stack + tool payload + agent rationale + decision buttons.
 * Category: Frontend / governance / components
 * Scope: Phase 57 / Sprint 57.40 Day 1 (mockup-fidelity rebuild)
 *
 * Description:
 *   Verbatim port of `reference/design-mockups/page-governance.jsx:365-403`
 *   (right Card in 2-col Active layout). Renders:
 *     - Header: SevDot + request_id (mono); subtitle = session_title; Audit ghost button
 *     - 7-KvRow body: tool / risk / policy / scope / operator / age / SLA remaining
 *     - Field "Tool input payload": <pre> JSON-stringified tool_arguments
 *     - Field "Agent rationale": rationale text block (payload.reason ?? fallback)
 *     - 4-button col: Approve & continue (REAL onApprove) / Approve with edits…
 *       (AP-2 stub) / Reject (REAL onReject) / Escalate (AP-2 stub)
 *
 *   Empty state when no approval selected: subtle placeholder Card.
 *
 *   The mockup's `<Button variant="success" | "danger">` variants are not in
 *   our mockup-ui `Button` (variant union = "outline" | "primary" | "ghost").
 *   Per AD-Inline-Style-Rule-vs-Verbatim-Method, we use semantic
 *   `<button className="btn success">` etc. — styles-mockup.css L? defines
 *   the .btn.success / .btn.danger color classes.
 *
 * Key Components:
 *   - ApprovalDetailPane: controlled component (selection passed in via props)
 *   - formatSlaRemaining: ISO timestamp → "Xm Ys" / "expired" / "—"
 *
 * Created: 2026-05-25 (Sprint 57.40 Day 1)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Sprint 57.40 — initial creation (right-col rich Detail pane port)
 *
 * Related:
 *   - reference/design-mockups/page-governance.jsx L365-403
 *   - ../../../components/mockup-ui.tsx (Card / Button / Field / KvRow / SevDot / RiskBadge / Badge)
 *   - ../hooks/useApprovalDecide.ts (parent owns mutation; this component fires onApprove/onReject)
 */

/* eslint-disable no-restricted-syntax -- verbatim re-point: inline `style=` literals are mockup page-governance.jsx visual-layer copied byte-for-byte; re-expressing as Tailwind IS the drift bug this epic kills (STYLE.md §3 escape hatch + frontend-mockup-fidelity.md) */

import {
  Badge,
  Button,
  Card,
  Field,
  KvRow,
  RiskBadge,
} from "../../../components/mockup-ui";
import type { ApprovalSummary, RiskLevelLabel } from "../types";

interface Props {
  approval: ApprovalSummary | null;
  onApprove: () => void;
  onReject: () => void;
}

// Map ApprovalSummary risk_level (UPPERCASE) to mockup-ui RiskLevel (lowercase).
const RISK_MAP: Record<RiskLevelLabel, "low" | "medium" | "high" | "critical"> = {
  LOW: "low",
  MEDIUM: "medium",
  HIGH: "high",
  CRITICAL: "critical",
};

function formatSlaRemaining(iso: string): string {
  const ms = new Date(iso).getTime() - Date.now();
  if (Number.isNaN(ms)) return "—";
  if (ms < 0) return "expired";
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}m ${String(seconds).padStart(2, "0")}s`;
}

export function ApprovalDetailPane({ approval, onApprove, onReject }: Props) {
  if (!approval) {
    return (
      <Card title="Approval detail" subtitle="Select a request from the list">
        <div className="subtle" style={{ fontSize: 12, fontStyle: "italic" }}>
          Select an approval from the list to view details.
        </div>
      </Card>
    );
  }

  const riskKey = RISK_MAP[approval.risk_level];
  const toolName = approval.payload.tool_name ?? "—";
  const sessionTitle =
    typeof approval.payload.summary === "string"
      ? approval.payload.summary.slice(0, 80)
      : typeof approval.payload.reason === "string"
        ? approval.payload.reason.slice(0, 80)
        : approval.session_id;
  const scopeLabel = `tenant.${approval.tenant_id.slice(0, 8)}`;
  const slaRemaining = formatSlaRemaining(approval.sla_deadline);
  const toolArgs = approval.payload.tool_arguments ?? {};
  const rationale =
    typeof approval.payload.reason === "string"
      ? approval.payload.reason
      : "No rationale provided.";

  return (
    <Card
      title={
        <span className="row" style={{ gap: 6 }}>
          <span className={`sev-dot sev-${riskKey}`} />
          <span className="mono" style={{ fontSize: 12.5 }}>{approval.request_id}</span>
        </span>
      }
      subtitle={sessionTitle}
      bodyClass="dense"
      actions={<Button variant="ghost" size="sm" icon="audit">Audit</Button>}
    >
      <div className="col" style={{ gap: 6, fontSize: 12, marginBottom: 12 }}>
        <KvRow
          k="tool"
          v={<span className="mono" style={{ color: "var(--tool)" }}>{toolName}</span>}
        />
        <KvRow k="risk" v={<RiskBadge level={riskKey} />} />
        <KvRow k="policy" v={<Badge tone="warning">always_ask</Badge>} />
        <KvRow k="scope" v={<Badge>{scopeLabel}</Badge>} />
        <KvRow k="operator" v={approval.requester} />
        <KvRow k="age" v="0m 14s" mono />
        <KvRow
          k="SLA remaining"
          v={<span className="mono" style={{ color: "var(--warning)" }}>{slaRemaining}</span>}
        />
      </div>
      <Field label="Tool input payload">
        <pre
          style={{
            margin: 0,
            padding: 10,
            background: "var(--bg-2)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            fontFamily: "var(--font-mono)",
            fontSize: 11,
            lineHeight: 1.55,
            color: "var(--fg)",
            maxHeight: 160,
            overflowY: "auto",
          }}
        >
          {JSON.stringify(toolArgs, null, 2)}
        </pre>
      </Field>
      <div style={{ height: 8 }} />
      <Field label="Agent rationale">
        <div
          style={{
            padding: 10,
            background: "var(--bg-2)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            fontSize: 12,
            color: "var(--fg-muted)",
            lineHeight: 1.55,
          }}
        >
          {rationale}
        </div>
      </Field>
      <div className="thin-rule" />
      <div className="col" style={{ gap: 8 }}>
        <button type="button" className="btn success" onClick={onApprove}>
          Approve &amp; continue
        </button>
        <button
          type="button"
          className="btn outline"
          onClick={() => alert("Approve with edits — backend gap (Phase 58+)")}
        >
          Approve with edits…
        </button>
        <button type="button" className="btn danger" onClick={onReject}>
          Reject
        </button>
        <button
          type="button"
          className="btn ghost"
          style={{ fontSize: 12 }}
          onClick={() => alert("Escalate — backend gap (Phase 58+)")}
        >
          Escalate to L2 · @platform-l2
        </button>
      </div>
    </Card>
  );
}
