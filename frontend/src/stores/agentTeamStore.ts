/**
 * Agent Team Store - Zustand State Management for Agent Team
 *
 * Sprint 105: OrchestrationPanel 整合 + 狀態管理
 *
 * Manages the state of multi-agent team executions including:
 * - Team status and overall progress
 * - Individual agent states
 * - Agent detail views
 * - Drawer state
 *
 * Uses immer for immutable updates and devtools for debugging.
 */

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { devtools } from 'zustand/middleware';
import type {
  UIAgentTeamStatus,
  UIAgentSummary,
  AgentDetail,
  ThinkingContent,
  ToolCallInfo,
  AgentThinkingPayload,
  AgentToolCallPayload,
  AgentProgressPayload,
  AgentCompletedPayload,
} from '@/components/unified-chat/agent-team/types';

// =============================================================================
// Types
// =============================================================================

interface AgentTeamState {
  // Core state
  agentTeamStatus: UIAgentTeamStatus | null;
  selectedAgentId: string | null;
  selectedAgentDetail: AgentDetail | null;
  isDrawerOpen: boolean;
  isLoading: boolean;
  error: string | null;
}

interface AgentTeamActions {
  // Team-level actions
  setTeamStatus: (status: UIAgentTeamStatus | null) => void;
  updateTeamProgress: (progress: number) => void;
  completeTeam: (status: 'completed' | 'failed', completedAt?: string) => void;

  // Agent-level actions
  addAgent: (agent: UIAgentSummary) => void;
  updateAgentProgress: (payload: AgentProgressPayload) => void;
  updateAgentThinking: (payload: AgentThinkingPayload) => void;
  updateAgentToolCall: (payload: AgentToolCallPayload) => void;
  completeAgent: (payload: AgentCompletedPayload) => void;

  // UI actions
  selectAgent: (agent: UIAgentSummary | null) => void;
  setAgentDetail: (detail: AgentDetail | null) => void;
  openDrawer: () => void;
  closeDrawer: () => void;

