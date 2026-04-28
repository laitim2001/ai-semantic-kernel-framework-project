/**
 * AG-UI API Endpoints
 *
 * Sprint 64: Approval Flow & Risk Indicators
 * S64-4: Approval API Integration
 * Sprint 65: Checkpoint Integration
 * Phase 16: Unified Agentic Chat Interface
 *
 * API client functions for AG-UI operations including
 * approval endpoints for HITL (Human-in-the-Loop) workflow
 * and checkpoint management.
 */

import { api, ApiError } from '../client';
import type { PendingApproval, RunAgentInput, AGUIRunState } from '@/types/ag-ui';
import type { Checkpoint } from '@/types/unified-chat';

// =============================================================================
// Types
// =============================================================================

/** Approval response from server */
export interface ApprovalResponse {
  success: boolean;
  toolCallId: string;
  action: 'approved' | 'rejected';
  timestamp: string;
  message?: string;
}

/** Reject request body */
export interface RejectRequest {
  reason?: string;
}

/** Thread info response */
export interface ThreadInfo {
  threadId: string;
  sessionId: string;
  status: 'active' | 'idle' | 'closed';
  messageCount: number;
  createdAt: string;
  lastActivityAt: string;
}

/** Create thread request */
export interface CreateThreadRequest {
  sessionId?: string;
  metadata?: Record<string, unknown>;
}

/** Create thread response */
export interface CreateThreadResponse {
  threadId: string;
  sessionId: string;
}

/** Restore checkpoint response (Sprint 65) */
export interface RestoreCheckpointResponse {
  success: boolean;
  checkpointId: string;
  restoredState?: Record<string, unknown>;
  message?: string;
}

// =============================================================================
// AG-UI API Client
// =============================================================================

/**
 * AG-UI API endpoints
 */
export const aguiApi = {
  // ===========================================================================
  // Approval Endpoints (HITL)
  // ===========================================================================

  /**
   * Approve a tool call
   *
   * @param toolCallId - The ID of the tool call to approve
   * @returns Approval response
   *
   * @example
   * ```typescript
   * const result = await aguiApi.approve('tool-call-123');
   * console.log(result.success); // true
   * ```
   */
  approve: async (toolCallId: string): Promise<ApprovalResponse> => {
    try {
      const response = await api.post<ApprovalResponse>(
        `/ag-ui/tool-calls/${toolCallId}/approve`
      );
      return response;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to approve tool call', 500, error);
    }
  },

  /**
   * Reject a tool call
   *
   * @param toolCallId - The ID of the tool call to reject
   * @param reason - Optional reason for rejection
   * @returns Approval response
   *
   * @example
   * ```typescript
   * const result = await aguiApi.reject('tool-call-123', 'Security concern');
   * console.log(result.success); // true
   * ```
   */
  reject: async (toolCallId: string, reason?: string): Promise<ApprovalResponse> => {
    try {
      const body: RejectRequest = reason ? { reason } : {};
      const response = await api.post<ApprovalResponse>(
        `/ag-ui/tool-calls/${toolCallId}/reject`,
        body
      );
      return response;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to reject tool call', 500, error);
    }
  },

  /**
   * Get pending approvals for a session
   *
   * @param sessionId - Session ID to get pending approvals for
   * @returns List of pending approvals
   */
  getPendingApprovals: async (sessionId: string): Promise<PendingApproval[]> => {
    try {
      const response = await api.get<{ approvals: PendingApproval[] }>(
        `/ag-ui/sessions/${sessionId}/pending-approvals`
      );
      return response.approvals;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to get pending approvals', 500, error);
    }
  },

  // ===========================================================================
  // Thread Endpoints
  // ===========================================================================

  /**
   * Create a new thread
   *
   * @param request - Thread creation request
   * @returns Created thread info
   */
  createThread: async (request: CreateThreadRequest = {}): Promise<CreateThreadResponse> => {
    try {
      const response = await api.post<CreateThreadResponse>('/ag-ui/threads', request);
      return response;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to create thread', 500, error);
    }
  },

  /**
   * Get thread information
   *
   * @param threadId - Thread ID
   * @returns Thread info
   */
  getThread: async (threadId: string): Promise<ThreadInfo> => {
    try {
      const response = await api.get<ThreadInfo>(`/ag-ui/threads/${threadId}`);
      return response;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to get thread', 500, error);
    }
  },

  /**
   * Delete/close a thread
   *
   * @param threadId - Thread ID to close
   */
  closeThread: async (threadId: string): Promise<void> => {
    try {
      await api.delete(`/ag-ui/threads/${threadId}`);
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to close thread', 500, error);
    }
  },

  // ===========================================================================
  // Run Endpoints
  // ===========================================================================

  /**
   * Get SSE endpoint URL for agent run
   *
   * @param input - Run agent input configuration
   * @returns SSE endpoint URL
   */
  getRunEndpoint: (input: RunAgentInput): string => {
    const baseUrl = import.meta.env.VITE_API_URL || '/api/v1';
    const params = new URLSearchParams();
    params.set('thread_id', input.threadId);
    if (input.runId) params.set('run_id', input.runId);
    if (input.sessionId) params.set('session_id', input.sessionId);
    if (input.mode) params.set('mode', input.mode);
    return `${baseUrl}/ag-ui?${params.toString()}`;
  },

  /**
   * Cancel a running agent execution
   *
   * @param runId - Run ID to cancel
   */
  cancelRun: async (runId: string): Promise<void> => {
    try {
      await api.post(`/ag-ui/runs/${runId}/cancel`);
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to cancel run', 500, error);
    }
  },

  /**
   * Get run status
   *
   * @param runId - Run ID
   * @returns Run state
   */
  getRunStatus: async (runId: string): Promise<AGUIRunState> => {
    try {
      const response = await api.get<AGUIRunState>(`/ag-ui/runs/${runId}`);
      return response;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to get run status', 500, error);
    }
  },

  // ===========================================================================
  // Checkpoint Endpoints (Sprint 65)
  // ===========================================================================

  /**
   * Get checkpoints for a session
   *
   * @param sessionId - Session ID to get checkpoints for
   * @returns List of checkpoints
   */
  getCheckpoints: async (sessionId: string): Promise<Checkpoint[]> => {
    try {
      const response = await api.get<{ checkpoints: Checkpoint[] }>(
        `/ag-ui/sessions/${sessionId}/checkpoints`
      );
      return response.checkpoints;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to get checkpoints', 500, error);
    }
  },

  /**
   * Restore a checkpoint
   *
   * @param checkpointId - Checkpoint ID to restore
   * @returns Restore result with restored state
   *
   * @example
   * ```typescript
   * const result = await aguiApi.restoreCheckpoint('cp-123');
   * if (result.success) {
   *   console.log('Restored to:', result.restoredState);
   * }
   * ```
   */
  restoreCheckpoint: async (checkpointId: string): Promise<RestoreCheckpointResponse> => {
    try {
      const response = await api.post<RestoreCheckpointResponse>(
        `/ag-ui/checkpoints/${checkpointId}/restore`
      );
      return response;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to restore checkpoint', 500, error);
    }
  },

  /**
   * Delete a checkpoint
   *
   * @param checkpointId - Checkpoint ID to delete
   */
  deleteCheckpoint: async (checkpointId: string): Promise<void> => {
    try {
      await api.delete(`/ag-ui/checkpoints/${checkpointId}`);
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to delete checkpoint', 500, error);
    }
  },
};

export default aguiApi;
