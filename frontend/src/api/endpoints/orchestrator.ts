/**
 * Orchestrator Chat API Endpoints
 *
 * Sprint 138: Phase 40 - Orchestrator Chat Enhancement
 *
 * API client for orchestrator chat endpoints:
 * - Send messages through orchestrator pipeline
 * - Health check
 * - SSE streaming support
 */

import { api, API_BASE_URL } from '../client';
import { useAuthStore } from '@/store/authStore';
import { getGuestHeaders } from '@/utils/guestUser';

// =============================================================================
// Types
// =============================================================================

/** Orchestrator chat message */
export interface OrchestratorMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: OrchestratorMessageMetadata;
}

/** Metadata attached to orchestrator messages */
export interface OrchestratorMessageMetadata {
  intent?: string;
  risk_level?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  execution_mode?: string;
  task_id?: string;
  session_id?: string;
  thinking_tokens?: string;
  tool_calls?: OrchestratorToolCall[];
}

/** Tool call info in message metadata */
export interface OrchestratorToolCall {
  tool_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: string;
}

/** Request to send a message via orchestrator */
export interface SendOrchestratorMessageRequest {
  message: string;
  session_id?: string;
  context?: Record<string, unknown>;
}

/** Response from orchestrator chat */
export interface SendOrchestratorMessageResponse {
  session_id: string;
  message: OrchestratorMessage;
  intent?: string;
  risk_level?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  execution_mode?: string;
  task_ids?: string[];
}

/** Orchestrator health status */
export interface OrchestratorHealthResponse {
  status: string;
  components: Record<string, string>;
  version?: string;
}

/** SSE event types from orchestrator stream */
export type OrchestratorSSEEventType =
  | 'message_start'
  | 'text_delta'
  | 'thinking_delta'
  | 'tool_call_start'
  | 'tool_call_end'
  | 'intent_result'
  | 'risk_result'
  | 'message_end'
  | 'error';

/** SSE event data structure */
export interface OrchestratorSSEEvent {
  type: OrchestratorSSEEventType;
  data: Record<string, unknown>;
}

// =============================================================================
// Orchestrator API Client
// =============================================================================

export const orchestratorApi = {
  /**
   * Send a message through the orchestrator pipeline
   */
  sendMessage: (
    request: SendOrchestratorMessageRequest
  ): Promise<SendOrchestratorMessageResponse> =>
    api.post<SendOrchestratorMessageResponse>('/orchestrator/chat', request),

  /**
   * Check orchestrator health
   */
  getHealth: (): Promise<OrchestratorHealthResponse> =>
    api.get<OrchestratorHealthResponse>('/orchestrator/health'),

  /**
   * Create an SSE EventSource for streaming orchestrator responses.
   * Returns the EventSource instance for the caller to manage.
   */
  createStream: (sessionId: string, message: string): EventSource => {
    const token = useAuthStore.getState().token;
    const guestHeaders = getGuestHeaders();
    const guestId = guestHeaders['X-Guest-Id'] || '';

    const params = new URLSearchParams({
      session_id: sessionId,
      message,
      ...(token ? { token } : {}),
      ...(guestId ? { guest_id: guestId } : {}),
    });

    return new EventSource(
      `${API_BASE_URL}/orchestrator/chat/stream?${params.toString()}`
    );
  },
};

export default orchestratorApi;