  // Utility actions
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

type AgentTeamStore = AgentTeamState & AgentTeamActions;

// =============================================================================
// Initial State
// =============================================================================

const initialState: AgentTeamState = {
  agentTeamStatus: null,
  selectedAgentId: null,
  selectedAgentDetail: null,
  isDrawerOpen: false,
  isLoading: false,
  error: null,
};

// =============================================================================
// Store Implementation
// =============================================================================

export const useAgentTeamStore = create<AgentTeamStore>()(
  devtools(
    immer((set) => ({
      // Initial state
      ...initialState,

      // =====================================================================
      // Team-level Actions
      // =====================================================================

      setTeamStatus: (status) =>
        set(
          (state) => {
            state.agentTeamStatus = status;
          },
          false,
          'setTeamStatus'
        ),

      updateTeamProgress: (progress) =>
        set(
          (state) => {
            if (state.agentTeamStatus) {
              state.agentTeamStatus.overallProgress = progress;
            }
          },
          false,
          'updateTeamProgress'
        ),

      completeTeam: (status, completedAt) =>
        set(
          (state) => {
            if (state.agentTeamStatus) {
              state.agentTeamStatus.status = status;
              state.agentTeamStatus.completedAt = completedAt || new Date().toISOString();
              if (status === 'completed') {
                state.agentTeamStatus.overallProgress = 100;
              }
            }
          },
          false,
          'completeTeam'
        ),

      // =====================================================================
      // Agent-level Actions
      // =====================================================================

      addAgent: (agent) =>
        set(
          (state) => {
            if (state.agentTeamStatus) {
              // Check if agent already exists
              const existingIndex = state.agentTeamStatus.agents.findIndex(
                (w: UIAgentSummary) => w.agentId === agent.agentId
              );
              if (existingIndex === -1) {
                state.agentTeamStatus.agents.push(agent);
                state.agentTeamStatus.totalAgents = state.agentTeamStatus.agents.length;
              }
            }
          },
          false,
          'addAgent'
        ),

      updateAgentProgress: (payload) =>
        set(
          (state) => {
            if (!state.agentTeamStatus) return;

            const workerIndex = state.agentTeamStatus.agents.findIndex(
              (w: UIAgentSummary) => w.agentId === payload.agent_id
            );
            if (workerIndex === -1) return;

            // Update agent in the list
            const agent = state.agentTeamStatus.agents[workerIndex];
            agent.progress = payload.progress;
            agent.currentAction = payload.current_action || undefined;
            agent.status = payload.status as UIAgentSummary['status'];

            // Recalculate overall progress
            const totalProgress = state.agentTeamStatus.agents.reduce(
              (sum: number, w: UIAgentSummary) => sum + w.progress,
              0
            );
            state.agentTeamStatus.overallProgress = Math.round(
              totalProgress / state.agentTeamStatus.agents.length
            );
          },
          false,
          'updateAgentProgress'
        ),

      updateAgentThinking: (payload) =>
        set(
          (state) => {
            // Update the selected agent detail if it matches
            if (
              state.selectedAgentDetail &&
              state.selectedAgentDetail.agentId === payload.agent_id
            ) {
              const thinkingHistory = state.selectedAgentDetail.thinkingHistory;
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
          'updateAgentThinking'
        ),

      updateAgentToolCall: (payload) =>
        set(
          (state) => {
            if (!state.agentTeamStatus) return;

            // Update tool call count in agent summary
            const workerIndex = state.agentTeamStatus.agents.findIndex(
              (w: UIAgentSummary) => w.agentId === payload.agent_id
            );
            if (workerIndex !== -1 && payload.status === 'running') {
              // Only increment when a new tool call starts
              state.agentTeamStatus.agents[workerIndex].toolCallsCount += 1;
            }

            // Update agent detail if it matches
            if (
              state.selectedAgentDetail &&
              state.selectedAgentDetail.agentId === payload.agent_id
            ) {
              const toolCalls = state.selectedAgentDetail.toolCalls;
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
          'updateAgentToolCall'
        ),

      completeAgent: (payload) =>
        set(
          (state) => {
            if (!state.agentTeamStatus) return;

            const workerIndex = state.agentTeamStatus.agents.findIndex(
              (w: UIAgentSummary) => w.agentId === payload.agent_id
            );
            if (workerIndex !== -1) {
              state.agentTeamStatus.agents[workerIndex].status = payload.status;
              state.agentTeamStatus.agents[workerIndex].progress = 100;
              state.agentTeamStatus.agents[workerIndex].completedAt = payload.completed_at;
            }

            // Update agent detail if it matches
            if (
              state.selectedAgentDetail &&
              state.selectedAgentDetail.agentId === payload.agent_id
            ) {
              state.selectedAgentDetail.status = payload.status;
              state.selectedAgentDetail.progress = 100;
              state.selectedAgentDetail.completedAt = payload.completed_at;
              state.selectedAgentDetail.result = payload.result || undefined;
              state.selectedAgentDetail.error = payload.error || undefined;
            }

            // Recalculate overall progress
            const totalProgress = state.agentTeamStatus.agents.reduce(
              (sum: number, w: UIAgentSummary) => sum + w.progress,
              0
            );
            state.agentTeamStatus.overallProgress = Math.round(
              totalProgress / state.agentTeamStatus.agents.length
            );
          },
          false,
          'completeAgent'
        ),

      // =====================================================================
      // UI Actions
      // =====================================================================

      selectAgent: (agent) =>
        set(
          (state) => {
            state.selectedAgentId = agent?.agentId || null;
            // Clear old detail when selecting new agent
            state.selectedAgentDetail = null;
          },
          false,
          'selectAgent'
        ),

      setAgentDetail: (detail) =>
        set(
          (state) => {
            state.selectedAgentDetail = detail;
          },
          false,
          'setAgentDetail'
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
            state.selectedAgentId = null;
            state.selectedAgentDetail = null;
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
    { name: 'AgentTeamStore' }
  )
);

// =============================================================================
// Selectors
// =============================================================================

/**
 * Select team status
 */
export const selectTeamStatus = (state: AgentTeamStore) => state.agentTeamStatus;

/**
 * Select agents list
 */
export const selectAgents = (state: AgentTeamStore) => state.agentTeamStatus?.agents || [];

/**
 * Select selected agent ID
 */
export const selectSelectedAgentId = (state: AgentTeamStore) => state.selectedAgentId;

/**
 * Select selected agent detail
 */
export const selectSelectedAgentDetail = (state: AgentTeamStore) => state.selectedAgentDetail;

/**
 * Select drawer state
 */
export const selectIsDrawerOpen = (state: AgentTeamStore) => state.isDrawerOpen;

/**
 * Select loading state
 */
export const selectIsLoading = (state: AgentTeamStore) => state.isLoading;

/**
 * Select error
 */
export const selectError = (state: AgentTeamStore) => state.error;

/**
 * Select completed agents
 */
export const selectCompletedAgents = (state: AgentTeamStore) =>
  state.agentTeamStatus?.agents.filter((w) => w.status === 'completed') || [];

/**
 * Select running agents
 */
export const selectRunningAgents = (state: AgentTeamStore) =>
  state.agentTeamStatus?.agents.filter((w) => w.status === 'running') || [];

/**
 * Select failed agents
 */
export const selectFailedAgents = (state: AgentTeamStore) =>
  state.agentTeamStatus?.agents.filter((w) => w.status === 'failed') || [];

/**
 * Select if team is active
 */
export const selectIsTeamActive = (state: AgentTeamStore) =>
  state.agentTeamStatus?.status === 'executing';

export default useAgentTeamStore;
