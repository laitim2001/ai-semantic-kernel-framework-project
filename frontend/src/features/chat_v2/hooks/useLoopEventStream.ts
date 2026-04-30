/**
 * File: frontend/src/features/chat_v2/hooks/useLoopEventStream.ts
 * Purpose: React hook wrapping streamChat + Zustand store integration.
 * Category: Frontend / chat_v2 / hooks
 * Scope: Phase 50 / Sprint 50.2 (Day 3.5)
 *
 * Description:
 *   Provides a `send(message)` function that:
 *     1. Pushes the user message into the store
 *     2. Calls streamChat() with onEvent → store.mergeEvent
 *     3. Routes errors to store.setError + status="error"
 *     4. Owns an AbortController for cancellation via `cancel()`
 *
 *   Reuses the same Zustand chatStore — components subscribe directly to
 *   store fields rather than receiving them through hook return value.
 *
 * Created: 2026-04-30 (Sprint 50.2 Day 3.5)
 * Last Modified: 2026-04-30
 *
 * Modification History:
 *   - 2026-04-30: Initial creation (Sprint 50.2 Day 3.5)
 *
 * Related:
 *   - ../services/chatService.ts (streamChat)
 *   - ../store/chatStore.ts (mergeEvent + status)
 */

import { useCallback, useRef } from "react";
import { streamChat } from "../services/chatService";
import { useChatStore } from "../store/chatStore";

export type UseLoopEventStream = {
  send: (message: string) => Promise<void>;
  cancel: () => void;
  isRunning: boolean;
};

export function useLoopEventStream(): UseLoopEventStream {
  const status = useChatStore((s) => s.status);
  const mode = useChatStore((s) => s.mode);
  const sessionId = useChatStore((s) => s.sessionId);
  const pushUserMessage = useChatStore((s) => s.pushUserMessage);
  const mergeEvent = useChatStore((s) => s.mergeEvent);
  const setStatus = useChatStore((s) => s.setStatus);
  const setError = useChatStore((s) => s.setError);

  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (message: string) => {
      if (status === "running") return;
      pushUserMessage(message);
      setStatus("running");
      setError(null);

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      await streamChat(
        {
          message,
          mode,
          ...(sessionId ? { session_id: sessionId } : {}),
        },
        {
          onEvent: mergeEvent,
          onError: (err) => {
            setError(err.message);
            setStatus("error");
          },
          signal: ctrl.signal,
        },
      );

      // If the loop did NOT emit loop_end (network drop / abort), state may
      // still be "running" — drop to "completed" so the UI re-enables input.
      const finalStatus = useChatStore.getState().status;
      if (finalStatus === "running") setStatus("completed");
    },
    [status, mode, sessionId, pushUserMessage, mergeEvent, setStatus, setError],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setStatus("cancelled");
  }, [setStatus]);

  return { send, cancel, isRunning: status === "running" };
}
