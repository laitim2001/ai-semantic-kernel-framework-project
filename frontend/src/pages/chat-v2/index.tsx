/**
 * V2 main chat page — wires ChatLayout + MessageList + InputBar.
 *
 * Modification History (newest-first):
 *   - 2026-04-30: Wire MessageList + InputBar (Sprint 50.2 Day 4.4) —
 *     end-to-end conversation panel ready for echo_demo + real_llm modes.
 *   - 2026-04-30: Replace 49.1 placeholder with ChatLayout shell (Sprint 50.2 Day 3.7)
 */

import ChatLayout from "@/features/chat_v2/components/ChatLayout";
import InputBar from "@/features/chat_v2/components/InputBar";
import MessageList from "@/features/chat_v2/components/MessageList";

export default function ChatV2Page(): JSX.Element {
  return (
    <ChatLayout>
      <MessageList />
      <InputBar />
    </ChatLayout>
  );
}
