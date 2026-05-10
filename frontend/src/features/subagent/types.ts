/**
 * File: frontend/src/features/subagent/types.ts
 * Purpose: TypeScript types for Cat 11 subagent SSE events + UI tree node (Sprint 57.12 US-3).
 * Category: Frontend / subagent / types
 * Scope: Phase 57 / Sprint 57.12 Day 2 / US-3
 *
 * Description:
 *   Single-source TS contract for the subagent feature folder consumed by:
 *     - components/SubagentTree.tsx (US-6 chat-v2 inline panel)
 *     - components/SubagentStatusBadge.tsx (3-state badge)
 *     - chat_v2/store/chatStore.ts (subagents slice; mergeEvent SSE branch)
 *
 *   Backend authority: api/v1/chat/sse.py — SubagentSpawned → 'subagent_spawned',
 *   SubagentCompleted → 'subagent_completed'. Per Sprint 57.12 Day 1 D1-005:
 *   SubagentCompleted carries only subagent_id / summary / tokens_used (no
 *   success/error_class field on the 17.md §4 contract). UI derives status:
 *   Spawned event = "running"; Completed event = "completed". (Failure shows
 *   as empty summary — richer error metadata is AD-Cat11-Completed-ErrorFields
 *   Phase 58+ carryover.)
 *
 * Created: 2026-05-10 (Sprint 57.12 Day 2 / US-3)
 *
 * Modification History (newest-first):
 *   - 2026-05-10: Initial creation (Sprint 57.12 Day 2 / US-3)
 *
 * Related:
 *   - backend/src/api/v1/chat/sse.py (SSE serializer)
 *   - backend/src/agent_harness/subagent/dispatcher.py (emission point)
 *   - frontend/src/features/chat_v2/types.ts (LoopEvent union — extended in US-6)
 *   - sprint-57-12-plan.md §US-3 + §US-6
 */

export type SubagentSpawnedEvent = {
  type: "subagent_spawned";
  data: {
    subagent_id: string | null;
    mode: string; // fork / teammate / handoff / as_tool
    parent_session_id: string | null;
  };
};

export type SubagentCompletedEvent = {
  type: "subagent_completed";
  data: {
    subagent_id: string | null;
    summary: string;
    tokens_used: number;
  };
};

/** Discriminated union of the 2 Cat 11 SSE event types. */
export type SubagentEvent = SubagentSpawnedEvent | SubagentCompletedEvent;

/** Derived UI status per Day 1 D1-005 (event ordering, not a contract field). */
export type SubagentStatus = "running" | "completed";

/**
 * UI tree node accumulated by chatStore.subagents slice from the SSE stream.
 * Parent→child links derived from parent_session_id. Root nodes have
 * parentId === chat session_id.
 */
export interface SubagentNode {
  subagentId: string;
  /** parent session id (chat session for root nodes; another subagent for nested). */
  parentId: string | null;
  mode: string;
  status: SubagentStatus;
  /** populated when subagent_completed arrives. */
  summary: string | null;
  tokensUsed: number | null;
  /** epoch ms when subagent_spawned arrived. */
  spawnedAt: number;
}
