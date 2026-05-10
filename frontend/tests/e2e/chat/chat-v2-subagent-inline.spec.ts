/**
 * File: frontend/tests/e2e/chat/chat-v2-subagent-inline.spec.ts
 * Purpose: Playwright e2e — Sprint 57.12 US-6 inline SubagentTree panel on chat-v2.
 * Category: Frontend / e2e / chat
 * Scope: Phase 57 / Sprint 57.12 Day 4 / US-8
 *
 * Description:
 *   Validates the chat-v2 inline SubagentTree panel (US-6 §3.8) end-to-end via
 *   a mocked SSE stream (page.route() per feedback_e2e_network_mocking_pattern):
 *     - Pre-session: SubagentTree renders null, chat-v2 unchanged.
 *     - After SSE with subagent_spawned → subagent_completed: the panel appears
 *       (`subagent-tree`) with a node showing the status badge transition
 *       (running → Done) + tokens + summary snippet.
 *
 *   AD-Subagent-RealShip-E2E (DEFERRED, plan §4.2 STRETCH): the real-backend
 *   spawn_subagent flow (Cat 11 dispatcher firing live SubagentSpawned events
 *   over a real SSE connection) is deferred to Phase 58+ — Playwright SSE mock
 *   at the network layer is the established pattern (3 prior sprints —
 *   verification, governance, approval — all deferred their real-flow variants
 *   for the same brittleness reason).
 *
 * Created: 2026-05-10 (Sprint 57.12 Day 4 / US-8)
 *
 * Modification History (newest-first):
 *   - 2026-05-10: Initial creation (Sprint 57.12 Day 4 / US-8)
 *
 * Related:
 *   - frontend/src/pages/chat-v2/index.tsx (mounts <SubagentTree />)
 *   - frontend/src/features/subagent/components/SubagentTree.tsx
 *   - frontend/src/features/chat_v2/store/chatStore.ts (subagents slice + mergeEvent)
 *   - tests/e2e/fixtures/approval-fixtures.ts (mockChatSSE)
 *   - tests/e2e/fixtures/auth-fixtures.ts (seedAuthJwt)
 */

import { expect, test } from "@playwright/test";

import { mockChatSSE } from "../fixtures/approval-fixtures";
import { seedAuthJwt } from "../fixtures/auth-fixtures";

test.describe("Sprint 57.12 US-6 — chat-v2 inline SubagentTree", () => {
  test("inline panel hidden before any session, shows spawned→completed node after SSE", async ({
    page,
  }) => {
    await seedAuthJwt(page);
    await mockChatSSE(page, [
      {
        event: "loop_start",
        data: { session_id: "ssn-sa-1", request_id: "req-sa-1", trace_id: null },
      },
      { event: "turn_start", data: { turn_num: 1, trace_id: null } },
      {
        event: "subagent_spawned",
        data: {
          subagent_id: "sa-12345678-aaaa-bbbb-cccc-ddddeeeeffff",
          mode: "fork",
          parent_session_id: "ssn-sa-1",
        },
      },
      {
        event: "subagent_completed",
        data: {
          subagent_id: "sa-12345678-aaaa-bbbb-cccc-ddddeeeeffff",
          summary: "Researched the docs and returned a 3-point answer.",
          tokens_used: 842,
        },
      },
      {
        event: "loop_end",
        data: { stop_reason: "end_turn", total_turns: 1, trace_id: null },
      },
    ]);

    await page.goto("/chat-v2/");

    // Pre-session: SubagentTree renders null.
    await expect(page.getByRole("heading", { level: 1, name: "Chat (V2)" })).toBeVisible();
    await expect(page.getByTestId("subagent-tree")).toHaveCount(0);

    // Send a message → SSE consumed → subagents slice populated.
    const textarea = page.getByPlaceholder(/Ask the agent/i);
    await textarea.fill("Spawn a subagent");
    await textarea.press("Enter");

    // Panel visible; node present; status badge resolved to completed (Done).
    await expect(page.getByTestId("subagent-tree")).toBeVisible();
    const node = page.getByTestId("subagent-node-sa-12345678-aaaa-bbbb-cccc-ddddeeeeffff");
    await expect(node).toBeVisible();
    await expect(node.getByTestId("subagent-status-badge-completed")).toBeVisible();
    // Tokens + summary snippet are scoped to the node row (the LoopVisualizer
    // debug tree also echoes the raw event JSON, so an unscoped getByText is
    // ambiguous).
    await expect(node.getByText(/842 tok/i)).toBeVisible();
    await expect(node.getByText(/Researched the docs/i)).toBeVisible();
  });
});
