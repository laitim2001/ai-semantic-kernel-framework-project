/**
 * File: frontend/tests/unit/chat_v2/components/ChatHeader.test.tsx
 * Purpose: Vitest render coverage for Sprint 57.21 ChatHeader (Day 3 §3.2).
 * Category: Frontend / tests / unit / chat_v2
 * Scope: Phase 57.21 Day 3 §3.2
 *
 * Created: 2026-05-17 (Sprint 57.21 Day 3 §3.2)
 *
 * Modification History:
 *   - 2026-06-12: Sprint 57.107 B3 — active-session title test seeds store.sessions (was FIXTURE_SESSIONS lookup)
 *   - 2026-06-06: CHANGE-054 honest surface — fallback assertions "incident-responder"→"agent", "claude-haiku-4-5"→"real_llm" (model badge reflects real run/mode)
 *   - 2026-05-17: Initial creation (Sprint 57.21 Day 3 §3.2)
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ChatHeader } from "@/features/chat_v2/components/ChatHeader";
import { useChatStore } from "@/features/chat_v2/store/chatStore";

function setUp(overrides: { listOpen?: boolean; inspOpen?: boolean } = {}): {
  onToggleList: ReturnType<typeof vi.fn>;
  onToggleInsp: ReturnType<typeof vi.fn>;
} {
  const onToggleList = vi.fn();
  const onToggleInsp = vi.fn();
  render(
    <ChatHeader
      listOpen={overrides.listOpen ?? true}
      inspOpen={overrides.inspOpen ?? true}
      onToggleList={onToggleList}
      onToggleInsp={onToggleInsp}
    />,
  );
  return { onToggleList, onToggleInsp };
}

describe("ChatHeader (Sprint 57.21 Day 3 §3.2)", () => {
  beforeEach(() => {
    useChatStore.getState().reset();
  });
  afterEach(() => {
    useChatStore.getState().reset();
  });

  test("renders fallback title when no active session", () => {
    setUp();
    expect(screen.getByText("New session")).toBeInTheDocument();
    // Honest-surface (CHANGE-054): no active fixture session → neutral "agent"
    // label; model badge reflects the active mode ("real_llm" default, since no
    // llm_request has set currentModel yet) instead of the hardcoded "claude-haiku-4-5".
    expect(screen.getByText("agent")).toBeInTheDocument();
    expect(screen.getByText("real_llm")).toBeInTheDocument();
  });

  test("renders active session title from the store when activeSessionId is set", () => {
    // Sprint 57.107 B3: ChatHeader looks up the active session in store.sessions
    // (real GET /sessions data) instead of FIXTURE_SESSIONS.
    useChatStore.setState({
      sessions: [
        {
          id: "sess_91kxu",
          title: "Q4 compliance audit — PCI scope",
          agent: "compliance-auditor",
          turns: 42,
          status: "hitl",
          time: "2026-06-12 09:52",
          handoffParentId: null,
          agentRole: "compliance-auditor",
        },
      ],
      activeSessionId: "sess_91kxu",
    });
    setUp();
    expect(screen.getByText("Q4 compliance audit — PCI scope")).toBeInTheDocument();
    expect(screen.getByText("compliance-auditor")).toBeInTheDocument();
  });

  test("streaming indicator hidden when status=idle", () => {
    setUp();
    expect(screen.queryByText(/streaming/i)).toBeNull();
  });

  test("streaming indicator visible when status=running", () => {
    useChatStore.setState({ status: "running" });
    setUp();
    expect(screen.getByText(/streaming/i)).toBeInTheDocument();
  });

  test("provider neutral indicator always visible", () => {
    setUp();
    expect(screen.getByText(/provider: neutral/i)).toBeInTheDocument();
  });

  test("left panel toggle button data-active reflects listOpen + fires callback", async () => {
    const user = userEvent.setup();
    const { onToggleList } = setUp({ listOpen: true });
    const btn = screen.getByTestId("chat-header-toggle-list");
    expect(btn.getAttribute("data-active")).toBe("true");
    await user.click(btn);
    expect(onToggleList).toHaveBeenCalledTimes(1);
  });

  test("right panel toggle button data-active reflects inspOpen + fires callback", async () => {
    const user = userEvent.setup();
    const { onToggleInsp } = setUp({ listOpen: true, inspOpen: false });
    const btn = screen.getByTestId("chat-header-toggle-inspector");
    expect(btn.getAttribute("data-active")).toBe("false");
    await user.click(btn);
    expect(onToggleInsp).toHaveBeenCalledTimes(1);
  });

  test("Loop + Audit action buttons render", () => {
    setUp();
    expect(screen.getByText("Loop")).toBeInTheDocument();
    expect(screen.getByText("Audit")).toBeInTheDocument();
  });

  test("uses live totalTurns when > 0", () => {
    useChatStore.setState({ activeSessionId: "sess_91kxu", totalTurns: 5 });
    setUp();
    expect(screen.getByText(/5 turns/)).toBeInTheDocument();
  });
});
