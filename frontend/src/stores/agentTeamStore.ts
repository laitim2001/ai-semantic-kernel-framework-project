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
  TeamMessagePayload,
  AgentApprovalRequiredPayload,
  AgentEvent,
  AgentEventType,
} from '@/components/unified-chat/agent-team/types';

// =============================================================================
// Types
// =============================================================================

/** Per-agent accumulated data from SSE events */
interface AgentAccumulatedData {
  thinkingHistory: ThinkingContent[];
  toolCalls: ToolCallInfo[];
  output: string;
}

/** Inter-agent team message (Phase 45: Sprint D) */
export interface TeamMessage {
  id: string;
  fromAgent: string;
  toAgent?: string | null;
  content: string;
  directed: boolean;
  timestamp: string;
}

/** Pending per-tool HITL approval (Phase 45: Sprint D) */
export interface PendingTeamApproval {
  approvalId: string;
  agentName: string;
  toolName: string;
  riskLevel: string;
  message: string;
  arguments?: Record<string, unknown>;
  timestamp: string;
}

interface AgentTeamState {
  // Core state
  agentTeamStatus: UIAgentTeamStatus | null;
  selectedAgentId: string | null;
  selectedAgentDetail: AgentDetail | null;
  isDrawerOpen: boolean;
  isLoading: boolean;
  error: string | null;
  // Accumulated data per agent (built from SSE events)
  agentDataMap: Record<string, AgentAccumulatedData>;
  // Inter-agent communication (Phase 45: Sprint D)
  teamMessages: TeamMessage[];
  // Per-tool HITL approvals (Phase 45: Sprint D)
  pendingApprovals: PendingTeamApproval[];
  // Unified conversation log (Phase 45: Sprint E)
  agentEvents: AgentEvent[];
  // Selected route from LLM routing (direct_answer / subagent / team)
  routeType: string | null;
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

  // Inter-agent communication actions (Phase 45: Sprint D)
  addTeamMessage: (payload: TeamMessagePayload) => void;
  addPendingApproval: (payload: AgentApprovalRequiredPayload) => void;
  removePendingApproval: (approvalId: string) => void;

  // Route type action
  setRouteType: (route: string) => void;

  // Conversation log actions (Phase 45: Sprint E)
  addAgentEvent: (type: AgentEventType, agentId: string, agentName: string, content: string, metadata?: Record<string, unknown>) => void;

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
  agentDataMap: {},
  teamMessages: [],
  pendingApprovals: [],
  agentEvents: [],
  routeType: null,
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
            // Accumulate in agentDataMap
            if (!state.agentDataMap[payload.agent_id]) {
              state.agentDataMap[payload.agent_id] = { thinkingHistory: [], toolCalls: [], output: '' };
            }
            const accum = state.agentDataMap[payload.agent_id];
            const newThinking: ThinkingContent = {
              content: payload.thinking_content,
              timestamp: payload.timestamp,
              tokenCount: payload.token_count || undefined,
            };
            const lastThinking = accum.thinkingHistory[accum.thinkingHistory.length - 1];
            if (lastThinking && payload.thinking_content.startsWith(lastThinking.content)) {
              accum.thinkingHistory[accum.thinkingHistory.length - 1] = newThinking;
            } else {
              accum.thinkingHistory.push(newThinking);
            }

