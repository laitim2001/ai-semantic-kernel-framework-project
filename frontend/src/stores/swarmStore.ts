/**
 * Swarm Store - Zustand State Management for Agent Swarm
 *
 * Sprint 105: OrchestrationPanel 整合 + 狀態管理
 *
 * Manages the state of multi-agent swarm executions including:
 * - Swarm status and overall progress
 * - Individual worker states
 * - Worker detail views
 * - Drawer state
 *
 * Uses immer for immutable updates and devtools for debugging.
 */

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { devtools } from 'zustand/middleware';
import type {
  UIAgentSwarmStatus,
  UIWorkerSummary,
  WorkerDetail,
  ThinkingContent,
  ToolCallInfo,
  WorkerThinkingPayload,
  WorkerToolCallPayload,
  WorkerProgressPayload,
  WorkerCompletedPayload,
} from '@/components/unified-chat/agent-swarm/types';

// =============================================================================
// Types
// =============================================================================

interface SwarmState {
  // Core state
  swarmStatus: UIAgentSwarmStatus | null;
  selectedWorkerId: string | null;
  selectedWorkerDetail: WorkerDetail | null;
  isDrawerOpen: boolean;
  isLoading: boolean;
  error: string | null;
}

interface SwarmActions {
  // Swarm-level actions
  setSwarmStatus: (status: UIAgentSwarmStatus | null) => void;
  updateSwarmProgress: (progress: number) => void;
  completeSwarm: (status: 'completed' | 'failed', completedAt?: string) => void;

  // Worker-level actions
  addWorker: (worker: UIWorkerSummary) => void;
  updateWorkerProgress: (payload: WorkerProgressPayload) => void;
  updateWorkerThinking: (payload: WorkerThinkingPayload) => void;
  updateWorkerToolCall: (payload: WorkerToolCallPayload) => void;
  completeWorker: (payload: WorkerCompletedPayload) => void;

  // UI actions
  selectWorker: (worker: UIWorkerSummary | null) => void;
  setWorkerDetail: (detail: WorkerDetail | null) => void;
  openDrawer: () => void;
  closeDrawer: () => void;

