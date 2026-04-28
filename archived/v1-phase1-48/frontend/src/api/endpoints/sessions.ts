/**
 * Session Management API Endpoints
 *
 * Sprint 138: Phase 40 - Session Management
 *
 * API client for session CRUD and recovery:
 * - List / get / delete sessions
 * - Get session messages
 * - Get recoverable sessions
 * - Resume interrupted sessions
 */

import { api } from '../client';

// =============================================================================
// Types
// =============================================================================

/** Session status */
export type SessionStatus =
  | 'active'
  | 'completed'
  | 'interrupted'
  | 'expired'
  | 'error';

/** Session summary for list views */
export interface SessionSummary {
  session_id: string;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message?: string;
  agent_type?: string;
  metadata?: Record<string, unknown>;
}

/** Detailed session info */
export interface SessionDetail {
  session_id: string;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
  message_count: number;
  agent_type?: string;
  execution_mode?: string;
  intent_category?: string;
  risk_level?: string;
  active_tasks?: string[];
  metadata?: Record<string, unknown>;
}

/** Session message */
export interface SessionMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

/** Session list response */
export interface SessionListResponse {
  sessions: SessionSummary[];
  total: number;
}

/** Session messages response */
export interface SessionMessagesResponse {
  messages: SessionMessage[];
  total: number;
}

/** Session resume response */
export interface SessionResumeResponse {
  session_id: string;
  status: string;
  restored_messages: number;
  active_tasks?: string[];
  message?: string;
}

/** Filters for session list */
export interface SessionFilters {
  status?: SessionStatus;
  limit?: number;
  offset?: number;
}

// =============================================================================
// Sessions API Client
// =============================================================================

export const sessionsApi = {
  /**
   * List sessions with optional filters
   */
  getSessions: (filters?: SessionFilters): Promise<SessionListResponse> => {
    const params = new URLSearchParams();
    if (filters?.status) params.set('status', filters.status);
    if (filters?.limit) params.set('limit', String(filters.limit));
    if (filters?.offset) params.set('offset', String(filters.offset));
    const query = params.toString();
    return api.get<SessionListResponse>(
      `/sessions${query ? `?${query}` : ''}`
    );
  },

  /**
   * Get a single session by ID
   */
  getSession: (id: string): Promise<SessionDetail> =>
    api.get<SessionDetail>(`/sessions/${id}`),

  /**
   * Get messages for a session
   */
  getSessionMessages: (id: string): Promise<SessionMessagesResponse> =>
    api.get<SessionMessagesResponse>(`/sessions/${id}/messages`),

  /**
   * Get recoverable (interrupted) sessions
   */
  getRecoverableSessions: (): Promise<SessionListResponse> =>
    api.get<SessionListResponse>('/sessions/recoverable'),

  /**
   * Resume an interrupted session
   */
  resumeSession: (id: string): Promise<SessionResumeResponse> =>
    api.post<SessionResumeResponse>(`/sessions/${id}/resume`),

  /**
   * Delete a session
   */
  deleteSession: (id: string): Promise<void> =>
    api.delete(`/sessions/${id}`),
};

export default sessionsApi;
