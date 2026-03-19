/**
 * useOrchestratorChat - Orchestrator Chat Hook
 *
 * Sprint 138: Phase 40 - Orchestrator Chat Enhancement
 *
 * Manages orchestrator chat state including:
 * - Message send/receive via /orchestrator/chat
 * - SSE streaming responses with auto-reconnect
 * - Intent/risk/execution mode metadata
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import {
  orchestratorApi,
  type OrchestratorMessage,
  type OrchestratorMessageMetadata,
  type OrchestratorSSEEventType,
} from '@/api/endpoints/orchestrator';

// =============================================================================
// Types
// =============================================================================

export interface UseOrchestratorChatOptions {
  /** Initial session ID (optional, will be created if not provided) */
  sessionId?: string;
  /** Enable SSE streaming (default: true) */
  enableStreaming?: boolean;
  /** Auto-reconnect delay in ms (default: 3000) */
  reconnectDelay?: number;
  /** Max reconnect attempts (default: 5) */
  maxReconnectAttempts?: number;
}

export interface UseOrchestratorChatReturn {
  /** Current messages */
  messages: OrchestratorMessage[];
  /** Send a message */
  sendMessage: (content: string) => Promise<void>;
  /** Whether a message is being processed */
  isLoading: boolean;
  /** Current error */
  error: string | null;
  /** Whether SSE connection is active */
  isConnected: boolean;
  /** Current session ID */
  sessionId: string | null;
  /** Latest intent/risk metadata */
  latestMetadata: OrchestratorMessageMetadata | null;
  /** Clear all messages */
  clearMessages: () => void;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useOrchestratorChat(
  options: UseOrchestratorChatOptions = {}
): UseOrchestratorChatReturn {
  const {
    sessionId: initialSessionId,
    enableStreaming = true,
    reconnectDelay = 3000,
    maxReconnectAttempts = 5,
  } = options;

  const [messages, setMessages] = useState<OrchestratorMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(
    initialSessionId ?? null
  );
  const [latestMetadata, setLatestMetadata] =
    useState<OrchestratorMessageMetadata | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const streamingMessageRef = useRef<string>('');

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
    };
  }, []);

  // Update session ID when prop changes
  useEffect(() => {
    if (initialSessionId) {
      setSessionId(initialSessionId);
    }
  }, [initialSessionId]);

  /**
   * Handle SSE streaming response
   */
  const handleStreamMessage = useCallback(
    (message: string, currentSessionId: string) => {
      const eventSource = orchestratorApi.createStream(
        currentSessionId,
        message
      );
      eventSourceRef.current = eventSource;
      streamingMessageRef.current = '';

      eventSource.onopen = () => {
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const eventType = data.type as OrchestratorSSEEventType;

          switch (eventType) {
            case 'text_delta': {
              streamingMessageRef.current += data.data?.text || '';
              // Update the last assistant message with streaming content
              setMessages((prev) => {
                const updated = [...prev];
                const lastIdx = updated.length - 1;
                if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
                  updated[lastIdx] = {
                    ...updated[lastIdx],
                    content: streamingMessageRef.current,
                  };
                }
                return updated;
              });
              break;
            }
            case 'message_start': {
              // Add placeholder assistant message for streaming
              const assistantMsg: OrchestratorMessage = {
                role: 'assistant',
                content: '',
                timestamp: new Date().toISOString(),
              };
              setMessages((prev) => [...prev, assistantMsg]);
              break;
            }
            case 'intent_result': {
              const metadata: OrchestratorMessageMetadata = {
                intent: data.data?.intent,
                risk_level: data.data?.risk_level,
                execution_mode: data.data?.execution_mode,
              };
              setLatestMetadata(metadata);
              // Attach metadata to the current assistant message
              setMessages((prev) => {
                const updated = [...prev];
                const lastIdx = updated.length - 1;
                if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
                  updated[lastIdx] = {
                    ...updated[lastIdx],
                    metadata: { ...updated[lastIdx].metadata, ...metadata },
                  };
                }
                return updated;
              });
              break;
            }
            case 'risk_result': {
              setLatestMetadata((prev) => ({
                ...prev,
                risk_level: data.data?.risk_level,
              }));
              break;
            }
            case 'thinking_delta': {
              setLatestMetadata((prev) => ({
                ...prev,
                thinking_tokens:
                  (prev?.thinking_tokens || '') + (data.data?.text || ''),
              }));
              break;
            }
            case 'tool_call_start':
            case 'tool_call_end': {
              // Tool call events are informational
              break;
            }
            case 'message_end': {
              setIsLoading(false);
              eventSource.close();
              eventSourceRef.current = null;
              setIsConnected(false);
              break;
            }
            case 'error': {
              setError(data.data?.message || 'Stream error');
              setIsLoading(false);
              eventSource.close();
              eventSourceRef.current = null;
              setIsConnected(false);
              break;
            }
          }
        } catch {
          // Ignore malformed events
        }
      };

      eventSource.onerror = () => {
        setIsConnected(false);
        eventSource.close();
        eventSourceRef.current = null;

        // Auto-reconnect if still loading
        if (
          reconnectAttemptsRef.current < maxReconnectAttempts &&
          isLoading
        ) {
          reconnectAttemptsRef.current += 1;
          reconnectTimerRef.current = setTimeout(() => {
            handleStreamMessage(message, currentSessionId);
          }, reconnectDelay);
        } else {
          setIsLoading(false);
          setError('Connection lost');
        }
      };
    },
    [reconnectDelay, maxReconnectAttempts, isLoading]
  );

  /**
   * Send a message via orchestrator
   */
  const sendMessage = useCallback(
    async (content: string) => {
      setError(null);
      setIsLoading(true);

      // Add user message immediately
      const userMessage: OrchestratorMessage = {
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      try {
        if (enableStreaming && sessionId) {
          // Use SSE streaming
          handleStreamMessage(content, sessionId);
        } else {
          // Use regular POST
          const response = await orchestratorApi.sendMessage({
            message: content,
            session_id: sessionId ?? undefined,
          });

          // Update session ID if newly created
          if (response.session_id && !sessionId) {
            setSessionId(response.session_id);
          }

          // Update metadata
          if (response.intent || response.risk_level) {
            const metadata: OrchestratorMessageMetadata = {
              intent: response.intent,
              risk_level: response.risk_level,
              execution_mode: response.execution_mode,
              session_id: response.session_id,
            };
            setLatestMetadata(metadata);
          }

          // Add assistant response
          setMessages((prev) => [
            ...prev,
            {
              ...response.message,
              metadata: {
                intent: response.intent,
                risk_level: response.risk_level,
                execution_mode: response.execution_mode,
              },
            },
          ]);

          setIsLoading(false);
        }
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to send message';
        setError(errorMessage);
        setIsLoading(false);
      }
    },
    [sessionId, enableStreaming, handleStreamMessage]
  );

  /**
   * Clear all messages
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
    setLatestMetadata(null);
    setError(null);
  }, []);

  return {
    messages,
    sendMessage,
    isLoading,
    error,
    isConnected,
    sessionId,
    latestMetadata,
    clearMessages,
  };
}
