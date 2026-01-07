/**
 * Unified Chat Store - Zustand State Management
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * S62-2: Adaptive Layout Logic
 * Phase 16: Unified Agentic Chat Interface
 *
 * Central state store for the unified chat interface.
 * Manages mode, messages, workflow state, approvals, and metrics.
 */

import { create } from 'zustand';
import { devtools, persist, createJSONStorage } from 'zustand/middleware';
import type {
  UnifiedChatState,
  UnifiedChatActions,
  ExecutionMode,
  ConnectionStatus,
  ExecutionMetrics,
  WorkflowState,
  WorkflowStepStatus,
  TrackedToolCall,
  Checkpoint,
} from '@/types/unified-chat';
import type { ChatMessage, PendingApproval } from '@/types/ag-ui';

// Initial metrics state
const initialMetrics: ExecutionMetrics = {
  tokens: { used: 0, limit: 4000, percentage: 0 },
  time: { total: 0, isRunning: false },
  toolCallCount: 0,
  messageCount: 0,
};

// Initial state
const initialState: UnifiedChatState = {
  // Core identifiers
  threadId: '',
  sessionId: '',

  // Mode management
  mode: 'chat',
  autoMode: 'chat',
  manualOverride: null,

  // Messages
  messages: [],
  isStreaming: false,
  streamingMessageId: null,

  // Workflow
  workflowState: null,

  // Tool calls
  toolCalls: [],

  // Approvals
  pendingApprovals: [],
  dialogApproval: null,

  // Checkpoints
  checkpoints: [],
  currentCheckpoint: null,

  // Metrics
  metrics: initialMetrics,

  // Connection
  connection: 'disconnected',

  // Error
  error: null,
};

