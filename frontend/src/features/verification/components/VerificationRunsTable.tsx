/* eslint-disable no-restricted-syntax -- mockup verbatim CSS literals; mockup-fidelity (Sprint 57.41). See reference/design-mockups/page-extras.jsx L855-878. */
/**
 * File: frontend/src/features/verification/components/VerificationRunsTable.tsx
 * Purpose: Recent verification runs table — 6 columns matching mockup VerificationPage table.
 * Category: Frontend / verification / components
 * Scope: Phase 57 / Sprint 57.41 Day 1 (mockup-fidelity rebuild)
 *
 * Description:
 *   Verbatim port of `reference/design-mockups/page-extras.jsx:855-878`
 *   ("Recent verification runs" Card). Renders a 6-column table:
 *     1. Status circle (16×16 rounded-full, success/danger tone)
 *     2. Claim + evidence dual-line cell
 *     3. Agent (mono)
 *     4. Kind (Badge success tone)
 *     5. Score (mono tnum, color tiered: >0.85 success / >0.6 warning / else danger)
 *     6. When (subtle relative time)
 *
 *   Mockup uses fixture VERIFY_CLAIMS shape; production maps real
 *   VerificationLogItem fields via per-row adapter (see plan §3.7):
 *     agent ← verifier_name
 *     claim ← passed ? "${verifier_name} check passed" : (reason ?? "verification failed")
 *     evidence ← (reason ?? "no evidence text").slice(0, 80)
 *     ok ← passed
 *     score ← score ?? (passed ? 0.95 : 0.5)
 *     kind ← verifier_type (rules_based / llm_judge / external)
 *     at ← relative time from created_at_ms (now / Nm ago / Nh ago)
 *
 *   Empty / error / loading states handled with simple in-table rows
 *   (skeleton-style for loading, subtle for empty, danger banner for error).
 *
 * Key Components:
 *   - VerificationRunsTable: stateless table; items prop array
 *   - formatRelativeTime: created_at_ms → "now" / "Nm ago" / "Nh ago" / "Nd ago"
 *
 * Created: 2026-05-25 (Sprint 57.41 Day 1)
 * Last Modified: 2026-05-25
 *
 * Modification History (newest-first):
 *   - 2026-05-25: Initial creation (Sprint 57.41 Day 1) — verification view full mockup-fidelity rebuild
 *
 * Related:
 *   - reference/design-mockups/page-extras.jsx L855-878
 *   - ../types.ts (VerificationLogItem)
 *   - ../../../components/mockup-ui.tsx (Card, Badge, Icon primitives)
 */

import { Badge, Card, Icon } from "../../../components/mockup-ui";
import type { VerificationLogItem } from "../types";

interface Props {
  items: VerificationLogItem[];
  isLoading?: boolean;
  isError?: boolean;
}

function formatRelativeTime(epochMs: number): string {
  const deltaMs = Date.now() - epochMs;
  if (deltaMs < 60_000) return "now";
  const minutes = Math.floor(deltaMs / 60_000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(deltaMs / 3_600_000);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(deltaMs / 86_400_000);
  return `${days}d ago`;
}

function adaptItem(item: VerificationLogItem) {
  const score = item.score ?? (item.passed ? 0.95 : 0.5);
  return {
    id: item.id,
    ok: item.passed,
    claim: item.passed
      ? `${item.verifier_name} check passed`
      : (item.reason ?? "verification failed"),
    evidence: (item.reason ?? "no evidence text").slice(0, 80),
    agent: item.verifier_name,
    kind: item.verifier_type,
    score,
    at: formatRelativeTime(item.created_at_ms),
  };
}

export function VerificationRunsTable({ items, isLoading, isError }: Props) {
  return (
    <Card
      title="Recent verification runs"
      subtitle="Most recent first · failures pinned"
      bodyClass="flush"
    >
      <table className="table">
        <thead>
          <tr>
            <th></th>
            <th>Claim</th>
            <th>Agent</th>
            <th>Kind</th>
            <th style={{ textAlign: "right" }}>Score</th>
            <th>When</th>
          </tr>
        </thead>
        <tbody>
          {isError ? (
            <tr>
              <td colSpan={6} className="subtle" style={{ padding: 14, color: "var(--danger)" }}>
                Failed to load verification runs.
              </td>
            </tr>
          ) : isLoading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <tr key={`skel-${i}`}>
                <td colSpan={6} className="subtle" style={{ padding: 10 }}>
                  <span className="mono" style={{ opacity: 0.4 }}>loading…</span>
                </td>
              </tr>
            ))
          ) : items.length === 0 ? (
            <tr>
              <td colSpan={6} className="subtle" style={{ padding: 14 }}>
                No verification runs yet.
              </td>
            </tr>
          ) : (
            items.map((raw) => {
              const c = adaptItem(raw);
              const scoreColor =
                c.score > 0.85
                  ? "var(--success)"
                  : c.score > 0.6
                    ? "var(--warning)"
                    : "var(--danger)";
              return (
                <tr key={c.id}>
                  <td>
                    {c.ok ? (
                      <span
                        style={{
                          width: 16,
                          height: 16,
                          borderRadius: "50%",
                          background: "oklch(from var(--success) l c h / 0.2)",
                          color: "var(--success)",
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        <Icon name="check" size={10} />
                      </span>
                    ) : (
                      <span
                        style={{
                          width: 16,
                          height: 16,
                          borderRadius: "50%",
                          background: "oklch(from var(--danger) l c h / 0.2)",
                          color: "var(--danger)",
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        <Icon name="x" size={10} />
                      </span>
                    )}
                  </td>
                  <td>
                    <div style={{ fontSize: 12.5 }}>{c.claim}</div>
                    <div className="subtle mono" style={{ fontSize: 11, marginTop: 2 }}>
                      evidence: {c.evidence}
                    </div>
                  </td>
                  <td className="mono" style={{ fontSize: 11.5, color: "var(--fg-muted)" }}>
                    {c.agent}
                  </td>
                  <td>
                    <Badge tone="success">{c.kind}</Badge>
                  </td>
                  <td
                    className="mono tnum"
                    style={{ textAlign: "right", color: scoreColor }}
                  >
                    {c.score.toFixed(2)}
                  </td>
                  <td className="subtle" style={{ fontSize: 11.5 }}>
                    {c.at}
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </Card>
  );
}
