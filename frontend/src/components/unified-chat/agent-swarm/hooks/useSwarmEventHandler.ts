/**
 * useSwarmEventHandler Hook
 *
 * Sprint 105: OrchestrationPanel 整合 + 狀態管理
 *
 * Connects Swarm SSE events to the Zustand store.
 * This hook bridges useSwarmEvents with useSwarmStore.
 *
 * @example
 * ```tsx
 * function ChatContainer({ sessionId }) {
 *   const eventSource = useEventSource(`/api/v1/ag-ui?session_id=${sessionId}`);
 *
 *   // This hook automatically updates the swarm store when events arrive
 *   useSwarmEventHandler(eventSource);
 *
 *   // The rest of your component can use swarmStore directly
 *   const { swarmStatus } = useSwarmStatus();
 *
 *   return <AgentSwarmPanel swarmStatus={swarmStatus} />;
 * }
 * ```
 */

import { useCallback } from 'react';
import { useSwarmStore } from '@/stores/swarmStore';
import { useSwarmEvents } from './useSwarmEvents';
import type {
  SwarmCreatedPayload,
  SwarmStatusUpdatePayload,
  SwarmCompletedPayload,
  WorkerStartedPayload,
  WorkerProgressPayload,
  WorkerThinkingPayload,
  WorkerToolCallPayload,
  WorkerMessagePayload,
  WorkerCompletedPayload,
} from '../types/events';
import type { UIAgentSwarmStatus, UIWorkerSummary } from '../types';

/**
 * Options for useSwarmEventHandler
 */
export interface UseSwarmEventHandlerOptions {
  /** Callback when swarm is created */
  onSwarmCreated?: (payload: SwarmCreatedPayload) => void;
  /** Callback when swarm completes */
  onSwarmCompleted?: (payload: SwarmCompletedPayload) => void;
  /** Callback on any error */
  onError?: (error: Error) => void;
  /** Whether to log events to console (for debugging) */
  debug?: boolean;
}

/**
 * Hook to connect Swarm SSE events to the Zustand store
 *
 * @param eventSource - EventSource instance or null
 * @param options - Optional callbacks and settings
 */
