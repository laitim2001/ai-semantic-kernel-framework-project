/**
 * useSSEChat — SSE streaming hook for orchestrator pipeline.
 *
 * Uses fetch() + ReadableStream to receive Server-Sent Events from
 * POST /orchestrator/chat/stream. Parses SSE format and dispatches
 * events to callbacks for real-time UI updates.
 *
 * Sprint 145 — Phase 42 SSE Streaming.
 */

import { useCallback, useRef, useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import { getGuestHeaders } from '@/utils/guestUser';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

/** SSE event types from the pipeline */
export type PipelineSSEEventType =
  | 'PIPELINE_START'
  | 'ROUTING_COMPLETE'
  | 'AGENT_THINKING'
  | 'TOOL_CALL_START'
  | 'TOOL_CALL_END'
  | 'TEXT_DELTA'
  | 'TASK_DISPATCHED'
  | 'SWARM_WORKER_START'
  | 'SWARM_PROGRESS'
  | 'APPROVAL_REQUIRED'
  | 'PIPELINE_COMPLETE'
  | 'PIPELINE_ERROR';

/** Parsed SSE event */
export interface PipelineSSEEvent {
  type: PipelineSSEEventType;
  data: Record<string, unknown>;
}

/** Event handlers for each SSE event type */
export interface SSEEventHandlers {
  onPipelineStart?: (data: Record<string, unknown>) => void;
  onRoutingComplete?: (data: Record<string, unknown>) => void;
  onAgentThinking?: (data: Record<string, unknown>) => void;
  onToolCallStart?: (data: Record<string, unknown>) => void;
  onToolCallEnd?: (data: Record<string, unknown>) => void;
  onTextDelta?: (delta: string) => void;
  onTaskDispatched?: (data: Record<string, unknown>) => void;
  onSwarmWorkerStart?: (data: Record<string, unknown>) => void;
  onSwarmProgress?: (data: Record<string, unknown>) => void;
  onApprovalRequired?: (data: Record<string, unknown>) => void;
  onPipelineComplete?: (data: Record<string, unknown>) => void;
  onPipelineError?: (error: string) => void;
}

/** Request payload for SSE streaming */
export interface SSEChatRequest {
  content: string;
  mode?: 'chat' | 'workflow' | 'swarm';
  source?: string;
  user_id?: string;
  session_id?: string;
  metadata?: Record<string, unknown>;
}

export function useSSEChat() {
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const sendSSE = useCallback(
    async (request: SSEChatRequest, handlers: SSEEventHandlers) => {
      // Abort any existing stream
      if (abortRef.current) {
        abortRef.current.abort();
      }

      const controller = new AbortController();
      abortRef.current = controller;
      setIsStreaming(true);

      try {
        const token = useAuthStore.getState().token;
        const guestHeaders = getGuestHeaders();

        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
          ...guestHeaders,
        };
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_BASE_URL}/orchestrator/chat/stream`, {
          method: 'POST',
          headers,
          body: JSON.stringify(request),
          signal: controller.signal,
        });

        if (!response.ok) {
          const errorText = await response.text();
          handlers.onPipelineError?.(errorText || `HTTP ${response.status}`);
          return;
        }

        const reader = response.body?.getReader();
        if (!reader) {
          handlers.onPipelineError?.('No response body');
          return;
        }

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE events from buffer
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line

          let currentEventType = '';
          let currentData = '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              currentData = line.slice(6);
            } else if (line === '' && currentEventType && currentData) {
              // Empty line = end of event
              try {
                const data = JSON.parse(currentData);
                dispatchEvent(currentEventType as PipelineSSEEventType, data, handlers);
              } catch {
                // Skip malformed events
              }
              currentEventType = '';
              currentData = '';
            }
          }
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          return; // User cancelled
        }
        handlers.onPipelineError?.(err instanceof Error ? err.message : String(err));
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    []
  );

  const cancelStream = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  return { sendSSE, isStreaming, cancelStream };
}

function dispatchEvent(
  type: PipelineSSEEventType,
  data: Record<string, unknown>,
  handlers: SSEEventHandlers
) {
  switch (type) {
    case 'PIPELINE_START':
      handlers.onPipelineStart?.(data);
      break;
    case 'ROUTING_COMPLETE':
      handlers.onRoutingComplete?.(data);
      break;
    case 'AGENT_THINKING':
      handlers.onAgentThinking?.(data);
      break;
    case 'TOOL_CALL_START':
      handlers.onToolCallStart?.(data);
      break;
    case 'TOOL_CALL_END':
      handlers.onToolCallEnd?.(data);
      break;
    case 'TEXT_DELTA':
      handlers.onTextDelta?.(data.delta as string || '');
      break;
    case 'TASK_DISPATCHED':
      handlers.onTaskDispatched?.(data);
      break;
    case 'SWARM_WORKER_START':
      handlers.onSwarmWorkerStart?.(data);
      break;
    case 'SWARM_PROGRESS':
      handlers.onSwarmProgress?.(data);
      break;
    case 'APPROVAL_REQUIRED':
      handlers.onApprovalRequired?.(data);
      break;
    case 'PIPELINE_COMPLETE':
      handlers.onPipelineComplete?.(data);
      break;
    case 'PIPELINE_ERROR':
      handlers.onPipelineError?.(data.error as string || 'Unknown error');
      break;
  }
}
