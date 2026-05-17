/**
 * File: frontend/src/features/chat_v2/components/MessageList.tsx
 * Purpose: Renders the rolling conversation — user / agent turns + inline tool cards.
 * Category: Frontend / chat_v2 / components
 * Scope: Phase 50 / Sprint 50.2 (Day 4.1) + Phase 57.21 (Day 1 — Turn adapter)
 *
 * Description:
 *   Sprint 57.21 Day 1: temporary Turn-based stub preserving Sprint 57.x visual
 *   baseline. Reads `turns: Turn[]` (replaces old `messages: Message[]`); skips
 *   hitl turns (rendered via existing approvals dict path below; Day 2 unifies).
 *   ToolBlock → ToolCallCard adapter inline (Day 2 replaces with proper TurnList
 *   + components/blocks/ToolBlock.tsx).
 *
 * Created: 2026-04-30 (Sprint 50.2 Day 4.1)
 * Last Modified: 2026-05-17
 *
 * Modification History (newest-first):
 *   - 2026-05-17: Sprint 57.21 Day 1 — switch to turns[]; ToolBlock→ToolCallCard adapter
 *   - 2026-05-17: Sprint 57.20 Day 3 — token migration bg-card→bg-bg-1
 *   - 2026-05-11: Sprint 57.15 — inline styles → Tailwind utility classes
 *   - 2026-04-30: Initial creation (Sprint 50.2 Day 4.1)
 *
 * Related:
 *   - ../store/chatStore.ts (subscribes to turns)
 *   - ../types.ts (Turn + Block discriminated unions)
 *   - ToolCallCard.tsx (per-tool-call panel)
 *   - reference/design-mockups/page-chat.jsx (Day 2 TurnList visual target)
 */

import { useEffect, useRef } from "react";

import { useChatStore } from "../store/chatStore";
import type { AgentTurn, ThinkingBlock, ToolBlock, ToolCallEntry, Turn } from "../types";
import { ApprovalCard } from "./ApprovalCard";
import ToolCallCard from "./ToolCallCard";

const BUBBLE_BASE =
  "whitespace-pre-wrap break-words rounded-xl px-3.5 py-2.5 text-sm leading-normal";

/** Convert a Sprint 57.21 ToolBlock into the legacy ToolCallEntry shape Day 1 expects. */
function toolBlockToEntry(b: ToolBlock): ToolCallEntry {
  return {
    toolCallId: b.toolCallId,
    toolName: b.name,
    args: {},
    result: b.output ?? undefined,
    isError: b.isError,
    durationMs: b.durationMs ?? undefined,
  };
}

function TurnRow({ turn }: { turn: Turn }): JSX.Element | null {
  if (turn.role === "user") {
    return (
      <div className="max-w-[min(720px,90%)] self-end">
        <div className={`${BUBBLE_BASE} rounded-br bg-primary text-white`}>{turn.text}</div>
      </div>
    );
  }
  if (turn.role === "hitl") {
    // Day 1 stub: skip — existing approvals dict path renders ApprovalCard.
    // Day 2 TurnList unifies HITLTurn rendering inline.
    return null;
  }
  const agent = turn as AgentTurn;
  const thinkingBlock = agent.blocks.find((b) => b.type === "thinking") as
    | ThinkingBlock
    | undefined;
  const toolBlocks = agent.blocks.filter((b): b is ToolBlock => b.type === "tool");
  return (
    <div className="max-w-[min(720px,90%)] w-[min(720px,90%)] self-start">
      <div className={`${BUBBLE_BASE} rounded-bl border border-border bg-bg-1 text-foreground`}>
        {thinkingBlock && (
          <div className="mb-1.5 text-xs italic text-fg-muted">
            thinking: {thinkingBlock.text}
          </div>
        )}
        {toolBlocks.length > 0 && (
          <div className="mt-2.5 flex flex-col gap-2">
            {toolBlocks.map((b) => (
              <ToolCallCard key={b.toolCallId} entry={toolBlockToEntry(b)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function MessageList(): JSX.Element {
  const turns = useChatStore((s) => s.turns);
  const approvals = useChatStore((s) => s.approvals);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Sort approvals by receivedAt (chronological with turns).
  const approvalEntries = Object.values(approvals).sort(
    (a, b) => a.receivedAt - b.receivedAt,
  );

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [turns.length, approvalEntries.length]);

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-6" ref={scrollRef}>
      {turns.length === 0 && approvalEntries.length === 0 ? (
        <div className="p-8 text-center text-sm text-fg-muted">
          Type a message below to start. Try <code>echo hello</code> in echo_demo
          mode.
        </div>
      ) : (
        <>
          {turns.map((t) => (
            <TurnRow key={t.id} turn={t} />
          ))}
          {approvalEntries.map((a) => (
            <ApprovalCard key={a.approvalRequestId} approvalRequestId={a.approvalRequestId} />
          ))}
        </>
      )}
    </div>
  );
}
