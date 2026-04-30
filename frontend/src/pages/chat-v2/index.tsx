/**
 * V2 main chat page — Sprint 50.2 Day 3 wires the ChatLayout shell.
 * Day 4 fills MessageList + InputBar inside.
 *
 * Modification History:
 *   - 2026-04-30: Replace 49.1 placeholder with ChatLayout shell (Sprint 50.2 Day 3.7)
 */

import ChatLayout from "@/features/chat_v2/components/ChatLayout";

export default function ChatV2Page(): JSX.Element {
  return (
    <ChatLayout>
      <div
        style={{
          padding: "2rem",
          display: "flex",
          flexDirection: "column",
          gap: "1rem",
          color: "#3b4252",
        }}
      >
        <h2 style={{ margin: 0 }}>Conversation panel</h2>
        <p style={{ color: "#7c8696", fontSize: 14 }}>
          Sprint 50.2 Day 3 skeleton — MessageList + InputBar arrive in Day 4
          and will display the LoopEvent stream from <code>POST /api/v1/chat/</code>.
        </p>
      </div>
    </ChatLayout>
  );
}
