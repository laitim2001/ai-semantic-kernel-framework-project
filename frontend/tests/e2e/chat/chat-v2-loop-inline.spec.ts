/**
 * File: frontend/tests/e2e/chat/chat-v2-loop-inline.spec.ts
 * Purpose: Playwright e2e — Sprint 57.12 US-4 inline LoopVisualizer panel on chat-v2.
 * Category: Frontend / e2e / chat
 * Scope: Phase 57 / Sprint 57.12 Day 4 / US-8
 *
 * Description:
 *   Validates the chat-v2 inline LoopVisualizer panel (US-4 §3.8):
 *     - Before any session: panel renders null (inline mode), so chat-v2 looks
 *       unchanged from Sprint 57.8.
 *     - After an SSE turn (loop_start → turn_start → loop_end mocked via
 *       page.route() per feedback_e2e_network_mocking_pattern): the inline
 *       panel appears (`loop-visualizer-inline`) with a per-turn tree showing
 *       the parsed events.
 *
 * Created: 2026-05-10 (Sprint 57.12 Day 4 / US-8)
 *
 * Modification History (newest-first):
 *   - 2026-05-10: Initial creation (Sprint 57.12 Day 4 / US-8)
 *
 * Related:
 *   - frontend/src/pages/chat-v2/index.tsx (mounts <LoopVisualizer mode="inline" />)
 *   - frontend/src/features/orchestrator-loop/components/LoopVisualizer.tsx
 *   - tests/e2e/fixtures/approval-fixtures.ts (mockChatSSE)
 *   - tests/e2e/fixtures/auth-fixtures.ts (seedAuthJwt)
 */

import { expect, test } from "@playwright/test";

import { mockChatSSE } from "../fixtures/approval-fixtures";
import { seedAuthJwt } from "../fixtures/auth-fixtures";

test.describe("Sprint 57.12 US-4 — chat-v2 inline LoopVisualizer", () => {
  test("inline panel hidden before any session, appears after SSE turn", async ({ page }) => {
    await seedAuthJwt(page);
    await mockChatSSE(page, [
      {
        event: "loop_start",
        data: { session_id: "ssn-loop-1", request_id: "req-loop-1", trace_id: null },
      },
      { event: "turn_start", data: { turn_num: 1, trace_id: null } },
      {
        event: "loop_end",
        data: { stop_reason: "end_turn", total_turns: 1, trace_id: null },
      },
    ]);

    await page.goto("/chat-v2/");

    // Pre-session: inline LoopVisualizer renders null (mode="inline" + empty rawEvents).
    await expect(page.getByRole("heading", { level: 1, name: "Chat (V2)" })).toBeVisible();
    await expect(page.getByTestId("loop-visualizer-inline")).toHaveCount(0);

    // Send a message → SSE stream consumed → store.rawEvents populated.
    const textarea = page.getByPlaceholder(/Ask the agent/i);
    await textarea.fill("Trigger a loop turn");
    await textarea.press("Enter");

    // Inline panel now visible with a turn-1 bucket + the loop_start event row.
    await expect(page.getByTestId("loop-visualizer-inline")).toBeVisible();
    await expect(page.getByTestId("loop-turn-1")).toBeVisible();
    await expect(page.getByTestId("loop-event-loop_start")).toBeVisible();
  });
});
