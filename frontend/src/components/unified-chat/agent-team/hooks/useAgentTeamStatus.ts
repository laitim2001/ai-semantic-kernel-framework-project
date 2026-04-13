/**
 * useTeamStatus Hook
 *
 * Sprint 105: OrchestrationPanel 整合 + 狀態管理
 *
 * Encapsulates team state access and provides computed properties
 * and action handlers for team UI components.
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
 *     agentTeamStatus,
 *     isTeamActive,
 *     runningAgents,
 *     handleWorkerSelect,
 *   } = useTeamStatus();
 *
 *   return (
 *     <div>
 *       {isTeamActive && <p>Team is running...</p>}
 *       <WorkerList
 *         agents={runningAgents}
 *         onSelect={handleWorkerSelect}
 *       />
 *     </div>
 *   );
 * }
 * ```
 */

import { useCallback, useMemo } from 'react';
import { useAgentTeamStore } from '@/stores/agentTeamStore';
import type { UIAgentSummary, UIAgentTeamStatus, AgentDetail } from '../types';

/**
 * Hook return type
 */
export interface UseTeamStatusReturn {
  // State
  agentTeamStatus: UIAgentTeamStatus | null;
  selectedAgentId: string | null;
  selectedAgentDetail: AgentDetail | null;
  isDrawerOpen: boolean;
  isLoading: boolean;
  error: string | null;

  // Computed properties
  isTeamActive: boolean;
  isSwarmCompleted: boolean;
  completedAgents: UIAgentSummary[];
  runningAgents: UIAgentSummary[];
  pendingAgents: UIAgentSummary[];
  failedAgents: UIAgentSummary[];
  totalProgress: number;
  workersCount: {
    total: number;
    completed: number;
    running: number;
    pending: number;
    failed: number;
  };

  // Actions
  handleWorkerSelect: (agent: UIAgentSummary) => void;
  handleDrawerClose: () => void;
  setAgentDetail: (detail: AgentDetail | null) => void;
  reset: () => void;
}

/**
 * useTeamStatus - Encapsulates team state access and operations
 *
 * Provides:
 * - Direct state access
 * - Computed properties for agent filtering
 * - Memoized action handlers
 *
 * @returns Object containing state, computed properties, and actions
 */
export function useTeamStatus(): UseTeamStatusReturn {
  // Get store state and actions
  const agentTeamStatus = useAgentTeamStore((state) => state.agentTeamStatus);
  const selectedAgentId = useAgentTeamStore((state) => state.selectedAgentId);
  const selectedAgentDetail = useAgentTeamStore((state) => state.selectedAgentDetail);
  const isDrawerOpen = useAgentTeamStore((state) => state.isDrawerOpen);
  const isLoading = useAgentTeamStore((state) => state.isLoading);
  const error = useAgentTeamStore((state) => state.error);

  const selectAgent = useAgentTeamStore((state) => state.selectAgent);
  const openDrawer = useAgentTeamStore((state) => state.openDrawer);
  const closeDrawer = useAgentTeamStore((state) => state.closeDrawer);
  const setAgentDetail = useAgentTeamStore((state) => state.setAgentDetail);
  const reset = useAgentTeamStore((state) => state.reset);

  // =========================================================================
  // Computed Properties
  // =========================================================================

  /**
   * Is the team currently executing
   */
  const isTeamActive = useMemo(() => {
    return agentTeamStatus?.status === 'executing';
  }, [agentTeamStatus?.status]);

  /**
   * Is the team completed (successfully or failed)
   */
  const isSwarmCompleted = useMemo(() => {
    return agentTeamStatus?.status === 'completed' || agentTeamStatus?.status === 'failed';
  }, [agentTeamStatus?.status]);

  /**
   * Workers that have completed successfully
   */
  const completedAgents = useMemo(() => {
    return agentTeamStatus?.agents.filter((w) => w.status === 'completed') || [];
  }, [agentTeamStatus?.agents]);

  /**
   * Workers currently running
   */
  const runningAgents = useMemo(() => {
    return agentTeamStatus?.agents.filter((w) => w.status === 'running') || [];
  }, [agentTeamStatus?.agents]);

  /**
   * Workers pending start
   */
  const pendingAgents = useMemo(() => {
    return agentTeamStatus?.agents.filter((w) => w.status === 'pending') || [];
  }, [agentTeamStatus?.agents]);

  /**
   * Workers that have failed
   */
  const failedAgents = useMemo(() => {
    return agentTeamStatus?.agents.filter((w) => w.status === 'failed') || [];
  }, [agentTeamStatus?.agents]);

  /**
   * Overall progress percentage
   */
  const totalProgress = useMemo(() => {
    return agentTeamStatus?.overallProgress || 0;
  }, [agentTeamStatus?.overallProgress]);

  /**
   * Agent counts by status
   */
  const workersCount = useMemo(() => {
    const agents = agentTeamStatus?.agents || [];
    return {
      total: agents.length,
      completed: completedAgents.length,
      running: runningAgents.length,
      pending: pendingAgents.length,
      failed: failedAgents.length,
    };
  }, [agentTeamStatus?.agents, completedAgents, runningAgents, pendingAgents, failedAgents]);

  // =========================================================================
  // Action Handlers
  // =========================================================================

  /**
   * Handle agent selection - select and open drawer
   */
  const handleWorkerSelect = useCallback(
    (agent: UIAgentSummary) => {
      selectAgent(agent);
      openDrawer();
    },
    [selectAgent, openDrawer]
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
    agentTeamStatus,
    selectedAgentId,
    selectedAgentDetail,
    isDrawerOpen,
    isLoading,
    error,

    // Computed properties
    isTeamActive,
    isSwarmCompleted,
    completedAgents,
    runningAgents,
    pendingAgents,
    failedAgents,
    totalProgress,
    workersCount,

    // Actions
    handleWorkerSelect,
    handleDrawerClose,
    setAgentDetail,
    reset,
  };
}

export default useTeamStatus;