  // Utility actions
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

type SwarmStore = SwarmState & SwarmActions;

// =============================================================================
// Initial State
// =============================================================================

const initialState: SwarmState = {
  swarmStatus: null,
  selectedWorkerId: null,
  selectedWorkerDetail: null,
  isDrawerOpen: false,
  isLoading: false,
  error: null,
};

// =============================================================================
// Store Implementation
// =============================================================================

export const useSwarmStore = create<SwarmStore>()(
  devtools(
    immer((set) => ({
      // Initial state
      ...initialState,

      // =====================================================================
      // Swarm-level Actions
      // =====================================================================

      setSwarmStatus: (status) =>
        set(
          (state) => {
            state.swarmStatus = status;
          },
          false,
          'setSwarmStatus'
        ),

      updateSwarmProgress: (progress) =>
        set(
          (state) => {
            if (state.swarmStatus) {
              state.swarmStatus.overallProgress = progress;
            }
          },
          false,
          'updateSwarmProgress'
        ),

      completeSwarm: (status, completedAt) =>
        set(
          (state) => {
            if (state.swarmStatus) {
              state.swarmStatus.status = status;
              state.swarmStatus.completedAt = completedAt || new Date().toISOString();
              if (status === 'completed') {
                state.swarmStatus.overallProgress = 100;
              }
            }
          },
          false,
          'completeSwarm'
        ),

      // =====================================================================
      // Worker-level Actions
      // =====================================================================

      addWorker: (worker) =>
        set(
          (state) => {
            if (state.swarmStatus) {
              // Check if worker already exists
              const existingIndex = state.swarmStatus.workers.findIndex(
                (w: UIWorkerSummary) => w.workerId === worker.workerId
              );
              if (existingIndex === -1) {
                state.swarmStatus.workers.push(worker);
                state.swarmStatus.totalWorkers = state.swarmStatus.workers.length;
              }
            }
          },
          false,
          'addWorker'
        ),

      updateWorkerProgress: (payload) =>
        set(
          (state) => {
            if (!state.swarmStatus) return;

            const workerIndex = state.swarmStatus.workers.findIndex(
              (w: UIWorkerSummary) => w.workerId === payload.worker_id
            );
            if (workerIndex === -1) return;

            // Update worker in the list
            const worker = state.swarmStatus.workers[workerIndex];
            worker.progress = payload.progress;
            worker.currentAction = payload.current_action || undefined;
            worker.status = payload.status as UIWorkerSummary['status'];

            // Recalculate overall progress
            const totalProgress = state.swarmStatus.workers.reduce(
              (sum: number, w: UIWorkerSummary) => sum + w.progress,
              0
            );
            state.swarmStatus.overallProgress = Math.round(
              totalProgress / state.swarmStatus.workers.length
            );
          },
          false,
          'updateWorkerProgress'
        ),

      updateWorkerThinking: (payload) =>
        set(
          (state) => {
            // Update the selected worker detail if it matches
            if (
              state.selectedWorkerDetail &&
              state.selectedWorkerDetail.workerId === payload.worker_id
            ) {
              const thinkingHistory = state.selectedWorkerDetail.thinkingHistory;
              const lastThinking = thinkingHistory[thinkingHistory.length - 1];

              // Create new thinking content
              const newThinking: ThinkingContent = {
                content: payload.thinking_content,
                timestamp: payload.timestamp,
                tokenCount: payload.token_count || undefined,
              };

              if (
                lastThinking &&
                payload.thinking_content.startsWith(lastThinking.content)
              ) {
                // Incremental update - replace last thinking block
                thinkingHistory[thinkingHistory.length - 1] = newThinking;
              } else {
                // New thinking block
                thinkingHistory.push(newThinking);
              }
            }
          },
          false,
          'updateWorkerThinking'
        ),

      updateWorkerToolCall: (payload) =>
        set(
          (state) => {
            if (!state.swarmStatus) return;

            // Update tool call count in worker summary
            const workerIndex = state.swarmStatus.workers.findIndex(
              (w: UIWorkerSummary) => w.workerId === payload.worker_id
            );
            if (workerIndex !== -1 && payload.status === 'running') {
              // Only increment when a new tool call starts
              state.swarmStatus.workers[workerIndex].toolCallsCount += 1;
            }

            // Update worker detail if it matches
            if (
              state.selectedWorkerDetail &&
              state.selectedWorkerDetail.workerId === payload.worker_id
            ) {
              const toolCalls = state.selectedWorkerDetail.toolCalls;
              const existingIndex = toolCalls.findIndex(
                (t: ToolCallInfo) => t.toolCallId === payload.tool_call_id
              );

              const updatedToolCall: ToolCallInfo = {
                toolCallId: payload.tool_call_id,
                toolName: payload.tool_name,
                status: payload.status,
                inputArgs: payload.input_args,
                outputResult: payload.output_result || undefined,
                error: payload.error || undefined,
                durationMs: payload.duration_ms || undefined,
              };

              if (existingIndex !== -1) {
                // Update existing tool call
                toolCalls[existingIndex] = updatedToolCall;
              } else {
                // Add new tool call
                toolCalls.push(updatedToolCall);
              }
            }
          },
          false,
          'updateWorkerToolCall'
        ),

      completeWorker: (payload) =>
        set(
          (state) => {
            if (!state.swarmStatus) return;

            const workerIndex = state.swarmStatus.workers.findIndex(
              (w: UIWorkerSummary) => w.workerId === payload.worker_id
            );
            if (workerIndex !== -1) {
              state.swarmStatus.workers[workerIndex].status = payload.status;
              state.swarmStatus.workers[workerIndex].progress = 100;
              state.swarmStatus.workers[workerIndex].completedAt = payload.completed_at;
            }

            // Update worker detail if it matches
            if (
              state.selectedWorkerDetail &&
              state.selectedWorkerDetail.workerId === payload.worker_id
            ) {
              state.selectedWorkerDetail.status = payload.status;
              state.selectedWorkerDetail.progress = 100;
              state.selectedWorkerDetail.completedAt = payload.completed_at;
              state.selectedWorkerDetail.result = payload.result || undefined;
              state.selectedWorkerDetail.error = payload.error || undefined;
            }

            // Recalculate overall progress
            const totalProgress = state.swarmStatus.workers.reduce(
              (sum: number, w: UIWorkerSummary) => sum + w.progress,
              0
            );
            state.swarmStatus.overallProgress = Math.round(
              totalProgress / state.swarmStatus.workers.length
            );
          },
          false,
          'completeWorker'
        ),

      // =====================================================================
      // UI Actions
      // =====================================================================

      selectWorker: (worker) =>
        set(
          (state) => {
            state.selectedWorkerId = worker?.workerId || null;
            // Clear old detail when selecting new worker
            state.selectedWorkerDetail = null;
          },
          false,
          'selectWorker'
        ),

      setWorkerDetail: (detail) =>
        set(
          (state) => {
            state.selectedWorkerDetail = detail;
          },
          false,
          'setWorkerDetail'
        ),

      openDrawer: () =>
        set(
          (state) => {
            state.isDrawerOpen = true;
          },
          false,
          'openDrawer'
        ),

      closeDrawer: () =>
        set(
          (state) => {
            state.isDrawerOpen = false;
            state.selectedWorkerId = null;
            state.selectedWorkerDetail = null;
          },
          false,
          'closeDrawer'
        ),

      // =====================================================================
      // Utility Actions
      // =====================================================================

      setLoading: (loading) =>
        set(
          (state) => {
            state.isLoading = loading;
          },
          false,
          'setLoading'
        ),

      setError: (error) =>
        set(
          (state) => {
            state.error = error;
          },
          false,
          'setError'
        ),

      reset: () =>
        set(
          () => initialState,
          false,
          'reset'
        ),
    })),
    { name: 'SwarmStore' }
  )
);

// =============================================================================
// Selectors
// =============================================================================

/**
 * Select swarm status
 */
export const selectSwarmStatus = (state: SwarmStore) => state.swarmStatus;

/**
 * Select workers list
 */
export const selectWorkers = (state: SwarmStore) => state.swarmStatus?.workers || [];

/**
 * Select selected worker ID
 */
export const selectSelectedWorkerId = (state: SwarmStore) => state.selectedWorkerId;

/**
 * Select selected worker detail
 */
export const selectSelectedWorkerDetail = (state: SwarmStore) => state.selectedWorkerDetail;

/**
 * Select drawer state
 */
export const selectIsDrawerOpen = (state: SwarmStore) => state.isDrawerOpen;

/**
 * Select loading state
 */
export const selectIsLoading = (state: SwarmStore) => state.isLoading;

/**
 * Select error
 */
export const selectError = (state: SwarmStore) => state.error;

/**
 * Select completed workers
 */
export const selectCompletedWorkers = (state: SwarmStore) =>
  state.swarmStatus?.workers.filter((w) => w.status === 'completed') || [];

/**
 * Select running workers
 */
export const selectRunningWorkers = (state: SwarmStore) =>
  state.swarmStatus?.workers.filter((w) => w.status === 'running') || [];

/**
 * Select failed workers
 */
export const selectFailedWorkers = (state: SwarmStore) =>
  state.swarmStatus?.workers.filter((w) => w.status === 'failed') || [];

/**
 * Select if swarm is active
 */
export const selectIsSwarmActive = (state: SwarmStore) =>
  state.swarmStatus?.status === 'executing';

export default useSwarmStore;
