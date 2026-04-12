/**
 * useAgentDetail Hook
 *
 * Fetches and manages Agent detail data with optional polling.
 * Sprint 103: AgentDetailDrawer
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type { AgentDetail } from '../types';

// =============================================================================
// Types
// =============================================================================

export interface UseAgentDetailOptions {
  /** Team ID */
  teamId: string;
  /** Agent ID */
  agentId: string;
  /** Whether to fetch data */
  enabled?: boolean;
  /** Poll interval in milliseconds (only for running agents) */
  pollInterval?: number;
}

export interface UseAgentDetailResult {
  /** Agent detail data */
  agent: AgentDetail | null;
  /** Whether data is loading */
  isLoading: boolean;
  /** Error if any */
  error: Error | null;
  /** Manually refetch data */
  refetch: () => Promise<void>;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Convert snake_case API response to camelCase UI format
 */
function transformAgentDetail(data: Record<string, unknown>): AgentDetail {
  return {
    agentId: data.agent_id as string,
    agentName: data.agent_name as string,
    agentType: data.agent_type as AgentDetail['agentType'],
    role: data.role as string,
    status: data.status as AgentDetail['status'],
    progress: data.progress as number,
    currentAction: data.current_action as string | undefined,
    toolCallsCount: data.tool_calls_count as number || 0,
    createdAt: data.created_at as string,
    startedAt: data.started_at as string | undefined,
    completedAt: data.completed_at as string | undefined,
    taskId: data.task_id as string || '',
    taskDescription: data.task_description as string || '',
    thinkingHistory: Array.isArray(data.thinking_history)
      ? data.thinking_history.map((t: Record<string, unknown>) => ({
          content: t.content as string,
          timestamp: t.timestamp as string,
          tokenCount: t.token_count as number | undefined,
        }))
      : [],
    toolCalls: Array.isArray(data.tool_calls)
      ? data.tool_calls.map((tc: Record<string, unknown>) => ({
          toolCallId: tc.tool_call_id as string || tc.tool_id as string,
          toolName: tc.tool_name as string,
          status: tc.status as 'pending' | 'running' | 'completed' | 'failed',
          inputArgs: (tc.input_args || tc.input_params || {}) as Record<string, unknown>,
          outputResult: tc.output_result as Record<string, unknown> | undefined,
          error: tc.error as string | undefined,
          startedAt: tc.started_at as string | undefined,
          completedAt: tc.completed_at as string | undefined,
          durationMs: tc.duration_ms as number | undefined,
        }))
      : [],
    messages: Array.isArray(data.messages)
      ? data.messages.map((m: Record<string, unknown>) => ({
          role: m.role as 'system' | 'user' | 'assistant' | 'tool',
          content: m.content as string,
          timestamp: m.timestamp as string,
          toolCallId: m.tool_call_id as string | undefined,
        }))
      : [],
    result: data.result as Record<string, unknown> | undefined,
    error: data.error as string | undefined,
    checkpointId: data.checkpoint_id as string | undefined,
    checkpointBackend: data.checkpoint_backend as string | undefined,
  };
}

// =============================================================================
// Hook
// =============================================================================

/**
 * useAgentDetail - Fetch and manage Agent detail data
 *
 * @param options - Configuration options
 * @returns Agent detail state and methods
 *
 * @example
 * ```tsx
 * const { agent, isLoading, error, refetch } = useAgentDetail({
 *   teamId: 'team-123',
 *   agentId: 'agent-456',
 *   enabled: isOpen,
 *   pollInterval: agent?.status === 'running' ? 2000 : undefined,
 * });
 * ```
 */
export function useAgentDetail({
  teamId,
  agentId,
  enabled = true,
  pollInterval,
}: UseAgentDetailOptions): UseAgentDetailResult {
  const [agent, setAgent] = useState<AgentDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Track if component is mounted to avoid state updates after unmount
  const isMountedRef = useRef(true);

  // Fetch agent detail
  const fetchAgentDetail = useCallback(async () => {
    if (!enabled || !teamId || !agentId) {
      return;
    }

    // Only set loading on first fetch, not on poll updates
    if (!agent) {
      setIsLoading(true);
    }
    setError(null);

    try {
      const response = await fetch(
        `/api/v1/agent-team/${teamId}/agents/${agentId}?include_thinking=true&include_messages=true`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch agent detail: ${response.statusText}`);
      }

      const data = await response.json();

      if (isMountedRef.current) {
        const transformed = transformAgentDetail(data);
        setAgent(transformed);
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError(err instanceof Error ? err : new Error('Unknown error'));
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [teamId, agentId, enabled, agent]);

  // Initial fetch
  useEffect(() => {
    isMountedRef.current = true;
    fetchAgentDetail();

    return () => {
      isMountedRef.current = false;
    };
  }, [teamId, agentId, enabled]); // Don't include fetchAgentDetail to avoid infinite loop

  // Polling (only when pollInterval is set)
  useEffect(() => {
    if (!pollInterval || !enabled) {
      return;
    }

    const intervalId = setInterval(() => {
      fetchAgentDetail();
    }, pollInterval);

    return () => {
      clearInterval(intervalId);
    };
  }, [pollInterval, enabled, teamId, agentId]);

  return {
    agent,
    isLoading,
    error,
    refetch: fetchAgentDetail,
  };
}

export default useAgentDetail;
