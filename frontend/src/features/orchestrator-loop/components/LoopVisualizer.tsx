/**
 * File: frontend/src/features/orchestrator-loop/components/LoopVisualizer.tsx
 * Purpose: TAO/ReAct state machine tree consuming the chat-v2 LoopEvent stream (Sprint 57.12 US-4).
 * Category: Frontend / orchestrator-loop / components
 * Scope: Phase 57 / Sprint 57.12 Day 2 / US-4 (was Phase 49.1 placeholder)
 *
 * Description:
 *   Renders a real-time tree of the agent loop, grouped per turn. Single
 *   component mounted in 2 contexts:
 *     - <LoopVisualizer mode="inline" />     — chat-v2 inline panel; compact;
 *       auto-collapses turns older than the last 5; max-height + scroll.
 *     - <LoopVisualizer mode="standalone" /> — /loop-debug page; full screen;
 *       all turns expanded; total-elapsed/tokens summary header.
 *
 *   Consumes `useChatStore` rawEvents (same source as chat-v2 SSE). Groups
 *   events into turn buckets at each `turn_start` event (events before the
 *   first turn_start — e.g. loop_start — go in turn 0). Per Day 1 D2-003:
 *   the frontend only knows the ~14 serialized SSE event types
 *   (the chat_v2 LoopEvent union), not all 22 backend LoopEvent subclasses;
 *   any event present in rawEvents is rendered with its type + key fields.
 *
 *   Visual encoding per STYLE.md §3:
 *     - failed events (tool_call_result is_error / verification_failed /
 *       guardrail_triggered) → red left border
 *     - warn-ish events (approval_requested) → amber left border
 *     - success/neutral → muted gray border
 *
 * Created: 2026-04-29 (Sprint 49.1 placeholder); 2026-05-10 (Sprint 57.12 real ship)
 * Last Modified: 2026-05-10
 *
 * Modification History (newest-first):
 *   - 2026-05-10: Sprint 57.12 US-4 Day 2 — dual-mount LoopVisualizer (real ship)
 *
 * Related:
 *   - frontend/src/features/chat_v2/store/chatStore.ts (rawEvents source)
 *   - frontend/src/features/chat_v2/types.ts (LoopEvent union)
 *   - frontend/src/pages/loop-debug/index.tsx (standalone mount; Day 2 §2.7)
 *   - sprint-57-12-plan.md §US-4
 */

import { useChatStore } from "@/features/chat_v2/store/chatStore";
import type { LoopEvent } from "@/features/chat_v2/types";

export type LoopVisualizerMode = "inline" | "standalone";

export interface LoopVisualizerProps {
  mode: LoopVisualizerMode;
}

interface TurnBucket {
  turnNum: number;
  events: LoopEvent[];
}

interface MutableBucket extends TurnBucket {
  /** True once a turn_start marker has been seen for this bucket. */
  hasTurnMarker: boolean;
}

/**
 * Group rawEvents into per-turn buckets at each turn_start marker. Events that
 * arrive before the first turn_start (e.g. loop_start) are absorbed into the
 * first turn's bucket rather than forming a duplicate turn-0 bucket.
 */
function groupByTurn(events: LoopEvent[]): TurnBucket[] {
  const buckets: TurnBucket[] = [];
  let current: MutableBucket | null = null;
  for (const ev of events) {
    if (ev.type === "turn_start") {
      if (current === null) {
        current = { turnNum: ev.data.turn_num, events: [ev], hasTurnMarker: true };
      } else if (!current.hasTurnMarker) {
        // Preamble bucket (only had pre-turn events so far) absorbs the marker.
        current.turnNum = ev.data.turn_num;
        current.events.push(ev);
        current.hasTurnMarker = true;
      } else {
        buckets.push(current);
        current = { turnNum: ev.data.turn_num, events: [ev], hasTurnMarker: true };
      }
    } else if (current === null) {
      current = { turnNum: 0, events: [ev], hasTurnMarker: false };
    } else {
      current.events.push(ev);
    }
  }
  if (current !== null && current.events.length > 0) buckets.push(current);
  return buckets;
}

/** Pick the left-border accent class for an event by severity. */
function borderClass(ev: LoopEvent): string {
  if (ev.type === "tool_call_result" && ev.data.is_error) return "border-l-4 border-red-500";
  if (ev.type === "verification_failed") return "border-l-4 border-red-500";
  if (ev.type === "guardrail_triggered") return "border-l-4 border-red-500";
  if (ev.type === "approval_requested") return "border-l-4 border-amber-500";
  return "border-l-4 border-muted";
}

