/**
 * File: frontend/src/features/subagent/components/SubagentStatusBadge.tsx
 * Purpose: Visual badge for SubagentStatus with 2-state variants + mode label (Sprint 57.12 US-3).
 * Category: Frontend / subagent / components
 * Scope: Phase 57 / Sprint 57.12 Day 2 / US-3 + US-6
 *
 * Description:
 *   Tailwind-only utility classes per .claude/rules/frontend-react.md + STYLE.md
 *   §3. 2 status variants (per Day 1 D1-005 — UI derives from event ordering):
 *     - running   → blue (subagent_spawned received, no subagent_completed yet)
 *     - completed → green (subagent_completed received)
 *
 *   Also renders the subagent `mode` (fork / teammate / handoff / as_tool) as
 *   a muted suffix so SubagentTree nodes show both at a glance.
 *
 *   Note: Sprint 57.12 only emits running/completed (no `error` variant —
 *   AD-Cat11-Completed-ErrorFields Phase 58+ would add it). Mirrors
 *   VerifierTypeBadge.tsx (Sprint 57.11) pattern.
 *
 * Created: 2026-05-10 (Sprint 57.12 Day 2 / US-3 + US-6)
 *
 * Related:
 *   - ../types.ts (SubagentStatus)
 *   - SubagentTree.tsx (US-6 consumer)
 *   - frontend/src/features/verification/components/VerifierTypeBadge.tsx (sibling pattern)
 */

import type { SubagentStatus } from "../types";

const STATUS_CLASSES: Record<SubagentStatus, string> = {
  running: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
};

const STATUS_LABELS: Record<SubagentStatus, string> = {
  running: "Running",
  completed: "Done",
};

export interface SubagentStatusBadgeProps {
  status: SubagentStatus;
  /** subagent mode (fork / teammate / handoff / as_tool) rendered as suffix. */
  mode?: string;
}

export function SubagentStatusBadge({ status, mode }: SubagentStatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ${STATUS_CLASSES[status]}`}
      data-testid={`subagent-status-badge-${status}`}
    >
      {STATUS_LABELS[status]}
      {mode ? <span className="font-normal opacity-70">· {mode}</span> : null}
    </span>
  );
}
