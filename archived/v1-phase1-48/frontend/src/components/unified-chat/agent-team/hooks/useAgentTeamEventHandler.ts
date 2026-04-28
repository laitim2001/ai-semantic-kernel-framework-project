/**
 * useAgentTeamEventHandler Hook
 *
 * Sprint 105: OrchestrationPanel 整合 + 狀態管理
 *
 * Connects Agent Team SSE events to the Zustand store.
 * This hook bridges useAgentTeamEvents with useAgentTeamStore.
 *
 * @example
 * ```tsx
 * function ChatContainer({ sessionId }) {
 *   const eventSource = useEventSource(`/api/v1/ag-ui?session_id=${sessionId}`);
 *
 *   // This hook automatically updates the team store when events arrive
 *   useAgentTeamEventHandler(eventSource);
 *
 *   // The rest of your component can use agentTeamStore directly
 *   const { agentTeamStatus } = useTeamStatus();
 *
 *   return <AgentTeamPanel agentTeamStatus={agentTeamStatus} />;
 * }
 * ```
 */

import { useCallback } from 'react';
import { useAgentTeamStore } from '@/stores/agentTeamStore';
import { useAgentTeamEvents } from './useAgentTeamEvents';
import type {
  TeamCreatedPayload,
  TeamStatusUpdatePayload,
  TeamCompletedPayload,
  AgentStartedPayload,
  AgentProgressPayload,
  AgentThinkingPayload,
  AgentToolCallPayload,
  AgentMessagePayload,
  AgentCompletedPayload,
} from '../types/events';
import type { UIAgentTeamStatus, UIAgentSummary } from '../types';

/**
 * Options for useAgentTeamEventHandler
 */
export interface UseAgentTeamEventHandlerOptions {
  /** Callback when team is created */
  onTeamCreated?: (payload: TeamCreatedPayload) => void;
  /** Callback when team completes */
  onTeamCompleted?: (payload: TeamCompletedPayload) => void;
  /** Callback on any error */
  onError?: (error: Error) => void;
  /** Whether to log events to console (for debugging) */
  debug?: boolean;
}

/**
 * Hook to connect Agent Team SSE events to the Zustand store
 *
 * @param eventSource - EventSource instance or null
 * @param options - Optional callbacks and settings
 */