/** One-line summary of an event's key fields for the tree row. */
function eventSummary(ev: LoopEvent): string {
  switch (ev.type) {
    case "loop_start":
      return `session=${ev.data.session_id ?? "(pending)"}`;
    case "turn_start":
      return `turn ${ev.data.turn_num}`;
    case "llm_request":
      return `model=${ev.data.model} tokens_in=${ev.data.tokens_in}`;
    case "llm_response": {
      const tc = ev.data.tool_calls.length;
      return `${tc} tool call${tc === 1 ? "" : "s"}${ev.data.thinking ? " · has thinking" : ""}`;
    }
    case "tool_call_request":
      return `${ev.data.tool_name}`;
    case "tool_call_result":
      return `${ev.data.tool_name} (${ev.data.duration_ms.toFixed(0)} ms)${ev.data.is_error ? " · ERROR" : ""}`;
    case "loop_end":
      return `stop=${ev.data.stop_reason} turns=${ev.data.total_turns}`;
    case "approval_requested":
      return `risk=${ev.data.risk_level}`;
    case "approval_received":
      return `decision=${ev.data.decision}`;
    case "guardrail_triggered":
      return `${ev.data.guardrail_type} → ${ev.data.action}`;
    case "verification_passed":
      return `${ev.data.verifier} (${ev.data.verifier_type})${ev.data.score !== null ? ` score=${ev.data.score.toFixed(2)}` : ""}`;
    case "verification_failed":
      return `${ev.data.verifier} (${ev.data.verifier_type}) · ${ev.data.reason ?? "no reason"}`;
    default: {
      // Defensive — unknown future serialized type (e.g. subagent_* added in US-6
      // is also typed; this branch only hits if a wholly-unmapped type slips in).
      return JSON.stringify((ev as { data?: unknown }).data ?? {});
    }
  }
}

export function LoopVisualizer({ mode }: LoopVisualizerProps): JSX.Element | null {
  const rawEvents = useChatStore((s) => s.rawEvents);
  const totalTurns = useChatStore((s) => s.totalTurns);

  if (rawEvents.length === 0) {
    if (mode === "inline") return null;
    return (
      <div className="rounded-md border border-border bg-muted/20 p-6 text-sm text-muted-foreground">
        No loop events yet. Start a chat-v2 session to populate the visualizer.
      </div>
    );
  }

  const buckets = groupByTurn(rawEvents);
  // Inline mode: only expand the last 5 turns; collapse the rest into a count.
  const collapsedCount = mode === "inline" && buckets.length > 5 ? buckets.length - 5 : 0;
  const visibleBuckets = collapsedCount > 0 ? buckets.slice(collapsedCount) : buckets;

  return (
    <div
      className={
        mode === "inline"
          ? "max-h-[400px] overflow-y-auto border-t border-border bg-muted/30 p-3"
          : "rounded-md border border-border bg-background p-4"
      }
      data-testid={`loop-visualizer-${mode}`}
      aria-label="Loop visualizer"
    >
      {mode === "standalone" && (
        <div
          className="mb-3 flex items-center gap-4 text-sm text-muted-foreground"
          data-testid="loop-visualizer-summary"
        >
          <span>
            Turns: <strong className="text-foreground">{totalTurns || buckets.length}</strong>
          </span>
          <span>
            Events: <strong className="text-foreground">{rawEvents.length}</strong>
          </span>
        </div>
      )}
      {mode === "inline" && (
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Loop ({buckets.length} turn{buckets.length === 1 ? "" : "s"})
        </h3>
      )}
      {collapsedCount > 0 && (
        <p className="mb-2 text-xs text-muted-foreground">
          {collapsedCount} earlier turn{collapsedCount === 1 ? "" : "s"} collapsed
        </p>
      )}
      <ul className="space-y-3">
        {visibleBuckets.map((bucket, bi) => (
          <li key={`turn-${bucket.turnNum}-${bi}`} data-testid={`loop-turn-${bucket.turnNum}`}>
            <div className="mb-1 text-xs font-semibold text-foreground">Turn {bucket.turnNum}</div>
            <ul className="space-y-1 pl-3">
              {bucket.events.map((ev, ei) => (
                <li
                  key={`ev-${bi}-${ei}`}
                  className={`rounded bg-background px-2 py-1 text-xs ${borderClass(ev)}`}
                  data-testid={`loop-event-${ev.type}`}
                >
                  <span className="font-mono text-[11px] text-muted-foreground">{ev.type}</span>{" "}
                  <span className="text-foreground">{eventSummary(ev)}</span>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </div>
  );
}
