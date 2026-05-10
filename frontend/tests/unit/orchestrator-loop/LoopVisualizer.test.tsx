/**
 * File: frontend/tests/unit/orchestrator-loop/LoopVisualizer.test.tsx
 * Purpose: Vitest tests for LoopVisualizer component — dual-mode rendering + turn grouping + event severity.
 * Category: Frontend / tests / unit / orchestrator-loop
 * Scope: Phase 57 / Sprint 57.12 Day 2 / US-4
 *
 * Created: 2026-05-10 (Sprint 57.12 Day 2 / US-4)
 *
 * Modification History:
 *   - 2026-05-10: Initial creation (Sprint 57.12 Day 2 / US-4)
 */

import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test } from "vitest";

import { useChatStore } from "@/features/chat_v2/store/chatStore";
import type { LoopEvent } from "@/features/chat_v2/types";
import { LoopVisualizer } from "@/features/orchestrator-loop/components/LoopVisualizer";

function feed(events: LoopEvent[]): void {
  const merge = useChatStore.getState().mergeEvent;
  for (const ev of events) merge(ev);
}

describe("LoopVisualizer (Sprint 57.12 US-4)", () => {
  beforeEach(() => {
    useChatStore.getState().reset();
  });
  afterEach(() => {
    useChatStore.getState().reset();
  });

  test("inline mode renders null when no events", () => {
    const { container } = render(<LoopVisualizer mode="inline" />);
    expect(container.firstChild).toBeNull();
  });

  test("standalone mode renders empty-state message when no events", () => {
    render(<LoopVisualizer mode="standalone" />);
    expect(screen.getByText(/No loop events yet/i)).toBeInTheDocument();
  });

  test("renders mixed event types grouped per turn (inline)", () => {
    feed([
      { type: "loop_start", data: { session_id: "s1", request_id: "r1" } },
      { type: "turn_start", data: { turn_num: 0 } },
      { type: "llm_request", data: { model: "gpt-x", tokens_in: 100 } },
      {
        type: "llm_response",
        data: { content: "hello", tool_calls: [], thinking: null },
      },
      { type: "turn_start", data: { turn_num: 1 } },
      {
        type: "tool_call_result",
        data: {
          tool_call_id: "tc1",
          tool_name: "search",
          duration_ms: 42,
          result: "ok",
          is_error: false,
        },
      },
      { type: "loop_end", data: { stop_reason: "end_turn", total_turns: 2 } },
    ]);
    render(<LoopVisualizer mode="inline" />);
    expect(screen.getByTestId("loop-visualizer-inline")).toBeInTheDocument();
    expect(screen.getByTestId("loop-turn-0")).toBeInTheDocument();
    expect(screen.getByTestId("loop-turn-1")).toBeInTheDocument();
    // event rows present for several known types
    expect(screen.getByTestId("loop-event-llm_request")).toBeInTheDocument();
    expect(screen.getByTestId("loop-event-tool_call_result")).toBeInTheDocument();
  });

  test("standalone mode renders summary header with turn + event counts", () => {
    feed([
      { type: "loop_start", data: { session_id: "s1", request_id: "r1" } },
      { type: "turn_start", data: { turn_num: 0 } },
      { type: "loop_end", data: { stop_reason: "end_turn", total_turns: 1 } },
    ]);
    render(<LoopVisualizer mode="standalone" />);
    const summary = screen.getByTestId("loop-visualizer-summary");
    expect(summary).toHaveTextContent("Events:");
    expect(summary).toHaveTextContent("3");
  });

  test("failed events get red left border (verification_failed)", () => {
    feed([
      { type: "turn_start", data: { turn_num: 0 } },
      {
        type: "verification_failed",
        data: {
          verifier: "topic_check",
          verifier_type: "llm_judge",
          reason: "off-topic",
          suggested_correction: null,
        },
      },
    ]);
    render(<LoopVisualizer mode="standalone" />);
    const evRow = screen.getByTestId("loop-event-verification_failed");
    expect(evRow.className).toContain("border-red-500");
  });

  test("inline mode collapses turns older than the last 5", () => {
    const events: LoopEvent[] = [];
    for (let i = 0; i < 8; i++) {
      events.push({ type: "turn_start", data: { turn_num: i } });
      events.push({ type: "llm_request", data: { model: "gpt-x", tokens_in: 1 } });
    }
    feed(events);
    render(<LoopVisualizer mode="inline" />);
    // 8 turns → 3 collapsed, 5 visible
    expect(screen.getByText(/3 earlier turns collapsed/i)).toBeInTheDocument();
    expect(screen.queryByTestId("loop-turn-0")).toBeNull();
    expect(screen.getByTestId("loop-turn-7")).toBeInTheDocument();
  });
});
