/**
 * useSwarmStatus Hook
 *
 * Sprint 105: OrchestrationPanel 整合 + 狀態管理
 *
 * Encapsulates swarm state access and provides computed properties
 * and action handlers for swarm UI components.
 *
 * Features:
 * - Memoized computed properties
 * - Stable action handlers
 * - Type-safe state access
 *
 * @example
 * ```tsx
 * function SwarmDisplay() {
 *   const {
 *     swarmStatus,
 *     isSwarmActive,
 *     runningWorkers,
 *     handleWorkerSelect,
 *   } = useSwarmStatus();
 *
 *   return (
 *     <div>
 *       {isSwarmActive && <p>Swarm is running...</p>}
 *       <WorkerList
 *         workers={runningWorkers}
 *         onSelect={handleWorkerSelect}
 *       />
 *     </div>
 *   );
 * }
 * ```
 */

import { useCallback, useMemo } from 'react';
import { useSwarmStore } from '@/stores/swarmStore';
import type { UIWorkerSummary, UIAgentSwarmStatus, WorkerDetail } from '../types';

/**
 * Hook return type
 */
export interface UseSwarmStatusReturn {
  // State
  swarmStatus: UIAgentSwarmStatus | null;
  selectedWorkerId: string | null;
  selectedWorkerDetail: WorkerDetail | null;
  isDrawerOpen: boolean;
  isLoading: boolean;
  error: string | null;

  // Computed properties
  isSwarmActive: boolean;
  isSwarmCompleted: boolean;
  completedWorkers: UIWorkerSummary[];
  runningWorkers: UIWorkerSummary[];
  pendingWorkers: UIWorkerSummary[];
  failedWorkers: UIWorkerSummary[];
  totalProgress: number;
  workersCount: {
    total: number;
    completed: number;
    running: number;
    pending: number;
    failed: number;
  };

  // Actions
  handleWorkerSelect: (worker: UIWorkerSummary) => void;
  handleDrawerClose: () => void;
  setWorkerDetail: (detail: WorkerDetail | null) => void;
  reset: () => void;
}

/**
 * useSwarmStatus - Encapsulates swarm state access and operations
 *
 * Provides:
 * - Direct state access
 * - Computed properties for worker filtering
 * - Memoized action handlers
 *
 * @returns Object containing state, computed properties, and actions
 */
export function useSwarmStatus(): UseSwarmStatusReturn {
  // Get store state and actions
  const swarmStatus = useSwarmStore((state) => state.swarmStatus);
  const selectedWorkerId = useSwarmStore((state) => state.selectedWorkerId);
  const selectedWorkerDetail = useSwarmStore((state) => state.selectedWorkerDetail);
  const isDrawerOpen = useSwarmStore((state) => state.isDrawerOpen);
  const isLoading = useSwarmStore((state) => state.isLoading);
  const error = useSwarmStore((state) => state.error);

  const selectWorker = useSwarmStore((state) => state.selectWorker);
  const openDrawer = useSwarmStore((state) => state.openDrawer);
  const closeDrawer = useSwarmStore((state) => state.closeDrawer);
  const setWorkerDetail = useSwarmStore((state) => state.setWorkerDetail);
  const reset = useSwarmStore((state) => state.reset);

  // =========================================================================
  // Computed Properties
  // =========================================================================

  /**
   * Is the swarm currently executing
   */
  const isSwarmActive = useMemo(() => {
    return swarmStatus?.status === 'executing';
  }, [swarmStatus?.status]);

  /**
   * Is the swarm completed (successfully or failed)
   */
  const isSwarmCompleted = useMemo(() => {
    return swarmStatus?.status === 'completed' || swarmStatus?.status === 'failed';
  }, [swarmStatus?.status]);

  /**
   * Workers that have completed successfully
   */
  const completedWorkers = useMemo(() => {
    return swarmStatus?.workers.filter((w) => w.status === 'completed') || [];
  }, [swarmStatus?.workers]);

  /**
   * Workers currently running
   */
  const runningWorkers = useMemo(() => {
    return swarmStatus?.workers.filter((w) => w.status === 'running') || [];
  }, [swarmStatus?.workers]);

  /**
   * Workers pending start
   */
  const pendingWorkers = useMemo(() => {
    return swarmStatus?.workers.filter((w) => w.status === 'pending') || [];
  }, [swarmStatus?.workers]);

  /**
   * Workers that have failed
   */
  const failedWorkers = useMemo(() => {
    return swarmStatus?.workers.filter((w) => w.status === 'failed') || [];
  }, [swarmStatus?.workers]);

  /**
   * Overall progress percentage
   */
  const totalProgress = useMemo(() => {
    return swarmStatus?.overallProgress || 0;
  }, [swarmStatus?.overallProgress]);

  /**
   * Worker counts by status
   */
  const workersCount = useMemo(() => {
    const workers = swarmStatus?.workers || [];
    return {
      total: workers.length,
      completed: completedWorkers.length,
      running: runningWorkers.length,
      pending: pendingWorkers.length,
      failed: failedWorkers.length,
    };
  }, [swarmStatus?.workers, completedWorkers, runningWorkers, pendingWorkers, failedWorkers]);

  // =========================================================================
  // Action Handlers
  // =========================================================================

  /**
   * Handle worker selection - select and open drawer
   */
  const handleWorkerSelect = useCallback(
    (worker: UIWorkerSummary) => {
      selectWorker(worker);
      openDrawer();
    },
    [selectWorker, openDrawer]
  );

  /**
   * Handle drawer close
   */
  const handleDrawerClose = useCallback(() => {
    closeDrawer();
  }, [closeDrawer]);

  // =========================================================================
  // Return
  // =========================================================================

  return {
    // State
    swarmStatus,
    selectedWorkerId,
    selectedWorkerDetail,
    isDrawerOpen,
    isLoading,
    error,

    // Computed properties
    isSwarmActive,
    isSwarmCompleted,
    completedWorkers,
    runningWorkers,
    pendingWorkers,
    failedWorkers,
    totalProgress,
    workersCount,

    // Actions
    handleWorkerSelect,
    handleDrawerClose,
    setWorkerDetail,
    reset,
  };
}

export default useSwarmStatus;