export function useAgentTeamEventHandler(
  eventSource: EventSource | null,
  options: UseAgentTeamEventHandlerOptions = {}
): void {
  const { onTeamCreated, onTeamCompleted, onError, debug = false } = options;

  // Get store actions
  const setTeamStatus = useAgentTeamStore((state) => state.setTeamStatus);
  const addAgent = useAgentTeamStore((state) => state.addAgent);
  const updateAgentProgress = useAgentTeamStore((state) => state.updateAgentProgress);
  const updateAgentThinking = useAgentTeamStore((state) => state.updateAgentThinking);
  const updateAgentToolCall = useAgentTeamStore((state) => state.updateAgentToolCall);
  const completeAgent = useAgentTeamStore((state) => state.completeAgent);
  const completeTeam = useAgentTeamStore((state) => state.completeTeam);
  const setError = useAgentTeamStore((state) => state.setError);

  // =========================================================================
  // Event Handlers
  // =========================================================================

  /**
   * Handle team_created event
   */
  const handleTeamCreated = useCallback(
    (payload: TeamCreatedPayload) => {
      if (debug) {
        console.log('[AgentTeamEventHandler] team_created', payload);
      }

      // Convert payload to UIAgentTeamStatus
      const agentTeamStatus: UIAgentTeamStatus = {
        teamId: payload.team_id,
        sessionId: payload.session_id,
        mode: payload.mode as UIAgentTeamStatus['mode'],
        status: 'initializing',
        totalAgents: payload.agents.length,
        overallProgress: 0,
        agents: payload.agents.map((w) => ({
          agentId: w.agent_id,
          agentName: w.agent_name,
          agentType: w.agent_type as UIAgentSummary['agentType'],
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

      setTeamStatus(agentTeamStatus);
      onTeamCreated?.(payload);
    },
    [setTeamStatus, onTeamCreated, debug]
  );

  /**
   * Handle team_status_update event
   */
  const handleTeamStatusUpdate = useCallback(
    (payload: TeamStatusUpdatePayload) => {
      if (debug) {
        console.log('[AgentTeamEventHandler] team_status_update', payload);
      }

      // Convert payload to UIAgentTeamStatus
      const agentTeamStatus: UIAgentTeamStatus = {
        teamId: payload.team_id,
        sessionId: payload.session_id,
        mode: payload.mode as UIAgentTeamStatus['mode'],
        status: payload.status === 'running' ? 'executing' : (payload.status as UIAgentTeamStatus['status']),
        totalAgents: payload.total_agents,
        overallProgress: payload.overall_progress,
        agents: payload.agents.map((w) => ({
          agentId: w.agent_id,
          agentName: w.agent_name,
          agentType: w.agent_type as UIAgentSummary['agentType'],
          role: w.role,
          status: (w.status || 'pending') as UIAgentSummary['status'],
          progress: w.progress || 0,
          currentAction: w.current_action || undefined,
          toolCallsCount: w.tool_calls_count || 0,
          createdAt: new Date().toISOString(),
        })),
        createdAt: new Date().toISOString(),
        metadata: payload.metadata,
      };

      setTeamStatus(agentTeamStatus);
    },
    [setTeamStatus, debug]
  );

  /**
   * Handle team_completed event
   */
  const handleTeamCompleted = useCallback(
    (payload: TeamCompletedPayload) => {
      if (debug) {
        console.log('[AgentTeamEventHandler] team_completed', payload);
      }

      completeTeam(payload.status, payload.completed_at);
      onTeamCompleted?.(payload);
    },
    [completeTeam, onTeamCompleted, debug]
  );

  /**
   * Handle agent_started event
   */
  const handleAgentStarted = useCallback(
    (payload: AgentStartedPayload) => {
      if (debug) {
        console.log('[AgentTeamEventHandler] agent_started', payload);
      }

      const agent: UIAgentSummary = {
        agentId: payload.agent_id,
        agentName: payload.agent_name,
        agentType: payload.agent_type as UIAgentSummary['agentType'],
        role: payload.role,
        status: 'running',
        progress: 0,
        currentAction: payload.task_description,
        toolCallsCount: 0,
        createdAt: payload.started_at,
        startedAt: payload.started_at,
      };

      addAgent(agent);
    },
    [addAgent, debug]
  );

  /**
   * Handle agent_progress event
   */
  const handleAgentProgress = useCallback(
    (payload: AgentProgressPayload) => {
      if (debug) {
        console.log('[AgentTeamEventHandler] agent_progress', payload);
      }

      updateAgentProgress(payload);
    },
    [updateAgentProgress, debug]
  );

  /**
   * Handle agent_thinking event
   */
  const handleAgentThinking = useCallback(
    (payload: AgentThinkingPayload) => {
      if (debug) {
        console.log('[AgentTeamEventHandler] agent_thinking', payload);
      }

      updateAgentThinking(payload);
    },
    [updateAgentThinking, debug]
  );

  /**
   * Handle agent_tool_call event
   */
  const handleAgentToolCall = useCallback(
    (payload: AgentToolCallPayload) => {
      if (debug) {
        console.log('[AgentTeamEventHandler] agent_tool_call', payload);
      }

      updateAgentToolCall(payload);
    },
    [updateAgentToolCall, debug]
  );

  /**
   * Handle agent_message event
   */
  const handleAgentMessage = useCallback(
    (payload: AgentMessagePayload) => {
      if (debug) {
        console.log('[AgentTeamEventHandler] agent_message', payload);
      }

      // Agent messages are stored in agent detail, which is managed
      // by useAgentDetail hook when the drawer is open
      // No direct store update needed here
    },
    [debug]
  );

  /**
   * Handle agent_completed event
   */
  const handleAgentCompleted = useCallback(
    (payload: AgentCompletedPayload) => {
      if (debug) {
        console.log('[AgentTeamEventHandler] agent_completed', payload);
      }

      completeAgent(payload);
    },
    [completeAgent, debug]
  );

  /**
   * Handle errors
   */
  const handleError = useCallback(
    (error: Error) => {
      if (debug) {
        console.error('[AgentTeamEventHandler] error', error);
      }

      setError(error.message);
      onError?.(error);
    },
    [setError, onError, debug]
  );

  // =========================================================================
  // Connect to SSE events
  // =========================================================================

  useAgentTeamEvents(eventSource, {
    onTeamCreated: handleTeamCreated,
    onTeamStatusUpdate: handleTeamStatusUpdate,
    onTeamCompleted: handleTeamCompleted,
    onWorkerStarted: handleAgentStarted,
    onWorkerProgress: handleAgentProgress,
    onWorkerThinking: handleAgentThinking,
    onWorkerToolCall: handleAgentToolCall,
    onAgentMessage: handleAgentMessage,
    onWorkerCompleted: handleAgentCompleted,
    onError: handleError,
  });
}

export default useAgentTeamEventHandler;
