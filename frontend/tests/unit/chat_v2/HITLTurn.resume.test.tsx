/**
 * File: frontend/tests/unit/chat_v2/HITLTurn.resume.test.tsx
 * Purpose: Vitest coverage for HITLTurn's Sprint 57.88 durable pause-resume trigger + guard.
 * Category: Frontend / tests / unit / chat_v2
 * Scope: Phase 57 / Sprint 57.88 Day 3 / US-5
 *
 * Description:
 *   HITLTurn's Approve button records the decision (governanceService.decide) and,
 *   ONLY for the deferred-pause flow (stopReason === "awaiting_approval"), drives
 *   the client resume (useLoopEventStream.resume). Asserts:
 *     - approve + awaiting_approval → decide("approved") + resume() fired
 *     - approve + non-paused stopReason → decide() fired, resume() NOT fired (guard
 *       protects the legacy blocking-HITL flow that continues server-side)
 *     - reject → decide("rejected") + resume() NOT fired
 *
 * Created: 2026-06-08 (Sprint 57.88 Day 3)
 *
 * Modification History:
 *   - 2026-06-08: Initial creation (Sprint 57.88 Day 3 / US-5)
 */

import "@testing-library/jest-dom/vitest";

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HITLTurn } from "@/features/chat_v2/components/turns/HITLTurn";
import { useChatStore } from "@/features/chat_v2/store/chatStore";
import type { HITLTurn as HITLTurnType } from "@/features/chat_v2/types";

const { decideSpy, resumeSpy } = vi.hoisted(() => ({
  decideSpy: vi.fn(),
  resumeSpy: vi.fn(),
}));

vi.mock("@/features/governance/services/governanceService", () => ({
  governanceService: { decide: decideSpy },
}));

vi.mock("@/features/chat_v2/hooks/useLoopEventStream", () => ({
  useLoopEventStream: () => ({
    send: vi.fn(),
    resume: resumeSpy,
    cancel: vi.fn(),
    isRunning: false,
  }),
}));

const makeTurn = (): HITLTurnType => ({
  role: "hitl",
  id: "h_1",
  at: "2026-06-08T00:00:00Z",
  title: "Approval required: HIGH",
  severity: "risk-high",
  tool: "echo_tool",
  payload: "—",
  rationale: "—",
  approvalRequestId: "ar-1",
  decision: null,
  countdownSec: null,
});

describe("HITLTurn — durable pause-resume trigger (Sprint 57.88)", () => {
  beforeEach(() => {
    decideSpy.mockResolvedValue(undefined);
    resumeSpy.mockReset();
  });

  afterEach(() => {
    useChatStore.getState().reset();
    vi.clearAllMocks();
  });

  it("approve while deferred-paused → decide(approved) + resume() fired", async () => {
    useChatStore.setState({ stopReason: "awaiting_approval" });
    render(<HITLTurn turn={makeTurn()} />);

    await userEvent.click(screen.getByTestId("approve-btn"));

    await waitFor(() => expect(decideSpy).toHaveBeenCalledWith("ar-1", "approved"));
    await waitFor(() => expect(resumeSpy).toHaveBeenCalledTimes(1));
  });

  it("approve when NOT deferred-paused → decide fired but resume() guarded off", async () => {
    useChatStore.setState({ stopReason: "end_turn" });
    render(<HITLTurn turn={makeTurn()} />);

    await userEvent.click(screen.getByTestId("approve-btn"));

    await waitFor(() => expect(decideSpy).toHaveBeenCalledWith("ar-1", "approved"));
    expect(resumeSpy).not.toHaveBeenCalled();
  });

  it("reject → decide(rejected) + resume() NOT fired", async () => {
    useChatStore.setState({ stopReason: "awaiting_approval" });
    render(<HITLTurn turn={makeTurn()} />);

    await userEvent.click(screen.getByTestId("reject-btn"));

    await waitFor(() => expect(decideSpy).toHaveBeenCalledWith("ar-1", "rejected"));
    expect(resumeSpy).not.toHaveBeenCalled();
  });
});
