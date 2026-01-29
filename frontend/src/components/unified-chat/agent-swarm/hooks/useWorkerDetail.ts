/**
 * useWorkerDetail Hook
 *
 * Fetches and manages Worker detail data with optional polling.
 * Sprint 103: WorkerDetailDrawer
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type { WorkerDetail } from '../types';

// =============================================================================
// Types
// =============================================================================

export interface UseWorkerDetailOptions {
  /** Swarm ID */
  swarmId: string;
  /** Worker ID */
  workerId: string;
  /** Whether to fetch data */
  enabled?: boolean;
  /** Poll interval in milliseconds (only for running workers) */
  pollInterval?: number;
}

export interface UseWorkerDetailResult {
  /** Worker detail data */
  worker: WorkerDetail | null;
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
function transformWorkerDetail(data: Record<string, unknown>): WorkerDetail {
  return {
    workerId: data.worker_id as string,
    workerName: data.worker_name as string,
    workerType: data.worker_type as WorkerDetail['workerType'],
    role: data.role as string,
    status: data.status as WorkerDetail['status'],
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
 * useWorkerDetail - Fetch and manage Worker detail data
 *
 * @param options - Configuration options
 * @returns Worker detail state and methods
 *
 * @example
 * ```tsx
 * const { worker, isLoading, error, refetch } = useWorkerDetail({
 *   swarmId: 'swarm-123',
 *   workerId: 'worker-456',
 *   enabled: isOpen,
 *   pollInterval: worker?.status === 'running' ? 2000 : undefined,
 * });
 * ```
 */
export function useWorkerDetail({
  swarmId,
  workerId,
  enabled = true,
  pollInterval,
}: UseWorkerDetailOptions): UseWorkerDetailResult {
  const [worker, setWorker] = useState<WorkerDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Track if component is mounted to avoid state updates after unmount
  const isMountedRef = useRef(true);

  // Fetch worker detail
  const fetchWorkerDetail = useCallback(async () => {
    if (!enabled || !swarmId || !workerId) {
      return;
    }

    // Only set loading on first fetch, not on poll updates
    if (!worker) {
      setIsLoading(true);
    }
    setError(null);

    try {
      const response = await fetch(
        `/api/v1/swarm/${swarmId}/workers/${workerId}?include_thinking=true&include_messages=true`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch worker detail: ${response.statusText}`);
      }

      const data = await response.json();

      if (isMountedRef.current) {
        const transformed = transformWorkerDetail(data);
        setWorker(transformed);
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
  }, [swarmId, workerId, enabled, worker]);

  // Initial fetch
  useEffect(() => {
    isMountedRef.current = true;
    fetchWorkerDetail();

    return () => {
      isMountedRef.current = false;
    };
  }, [swarmId, workerId, enabled]); // Don't include fetchWorkerDetail to avoid infinite loop

  // Polling (only when pollInterval is set)
  useEffect(() => {
    if (!pollInterval || !enabled) {
      return;
    }

    const intervalId = setInterval(() => {
      fetchWorkerDetail();
    }, pollInterval);

    return () => {
      clearInterval(intervalId);
    };
  }, [pollInterval, enabled, swarmId, workerId]);

  return {
    worker,
    isLoading,
    error,
    refetch: fetchWorkerDetail,
  };
}

export default useWorkerDetail;