            // Also update selectedAgentDetail if it matches
            if (state.selectedAgentDetail?.agentId === payload.agent_id) {
              state.selectedAgentDetail.thinkingHistory = [...accum.thinkingHistory];
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
            const agentIndex = state.agentTeamStatus.agents.findIndex(
              (w: UIAgentSummary) => w.agentId === payload.agent_id
            );
            if (agentIndex !== -1 && payload.status === 'running') {
              state.agentTeamStatus.agents[agentIndex].toolCallsCount += 1;
            }

            // Accumulate in agentDataMap
            if (!state.agentDataMap[payload.agent_id]) {
              state.agentDataMap[payload.agent_id] = { thinkingHistory: [], toolCalls: [], output: '' };
            }
            const accum = state.agentDataMap[payload.agent_id];
            const updatedToolCall: ToolCallInfo = {
              toolCallId: payload.tool_call_id,
              toolName: payload.tool_name,
              status: payload.status,
              inputArgs: payload.input_args,
              outputResult: payload.output_result || undefined,
              error: payload.error || undefined,
              durationMs: payload.duration_ms || undefined,
            };
            const existingIndex = accum.toolCalls.findIndex(
              (t: ToolCallInfo) => t.toolCallId === payload.tool_call_id
            );
            if (existingIndex !== -1) {
              accum.toolCalls[existingIndex] = updatedToolCall;
            } else {
              accum.toolCalls.push(updatedToolCall);
            }

            // Also update selectedAgentDetail if it matches
            if (state.selectedAgentDetail?.agentId === payload.agent_id) {
              state.selectedAgentDetail.toolCalls = [...accum.toolCalls];
            }
          },
          false,
          'updateAgentToolCall'
        ),

      completeAgent: (payload) =>
        set(
          (state) => {
            if (!state.agentTeamStatus) return;

            const agentIndex = state.agentTeamStatus.agents.findIndex(
              (w: UIAgentSummary) => w.agentId === payload.agent_id
            );
            if (agentIndex !== -1) {
              state.agentTeamStatus.agents[agentIndex].status = payload.status;
              state.agentTeamStatus.agents[agentIndex].progress = 100;
              state.agentTeamStatus.agents[agentIndex].completedAt = payload.completed_at;
            }

            // Accumulate output in agentDataMap
            if (!state.agentDataMap[payload.agent_id]) {
              state.agentDataMap[payload.agent_id] = { thinkingHistory: [], toolCalls: [], output: '' };
            }

            // Also update selectedAgentDetail if it matches
            if (state.selectedAgentDetail?.agentId === payload.agent_id) {
              state.selectedAgentDetail.status = payload.status;
              state.selectedAgentDetail.progress = 100;
              state.selectedAgentDetail.completedAt = payload.completed_at;
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
      // Route Type Action
      // =====================================================================

      setRouteType: (route) =>
        set(
          (state) => {
            state.routeType = route;
          },
          false,
          'setRouteType'
        ),

      // =====================================================================
      // Conversation Log Actions (Phase 45: Sprint E)
      // =====================================================================

      addAgentEvent: (type, agentId, agentName, content, metadata) =>
        set(
          (state) => {
            const event: AgentEvent = {
              id: `evt-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
              type,
              agentId,
              agentName,
              content,
              timestamp: new Date().toISOString(),
              metadata,
            };
            state.agentEvents.push(event);
            // Cap at 500 events to prevent memory bloat
            if (state.agentEvents.length > 500) {
              state.agentEvents = state.agentEvents.slice(-400);
            }
          },
          false,
          'addAgentEvent'
        ),

      // =====================================================================
      // Inter-Agent Communication Actions (Phase 45: Sprint D)
      // =====================================================================

      addTeamMessage: (payload) =>
        set(
          (state) => {
            const msg: TeamMessage = {
              id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
              fromAgent: payload.from_agent,
              toAgent: payload.to_agent,
              content: payload.content,
              directed: payload.directed,
              timestamp: new Date().toISOString(),
            };
            state.teamMessages.push(msg);
          },
          false,
          'addTeamMessage'
        ),

      addPendingApproval: (payload) =>
        set(
          (state) => {
            const approval: PendingTeamApproval = {
              approvalId: payload.approval_id,
              agentName: payload.agent_name,
              toolName: payload.tool_name,
              riskLevel: payload.risk_level,
              message: payload.message,
              arguments: payload.arguments,
              timestamp: new Date().toISOString(),
            };
            state.pendingApprovals.push(approval);
          },
          false,
          'addPendingApproval'
        ),

      removePendingApproval: (approvalId) =>
        set(
          (state) => {
            state.pendingApprovals = state.pendingApprovals.filter(
              (a) => a.approvalId !== approvalId
            );
          },
          false,
          'removePendingApproval'
        ),

      // =====================================================================
      // UI Actions
      // =====================================================================

      selectAgent: (agent) =>
        set(
          (state) => {
            state.selectedAgentId = agent?.agentId || null;
            if (agent) {
              // Build AgentDetail from accumulated SSE data
              const accum = state.agentDataMap[agent.agentId] || {
                thinkingHistory: [], toolCalls: [], output: '',
              };
              state.selectedAgentDetail = {
                ...agent,
                taskId: state.agentTeamStatus?.teamId || '',
                taskDescription: agent.role,
                thinkingHistory: [...accum.thinkingHistory],
                toolCalls: [...accum.toolCalls],
                messages: [],
                result: accum.output ? { output: accum.output } : undefined,
              };
              state.isDrawerOpen = true;
            } else {
              state.selectedAgentDetail = null;
              state.isDrawerOpen = false;
            }
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

/**
 * Select team messages
 */
export const selectTeamMessages = (state: AgentTeamStore) => state.teamMessages;

/**
 * Select pending approvals
 */
export const selectPendingApprovals = (state: AgentTeamStore) => state.pendingApprovals;

/**
 * Select agent events (conversation log)
 */
export const selectAgentEvents = (state: AgentTeamStore) => state.agentEvents;

export default useAgentTeamStore;
