/**
 * File: frontend/src/features/governance/components/ApprovalsPage.tsx
 * Purpose: Pending approvals page — polls list + handles row click → DecisionModal.
 * Category: Frontend / governance / components
 * Scope: Phase 53 / Sprint 53.5 US-1 → Sprint 57.9 US-2 Day 1 (Tailwind migration)
 *
 * Description:
 *   Polls GET /api/v1/governance/approvals every 30s while mounted (no SSE
 *   topic for governance.approvals.pending in 53.5 — frontend Playwright +
 *   real-time updates via SSE deferred to AD-Front-1 follow-up sprint).
 *
 *   On row click, opens DecisionModal; on submit, calls governanceService.decide
 *   then refreshes the list.
 *
 *   Sprint 57.9 US-2 Day 1: inline `style={{}}` migrated to Tailwind utility
 *   classes (per .claude/rules/frontend-react.md "no inline styles"); behavior
 *   100% preserved (regression sentinel: existing Vitest tests).
 *   Sprint 57.9 US-3 Day 2 will further refactor: drop manual setInterval +
 *   AbortController + useState/useEffect → consume `useApprovals` TanStack hook.
 *
 * Created: 2026-05-04 (Sprint 53.5 Day 3)
 * Last Modified: 2026-05-09
 *
 * Modification History (newest-first):
 *   - 2026-05-09: Sprint 57.9 US-2 Day 1 — Tailwind migration (drop inline styles)
 *   - 2026-05-04: Initial creation (Sprint 53.5 Day 3)
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
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <h2 className="m-0 text-xl font-semibold">Pending Approvals</h2>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={loading}
          className="inline-flex items-center rounded-md border border-primary bg-background px-3 py-1.5 text-sm font-medium text-primary hover:bg-primary/10 disabled:opacity-50"
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive"
        >
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