export function useSwarmEventHandler(
  eventSource: EventSource | null,
  options: UseSwarmEventHandlerOptions = {}
): void {
  const { onSwarmCreated, onSwarmCompleted, onError, debug = false } = options;

  // Get store actions
  const setSwarmStatus = useSwarmStore((state) => state.setSwarmStatus);
  const addWorker = useSwarmStore((state) => state.addWorker);
  const updateWorkerProgress = useSwarmStore((state) => state.updateWorkerProgress);
  const updateWorkerThinking = useSwarmStore((state) => state.updateWorkerThinking);
  const updateWorkerToolCall = useSwarmStore((state) => state.updateWorkerToolCall);
  const completeWorker = useSwarmStore((state) => state.completeWorker);
  const completeSwarm = useSwarmStore((state) => state.completeSwarm);
  const setError = useSwarmStore((state) => state.setError);

  // =========================================================================
  // Event Handlers
  // =========================================================================

  /**
   * Handle swarm_created event
   */
  const handleSwarmCreated = useCallback(
    (payload: SwarmCreatedPayload) => {
      if (debug) {
        console.log('[SwarmEventHandler] swarm_created', payload);
      }

      // Convert payload to UIAgentSwarmStatus
      const swarmStatus: UIAgentSwarmStatus = {
        swarmId: payload.swarm_id,
        sessionId: payload.session_id,
        mode: payload.mode as UIAgentSwarmStatus['mode'],
        status: 'initializing',
        totalWorkers: payload.workers.length,
        overallProgress: 0,
        workers: payload.workers.map((w) => ({
          workerId: w.worker_id,
          workerName: w.worker_name,
          workerType: w.worker_type as UIWorkerSummary['workerType'],
          role: w.role,
          status: 'pending' as const,
          progress: 0,
          currentAction: undefined,
          toolCallsCount: 0,
          createdAt: payload.created_at,
        })),
        createdAt: payload.created_at,
        metadata: {},
      };

      setSwarmStatus(swarmStatus);
      onSwarmCreated?.(payload);
    },
    [setSwarmStatus, onSwarmCreated, debug]
  );

  /**
   * Handle swarm_status_update event
   */
  const handleSwarmStatusUpdate = useCallback(
    (payload: SwarmStatusUpdatePayload) => {
      if (debug) {
        console.log('[SwarmEventHandler] swarm_status_update', payload);
      }

      // Convert payload to UIAgentSwarmStatus
      const swarmStatus: UIAgentSwarmStatus = {
        swarmId: payload.swarm_id,
        sessionId: payload.session_id,
        mode: payload.mode as UIAgentSwarmStatus['mode'],
        status: payload.status === 'running' ? 'executing' : (payload.status as UIAgentSwarmStatus['status']),
        totalWorkers: payload.total_workers,
        overallProgress: payload.overall_progress,
        workers: payload.workers.map((w) => ({
          workerId: w.worker_id,
          workerName: w.worker_name,
          workerType: w.worker_type as UIWorkerSummary['workerType'],
          role: w.role,
          status: (w.status || 'pending') as UIWorkerSummary['status'],
          progress: w.progress || 0,
          currentAction: w.current_action || undefined,
          toolCallsCount: w.tool_calls_count || 0,
          createdAt: new Date().toISOString(),
        })),
        createdAt: new Date().toISOString(),
        metadata: payload.metadata,
      };

      setSwarmStatus(swarmStatus);
    },
    [setSwarmStatus, debug]
  );

  /**
   * Handle swarm_completed event
   */
  const handleSwarmCompleted = useCallback(
    (payload: SwarmCompletedPayload) => {
      if (debug) {
        console.log('[SwarmEventHandler] swarm_completed', payload);
      }

      completeSwarm(payload.status, payload.completed_at);
      onSwarmCompleted?.(payload);
    },
    [completeSwarm, onSwarmCompleted, debug]
  );

  /**
   * Handle worker_started event
   */
  const handleWorkerStarted = useCallback(
    (payload: WorkerStartedPayload) => {
      if (debug) {
        console.log('[SwarmEventHandler] worker_started', payload);
      }

      const worker: UIWorkerSummary = {
        workerId: payload.worker_id,
        workerName: payload.worker_name,
        workerType: payload.worker_type as UIWorkerSummary['workerType'],
        role: payload.role,
        status: 'running',
        progress: 0,
        currentAction: payload.task_description,
        toolCallsCount: 0,
        createdAt: payload.started_at,
        startedAt: payload.started_at,
      };

      addWorker(worker);
    },
    [addWorker, debug]
  );

  /**
   * Handle worker_progress event
   */
  const handleWorkerProgress = useCallback(
    (payload: WorkerProgressPayload) => {
      if (debug) {
        console.log('[SwarmEventHandler] worker_progress', payload);
      }

      updateWorkerProgress(payload);
    },
    [updateWorkerProgress, debug]
  );

  /**
   * Handle worker_thinking event
   */
  const handleWorkerThinking = useCallback(
    (payload: WorkerThinkingPayload) => {
      if (debug) {
        console.log('[SwarmEventHandler] worker_thinking', payload);
      }

      updateWorkerThinking(payload);
    },
    [updateWorkerThinking, debug]
  );

  /**
   * Handle worker_tool_call event
   */
  const handleWorkerToolCall = useCallback(
    (payload: WorkerToolCallPayload) => {
      if (debug) {
        console.log('[SwarmEventHandler] worker_tool_call', payload);
      }

      updateWorkerToolCall(payload);
    },
    [updateWorkerToolCall, debug]
  );

  /**
   * Handle worker_message event
   */
  const handleWorkerMessage = useCallback(
    (payload: WorkerMessagePayload) => {
      if (debug) {
        console.log('[SwarmEventHandler] worker_message', payload);
      }

      // Worker messages are stored in worker detail, which is managed
      // by useWorkerDetail hook when the drawer is open
      // No direct store update needed here
    },
    [debug]
  );

  /**
   * Handle worker_completed event
   */
  const handleWorkerCompleted = useCallback(
    (payload: WorkerCompletedPayload) => {
      if (debug) {
        console.log('[SwarmEventHandler] worker_completed', payload);
      }

      completeWorker(payload);
    },
    [completeWorker, debug]
  );

  /**
   * Handle errors
   */
  const handleError = useCallback(
    (error: Error) => {
      if (debug) {
        console.error('[SwarmEventHandler] error', error);
      }

      setError(error.message);
      onError?.(error);
    },
    [setError, onError, debug]
  );

  // =========================================================================
  // Connect to SSE events
  // =========================================================================

  useSwarmEvents(eventSource, {
    onSwarmCreated: handleSwarmCreated,
    onSwarmStatusUpdate: handleSwarmStatusUpdate,
    onSwarmCompleted: handleSwarmCompleted,
    onWorkerStarted: handleWorkerStarted,
    onWorkerProgress: handleWorkerProgress,
    onWorkerThinking: handleWorkerThinking,
    onWorkerToolCall: handleWorkerToolCall,
    onWorkerMessage: handleWorkerMessage,
    onWorkerCompleted: handleWorkerCompleted,
    onError: handleError,
  });
}

export default useSwarmEventHandler;
