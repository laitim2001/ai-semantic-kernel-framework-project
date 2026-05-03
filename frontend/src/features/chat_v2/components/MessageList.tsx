/**
 * File: frontend/src/features/chat_v2/components/MessageList.tsx
 * Purpose: Renders the rolling conversation — user / assistant / tool cards.
 * Category: Frontend / chat_v2 / components
 * Scope: Phase 50 / Sprint 50.2 (Day 4.1)
 *
 * Description:
 *   Subscribes to chatStore.messages and renders one row per message. Each
 *   assistant message embeds 0..N ToolCallCards inline. Auto-scrolls to the
 *   bottom whenever message count grows.
 *
 *   Status pill is rendered above the input area (in InputBar) — this
 *   component focuses on the message list only.
 *
 * Created: 2026-04-30 (Sprint 50.2 Day 4.1)
 * Last Modified: 2026-04-30
 *
 * Modification History:
 *   - 2026-04-30: Initial creation (Sprint 50.2 Day 4.1)
 *
 * Related:
 *   - ../store/chatStore.ts (subscribes to messages)
 *   - ToolCallCard.tsx (per-tool-call panel)
 */

import { useEffect, useRef, type CSSProperties } from "react";
import { useChatStore } from "../store/chatStore";
import type { Message } from "../types";
import { ApprovalCard } from "./ApprovalCard";
import ToolCallCard from "./ToolCallCard";

const styles: Record<string, CSSProperties> = {
  list: {
    flex: 1,
    overflowY: "auto",
    padding: "1.5rem",
    display: "flex",
    flexDirection: "column",
    gap: "1rem",
  },
  row: {
    maxWidth: "min(720px, 90%)",
  },
  rowUser: {
    alignSelf: "flex-end",
  },
  rowAssistant: {
    alignSelf: "flex-start",
    width: "min(720px, 90%)",
  },
  bubbleUser: {
    background: "#5a78c8",
    color: "#fff",
    padding: "0.6rem 0.9rem",
    borderRadius: 12,
    borderBottomRightRadius: 4,
    fontSize: 14,
    lineHeight: 1.5,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
  bubbleAssistant: {
    background: "#fff",
    border: "1px solid #d8dde7",
    color: "#2c2c33",
    padding: "0.6rem 0.9rem",
    borderRadius: 12,
    borderBottomLeftRadius: 4,
    fontSize: 14,
    lineHeight: 1.5,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
  thinking: {
    color: "#7c8696",
    fontSize: 12,
    fontStyle: "italic",
    marginBottom: "0.4rem",
  },
  toolCalls: {
    marginTop: "0.6rem",
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
  },
  empty: {
    color: "#9aa3b3",
    fontSize: 13,
    textAlign: "center",
    padding: "2rem",
  },
};

function MessageRow({ msg }: { msg: Message }): JSX.Element {
  if (msg.kind === "user") {
    return (
      <div style={{ ...styles.row, ...styles.rowUser }}>
        <div style={styles.bubbleUser}>{msg.content}</div>
      </div>
    );
  }
  // assistant
  return (
    <div style={{ ...styles.row, ...styles.rowAssistant }}>
      <div style={styles.bubbleAssistant}>
        {msg.thinking !== null && msg.thinking !== "" && (
          <div style={styles.thinking}>thinking: {msg.thinking}</div>
        )}
        {msg.content && <div>{msg.content}</div>}
        {msg.toolCalls.length > 0 && (
          <div style={styles.toolCalls}>
            {msg.toolCalls.map((tc) => (
              <ToolCallCard key={tc.toolCallId} entry={tc} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function MessageList(): JSX.Element {
  const messages = useChatStore((s) => s.messages);
  const approvals = useChatStore((s) => s.approvals);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Sort approvals by receivedAt (chronological with messages).
  const approvalEntries = Object.values(approvals).sort(
    (a, b) => a.receivedAt - b.receivedAt,
  );

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages.length, approvalEntries.length]);

  return (
    <div style={styles.list} ref={scrollRef}>
      {messages.length === 0 && approvalEntries.length === 0 ? (
        <div style={styles.empty}>
          Type a message below to start. Try <code>echo hello</code> in echo_demo
          mode.
        </div>
      ) : (
        <>
          {messages.map((m) => (
            <MessageRow key={m.id} msg={m} />
          ))}
          {approvalEntries.map((a) => (
            <ApprovalCard key={a.approvalRequestId} approvalRequestId={a.approvalRequestId} />
          ))}
        </>
      )}
    </div>
  );
}
