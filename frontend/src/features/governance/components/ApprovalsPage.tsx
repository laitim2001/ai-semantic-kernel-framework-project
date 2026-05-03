/**
 * File: frontend/src/features/governance/components/ApprovalsPage.tsx
 * Purpose: Page-level container — fetches pending list + renders list/modal.
 * Category: Frontend / governance / components
 * Scope: Phase 53 / Sprint 53.5 US-1
 *
 * Description:
 *   Polls GET /api/v1/governance/approvals every 30s while mounted (no SSE
 *   topic for governance.approvals.pending in 53.5 — frontend Playwright +
 *   real-time updates via SSE deferred to AD-Front-1 follow-up sprint).
 *
 *   On row click, opens DecisionModal; on submit, calls governanceService.decide
 *   then refreshes the list.
 *
 * Created: 2026-05-04 (Sprint 53.5 Day 3)
 *
 * Related:
 *   - ./ApprovalList.tsx
 *   - ./DecisionModal.tsx
 *   - ../services/governanceService.ts
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { governanceService } from "../services/governanceService";
import type { ApprovalSummary, DecisionLabel } from "../types";
import { ApprovalList } from "./ApprovalList";
import { DecisionModal } from "./DecisionModal";

const POLL_INTERVAL_MS = 30_000;

const pageStyle: React.CSSProperties = {
  padding: "1.5rem 2rem",
  fontFamily: "system-ui, sans-serif",
};

const headerRow: React.CSSProperties = {
  display: "flex",
  alignItems: "baseline",
  justifyContent: "space-between",
  marginBottom: "1rem",
};

const buttonStyle: React.CSSProperties = {
  padding: "0.4rem 0.9rem",
  border: "1px solid #1976d2",
  background: "white",
  color: "#1976d2",
  borderRadius: 4,
  cursor: "pointer",
  fontSize: "0.9rem",
};

export function ApprovalsPage() {
  const [items, setItems] = useState<ApprovalSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<ApprovalSummary | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const refresh = useCallback(async () => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    try {
      const list = await governanceService.listPending(ctrl.signal);
      setItems(list);
      setError(null);
    } catch (err) {
      if ((err as { name?: string })?.name === "AbortError") return;
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const handle = window.setInterval(() => {
      void refresh();
    }, POLL_INTERVAL_MS);
    return () => {
      window.clearInterval(handle);
      abortRef.current?.abort();
    };
  }, [refresh]);

  const submit = async (decision: DecisionLabel, reason?: string) => {
    if (!selected) return;
    await governanceService.decide(selected.request_id, decision, reason);
    void refresh();
  };

  return (
    <div style={pageStyle}>
      <div style={headerRow}>
        <h2 style={{ margin: 0 }}>Pending Approvals</h2>
        <button type="button" style={buttonStyle} onClick={() => void refresh()} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {error && (
        <div role="alert" style={{ color: "#c62828", marginBottom: "1rem" }}>
          Failed to load approvals: {error}
        </div>
      )}

      <ApprovalList approvals={items} onSelect={setSelected} />

      {selected && (
        <DecisionModal
          approval={selected}
          onSubmit={submit}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