// Helper to generate simple IDs
const generateId = () => `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;

/**
 * Unified Chat Store
 *
 * Combines state and actions for the unified chat interface.
 * Uses Zustand with devtools for debugging and partial persistence.
 */
export const useUnifiedChatStore = create<UnifiedChatState & UnifiedChatActions>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        ...initialState,

        // =====================================================================
        // Mode Management Actions
        // =====================================================================

        setMode: (mode: ExecutionMode) => {
          set({ mode }, false, 'setMode');
        },

        setManualOverride: (override: ExecutionMode | null) => {
          set(
            {
              manualOverride: override,
              mode: override ?? get().autoMode,
            },
            false,
            'setManualOverride'
          );
        },

        setAutoMode: (autoMode: ExecutionMode) => {
          const state = get();
          set(
            {
              autoMode,
              // Only update effective mode if no manual override
              mode: state.manualOverride ?? autoMode,
            },
            false,
            'setAutoMode'
          );
        },

        // =====================================================================
        // Message Actions
        // =====================================================================

        addMessage: (message: ChatMessage) => {
          set(
            (state) => ({
              messages: [...state.messages, message],
              metrics: {
                ...state.metrics,
                messageCount: state.metrics.messageCount + 1,
              },
            }),
            false,
            'addMessage'
          );
        },

        updateMessage: (id: string, content: Partial<ChatMessage>) => {
          set(
            (state) => ({
              messages: state.messages.map((msg) =>
                msg.id === id ? { ...msg, ...content } : msg
              ),
            }),
            false,
            'updateMessage'
          );
        },

        setStreaming: (isStreaming: boolean, messageId?: string) => {
          set(
            {
              isStreaming,
              streamingMessageId: isStreaming ? (messageId ?? null) : null,
            },
            false,
            'setStreaming'
          );
        },

        clearMessages: () => {
          set(
            {
              messages: [],
              metrics: {
                ...initialMetrics,
              },
            },
            false,
            'clearMessages'
          );
        },

        // =====================================================================
        // Workflow Actions
        // =====================================================================

        setWorkflowState: (workflowState: WorkflowState | null) => {
          set({ workflowState }, false, 'setWorkflowState');
        },

        updateWorkflowStep: (stepId: string, status: WorkflowStepStatus) => {
          set(
            (state) => {
              if (!state.workflowState) return state;

              const updatedSteps = state.workflowState.steps.map((step) =>
                step.id === stepId
                  ? {
                      ...step,
                      status,
                      ...(status === 'running' && { startedAt: new Date().toISOString() }),
                      ...(status === 'completed' && { completedAt: new Date().toISOString() }),
                    }
                  : step
              );

              // Calculate new progress
              const completedSteps = updatedSteps.filter(
                (s) => s.status === 'completed' || s.status === 'skipped'
              ).length;
              const progress = (completedSteps / updatedSteps.length) * 100;

              return {
                workflowState: {
                  ...state.workflowState,
                  steps: updatedSteps,
                  progress,
                },
              };
            },
            false,
            'updateWorkflowStep'
          );
        },

        // =====================================================================
        // Tool Call Actions
        // =====================================================================

        addToolCall: (toolCall: TrackedToolCall) => {
          set(
            (state) => ({
              toolCalls: [...state.toolCalls, toolCall],
              metrics: {
                ...state.metrics,
                toolCallCount: state.metrics.toolCallCount + 1,
              },
            }),
            false,
            'addToolCall'
          );
        },

        updateToolCall: (id: string, update: Partial<TrackedToolCall>) => {
          set(
            (state) => ({
              toolCalls: state.toolCalls.map((tc) =>
                tc.id === id || tc.toolCallId === id ? { ...tc, ...update } : tc
              ),
            }),
            false,
            'updateToolCall'
          );
        },

        // =====================================================================
        // Approval Actions
        // =====================================================================

        addPendingApproval: (approval: PendingApproval) => {
          set(
            (state) => {
              // Check if already exists
              const exists = state.pendingApprovals.some(
                (a) => a.approvalId === approval.approvalId
              );
              if (exists) return state;

              // Auto-show dialog for high/critical risk
              const showDialog =
                approval.riskLevel === 'high' || approval.riskLevel === 'critical';

              return {
                pendingApprovals: [...state.pendingApprovals, approval],
                dialogApproval: showDialog ? approval : state.dialogApproval,
              };
            },
            false,
            'addPendingApproval'
          );
        },

        removePendingApproval: (approvalId: string) => {
          set(
            (state) => ({
              pendingApprovals: state.pendingApprovals.filter(
                (a) => a.approvalId !== approvalId
              ),
              // Clear dialog if it was showing this approval
              dialogApproval:
                state.dialogApproval?.approvalId === approvalId
                  ? null
                  : state.dialogApproval,
            }),
            false,
            'removePendingApproval'
          );
        },

        setDialogApproval: (approval: PendingApproval | null) => {
          set({ dialogApproval: approval }, false, 'setDialogApproval');
        },

        // =====================================================================
        // Checkpoint Actions
        // =====================================================================

        addCheckpoint: (checkpoint: Checkpoint) => {
          set(
            (state) => ({
              checkpoints: [...state.checkpoints, checkpoint],
              currentCheckpoint: checkpoint.id,
            }),
            false,
            'addCheckpoint'
          );
        },

        setCurrentCheckpoint: (id: string | null) => {
          set({ currentCheckpoint: id }, false, 'setCurrentCheckpoint');
        },

        // =====================================================================
        // Metrics Actions
        // =====================================================================

        updateMetrics: (updates: Partial<ExecutionMetrics>) => {
          set(
            (state) => ({
              metrics: {
                ...state.metrics,
                ...updates,
                tokens: updates.tokens
                  ? { ...state.metrics.tokens, ...updates.tokens }
                  : state.metrics.tokens,
                time: updates.time
                  ? { ...state.metrics.time, ...updates.time }
                  : state.metrics.time,
              },
            }),
            false,
            'updateMetrics'
          );
        },

        // =====================================================================
        // Connection Actions
        // =====================================================================

        setConnection: (status: ConnectionStatus) => {
          set({ connection: status }, false, 'setConnection');
        },

        // =====================================================================
        // Error Actions
        // =====================================================================

        setError: (error: string | null) => {
          set({ error }, false, 'setError');
        },

        // =====================================================================
        // Reset Action
        // =====================================================================

        reset: () => {
          set(
            {
              ...initialState,
              threadId: generateId(),
              sessionId: generateId(),
            },
            false,
            'reset'
          );
        },
      }),
      {
        name: 'unified-chat-storage',
        storage: createJSONStorage(() => sessionStorage),
        // Only persist certain state
        partialize: (state) => ({
          threadId: state.threadId,
          sessionId: state.sessionId,
          mode: state.mode,
          manualOverride: state.manualOverride,
        }),
      }
    ),
    { name: 'UnifiedChatStore' }
  )
);

/**
 * Initialize store with thread and session IDs
 */
export function initializeUnifiedChat(threadId?: string, sessionId?: string) {
  useUnifiedChatStore.setState({
    threadId: threadId || generateId(),
    sessionId: sessionId || generateId(),
  });
}

/**
 * Selectors for common state access patterns
 */
export const selectMode = (state: UnifiedChatState) => state.mode;
export const selectMessages = (state: UnifiedChatState) => state.messages;
export const selectIsStreaming = (state: UnifiedChatState) => state.isStreaming;
export const selectPendingApprovals = (state: UnifiedChatState) => state.pendingApprovals;
export const selectWorkflowState = (state: UnifiedChatState) => state.workflowState;
export const selectMetrics = (state: UnifiedChatState) => state.metrics;
export const selectConnection = (state: UnifiedChatState) => state.connection;

export default useUnifiedChatStore;
