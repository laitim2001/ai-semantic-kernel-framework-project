/**
 * useUnifiedChat - Unified Chat Orchestration Hook
 *
 * Sprint 63: Mode Switching & State Management
 * S63-1: useUnifiedChat Hook (8 pts)
 * Phase 16: Unified Agentic Chat Interface
 * Sprint 68: S68-5 - History Loading Integration
 *
 * Main orchestration hook that manages AG-UI connection, message handling,
 * and state coordination for the unified chat interface.
 *
 * Features:
 * - SSE connection lifecycle management
 * - AG-UI event handling (all 15 event types)
 * - Mode management integration with useHybridMode
 * - Zustand store synchronization
 * - STATE_SNAPSHOT/DELTA handling for shared state
 * - Optimistic updates support
 * - History loading from backend (Sprint 68)
 */

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import type {
  ChatMessage,
  ToolCallState,
  ToolCallStatus,
  PendingApproval,
  RiskLevel,
  AGUIEventType,
  ToolDefinition,
  MessageRole,
} from '@/types/ag-ui';
import type {
  ExecutionMode,
  WorkflowState,
  ConnectionStatus,
  TrackedToolCall,
  Checkpoint,
} from '@/types/unified-chat';
import { useUnifiedChatStore } from '@/stores/unifiedChatStore';
import { useHybridMode, dispatchModeDetection } from './useHybridMode';

// =============================================================================
// Types
// =============================================================================

/** useUnifiedChat Hook Options */
export interface UseUnifiedChatOptions {
  /** Thread ID for conversation isolation */
  threadId: string;
  /** Session ID (optional, defaults to threadId) */
  sessionId?: string;
  /** API base URL */
  apiUrl?: string;
  /** Initial messages */
  initialMessages?: ChatMessage[];
  /** Available tools */
  tools?: ToolDefinition[];
  /** Execution mode preference */
  modePreference?: ExecutionMode;
  /** Max tokens for LLM response */
  maxTokens?: number;
  /** Request timeout in ms */
  timeout?: number;
  /** Auto-reconnect on disconnect */
  autoReconnect?: boolean;
  /** Reconnect interval in ms */
  reconnectInterval?: number;
  /** Max reconnect attempts */
  maxReconnectAttempts?: number;
  /** S74-BF-1: Skip automatic history loading on threadId change (for localStorage-based persistence) */
  skipAutoLoadHistory?: boolean;
  /** Callback when message received */
  onMessage?: (message: ChatMessage) => void;
  /** Callback when tool call occurs */
  onToolCall?: (toolCall: ToolCallState) => void;
  /** Callback when approval required */
  onApprovalRequired?: (approval: PendingApproval) => void;
  /** Callback when run completes */
  onRunComplete?: (success: boolean, error?: string) => void;
  /** Callback on connection status change */
  onConnectionChange?: (status: ConnectionStatus) => void;
  /** Callback when mode changes */
  onModeChange?: (mode: ExecutionMode, source: 'auto' | 'manual') => void;
}

/** useUnifiedChat Hook Return Value */
export interface UseUnifiedChatReturn {
  // State
  messages: ChatMessage[];
  isConnected: boolean;
  isStreaming: boolean;
  error: Error | null;

  // Actions
  sendMessage: (content: string, fileIds?: string[]) => Promise<void>;
  cancelStream: () => void;
  clearMessages: () => void;
  setMessages: (messages: ChatMessage[]) => void;  // S74-BF-1: Allow external message setting
  reconnect: () => void;

  // Mode integration
  currentMode: ExecutionMode;
  autoMode: ExecutionMode;
  manualOverride: ExecutionMode | null;
  isManuallyOverridden: boolean;
  setManualOverride: (mode: ExecutionMode | null) => void;

  // Workflow state
  workflowState: WorkflowState | null;

  // Approvals
  pendingApprovals: PendingApproval[];
  dialogApproval: PendingApproval | null;
  approveToolCall: (approvalId: string, comment?: string) => Promise<boolean>;
  rejectToolCall: (approvalId: string, reason?: string) => Promise<boolean>;
  dismissDialog: () => void;
  /** Remove expired approval to allow new approvals for same tool */
  removeExpiredApproval: (approvalId: string) => void;

  // Tool calls
  toolCalls: TrackedToolCall[];

  // Checkpoints
  checkpoints: Checkpoint[];
  currentCheckpoint: string | null;

  // Metrics (basic)
  tokenUsage: { used: number; limit: number };

  // Shared state
  sharedState: Record<string, unknown>;
  updateSharedState: (path: string, value: unknown) => void;

  // Heartbeat (S67-BF-1)
  heartbeat: HeartbeatState | null;

  // History (S68-5)
  historyLoading: boolean;
  loadHistory: () => Promise<void>;
}

/** Heartbeat state for long-running operations (S67-BF-1) */
export interface HeartbeatState {
  count: number;
  elapsedSeconds: number;
  message: string;
  status: 'processing' | 'idle';
}

// =============================================================================
// Helpers
// =============================================================================

/** Generate unique message ID */
const generateMessageId = (): string => {
  return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

/** Generate unique run ID */
const generateRunId = (): string => {
  return `run_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

/** Parse SSE event data */
const parseSSEData = (data: string): Record<string, unknown> | null => {
  try {
    return JSON.parse(data);
  } catch {
    console.warn('[useUnifiedChat] Failed to parse SSE data:', data);
    return null;
  }
};

// =============================================================================
// Main Hook
// =============================================================================

/**
 * useUnifiedChat - Main Unified Chat Hook
 *
 * Provides complete unified chat functionality including:
 * - SSE connection management with auto-reconnect
 * - Message streaming and handling
 * - Tool call tracking
 * - HITL approval workflow
 * - Mode detection and management
 * - State synchronization (STATE_SNAPSHOT/DELTA)
 */
export function useUnifiedChat(options: UseUnifiedChatOptions): UseUnifiedChatReturn {
  const {
    threadId,
    sessionId = threadId,
    apiUrl = '/api/v1/ag-ui',
    initialMessages = [],
    tools = [],
    modePreference,
    maxTokens,
    timeout,
    autoReconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
    skipAutoLoadHistory = false,  // S74-BF-1
    onMessage,
    onToolCall,
    onApprovalRequired,
    onRunComplete,
    onConnectionChange,
    onModeChange,
  } = options;

  // ==========================================================================
  // Zustand Store Integration
  // ==========================================================================

  // Use selectors for stable action references (prevents infinite re-renders)
  const storeSetMode = useUnifiedChatStore((s) => s.setMode);
  const storeSetConnection = useUnifiedChatStore((s) => s.setConnection);
  const storeAddMessage = useUnifiedChatStore((s) => s.addMessage);
  const storeUpdateMessage = useUnifiedChatStore((s) => s.updateMessage);
  const storeSetMessages = useUnifiedChatStore((s) => s.setMessages);
  const storeClearMessages = useUnifiedChatStore((s) => s.clearMessages);
  const storeSetStreaming = useUnifiedChatStore((s) => s.setStreaming);
  const storeSetError = useUnifiedChatStore((s) => s.setError);
  const storeAddToolCall = useUnifiedChatStore((s) => s.addToolCall);
  const storeUpdateToolCall = useUnifiedChatStore((s) => s.updateToolCall);
  const storeAddPendingApproval = useUnifiedChatStore((s) => s.addPendingApproval);
  const storeRemovePendingApproval = useUnifiedChatStore((s) => s.removePendingApproval);
  const storeSetDialogApproval = useUnifiedChatStore((s) => s.setDialogApproval);
  const storeAddCheckpoint = useUnifiedChatStore((s) => s.addCheckpoint);
  const storeSetWorkflowState = useUnifiedChatStore((s) => s.setWorkflowState);

  // ==========================================================================
  // Mode Management (useHybridMode integration)
  // ==========================================================================

  const {
    currentMode,
    autoMode,
    manualOverride,
    isManuallyOverridden,
    setManualOverride,
  } = useHybridMode({
    initialMode: modePreference || 'chat',
    sessionId,
    onModeChange: (mode, source) => {
      storeSetMode(mode);
      onModeChange?.(mode, source);
    },
  });

  // ==========================================================================
  // Local State
  // ==========================================================================

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [toolCalls, setToolCalls] = useState<TrackedToolCall[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [dialogApproval, setDialogApproval] = useState<PendingApproval | null>(null);
  const [workflowState, setWorkflowState] = useState<WorkflowState | null>(null);
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [currentCheckpoint, setCurrentCheckpoint] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [tokenUsage, setTokenUsage] = useState({ used: 0, limit: 4000 });
  const [sharedState, setSharedState] = useState<Record<string, unknown>>({});
  const [stateVersion, setStateVersion] = useState(0);
  const [heartbeat, setHeartbeat] = useState<HeartbeatState | null>(null);  // S67-BF-1
  const [historyLoading, setHistoryLoading] = useState(false);  // S68-5

  // ==========================================================================
  // Refs
  // ==========================================================================

  const abortControllerRef = useRef<AbortController | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const currentMessageRef = useRef<ChatMessage | null>(null);
  const currentToolCallRef = useRef<TrackedToolCall | null>(null);

  // ==========================================================================
  // Computed Values
  // ==========================================================================

  const isConnected = useMemo(
    () => connectionStatus === 'connected',
    [connectionStatus]
  );

  // ==========================================================================
  // Connection Status Update
  // ==========================================================================

  const updateConnectionStatus = useCallback(
    (status: ConnectionStatus) => {
      setConnectionStatus(status);
      storeSetConnection(status);
      onConnectionChange?.(status);
    },
    [storeSetConnection, onConnectionChange]
  );

  // ==========================================================================
  // Message Management
  // ==========================================================================

  const addUserMessage = useCallback(
    (content: string): ChatMessage => {
      const message: ChatMessage = {
        id: generateMessageId(),
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, message]);
      storeAddMessage(message);
      onMessage?.(message);
      return message;
    },
    [storeAddMessage, onMessage]
  );

  const updateCurrentMessage = useCallback((delta: string) => {
    if (!currentMessageRef.current) {
      // Create new assistant message
      const newMessage: ChatMessage = {
        id: generateMessageId(),
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
      };
      currentMessageRef.current = newMessage;
      setMessages((prev) => [...prev, newMessage]);
      storeAddMessage(newMessage);
    }

    // Update content with delta
    currentMessageRef.current.content += delta;

    const messageId = currentMessageRef.current.id;
    const newContent = currentMessageRef.current.content;

    setMessages((prev) =>
      prev.map((m) =>
        m.id === messageId ? { ...m, content: newContent } : m
      )
    );
    storeUpdateMessage(messageId, { content: newContent });
  }, [storeUpdateMessage]);

  const finalizeCurrentMessage = useCallback(() => {
    if (currentMessageRef.current) {
      onMessage?.(currentMessageRef.current);
      currentMessageRef.current = null;
    }
  }, [onMessage]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setToolCalls([]);
    currentMessageRef.current = null;
    storeClearMessages();
  }, [storeClearMessages]);

  // ==========================================================================
  // Tool Call Management
  // ==========================================================================

  const startToolCall = useCallback(
    (toolCallId: string, name: string, args: Record<string, unknown> = {}) => {
      const toolCall: TrackedToolCall = {
        id: generateMessageId(),
        toolCallId,
        name,
        arguments: args,
        status: 'executing',
        startedAt: new Date().toISOString(),
        queuedAt: new Date().toISOString(),
      };

      currentToolCallRef.current = toolCall;
      setToolCalls((prev) => [...prev, toolCall]);
      storeAddToolCall(toolCall);
      onToolCall?.(toolCall);

      // AG-UI Fix: Also add tool call to current message for UI rendering
      if (currentMessageRef.current) {
        const toolCallState: ToolCallState = {
          id: toolCall.id,
          toolCallId: toolCall.toolCallId,
          name: toolCall.name,
          arguments: toolCall.arguments,
          status: toolCall.status,
          startedAt: toolCall.startedAt,
        };
        currentMessageRef.current.toolCalls = [
          ...(currentMessageRef.current.toolCalls || []),
          toolCallState,
        ];
        // Trigger re-render with updated message
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === currentMessageRef.current?.id
              ? { ...msg, toolCalls: currentMessageRef.current.toolCalls }
              : msg
          )
        );
      }
    },
    [storeAddToolCall, onToolCall]
  );

  const updateToolCallArgs = useCallback((args: Record<string, unknown>) => {
    if (!currentToolCallRef.current) return;

    currentToolCallRef.current.arguments = {
      ...currentToolCallRef.current.arguments,
      ...args,
    };

    const toolCallId = currentToolCallRef.current.toolCallId;
    const updatedArgs = currentToolCallRef.current.arguments;

    setToolCalls((prev) =>
      prev.map((tc) =>
        tc.toolCallId === toolCallId
          ? { ...tc, arguments: updatedArgs }
          : tc
      )
    );
    storeUpdateToolCall(toolCallId, { arguments: updatedArgs });

    // AG-UI Fix: Also update tool call args in messages for UI rendering
    setMessages((prev) =>
      prev.map((msg) => {
        if (msg.toolCalls?.some((tc) => tc.toolCallId === toolCallId)) {
          return {
            ...msg,
            toolCalls: msg.toolCalls.map((tc) =>
              tc.toolCallId === toolCallId
                ? { ...tc, arguments: updatedArgs }
                : tc
            ),
          };
        }
        return msg;
      })
    );
  }, [storeUpdateToolCall]);

  const completeToolCall = useCallback(
    (toolCallId: string, result: unknown, toolError?: string) => {
      const status: ToolCallStatus = toolError ? 'failed' : 'completed';
      const completedAt = new Date().toISOString();

      setToolCalls((prev) =>
        prev.map((tc) => {
          if (tc.toolCallId === toolCallId) {
            const duration = tc.startedAt
              ? new Date(completedAt).getTime() - new Date(tc.startedAt).getTime()
              : undefined;
            return { ...tc, status, result, error: toolError, completedAt, duration };
          }
          return tc;
        })
      );

      storeUpdateToolCall(toolCallId, { status, result, error: toolError, completedAt });

      // AG-UI Fix: Also update tool call status in messages for UI rendering
      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.toolCalls?.some((tc) => tc.toolCallId === toolCallId)) {
            return {
              ...msg,
              toolCalls: msg.toolCalls.map((tc) =>
                tc.toolCallId === toolCallId
                  ? { ...tc, status, result, error: toolError, completedAt }
                  : tc
              ),
            };
          }
          return msg;
        })
      );

      if (currentToolCallRef.current?.toolCallId === toolCallId) {
        const updated = {
          ...currentToolCallRef.current,
          status,
          result,
          error: toolError,
          completedAt,
        };
        onToolCall?.(updated);
        currentToolCallRef.current = null;
      }
    },
    [storeUpdateToolCall, onToolCall]
  );

  // ==========================================================================
  // Approval Management
  // ==========================================================================

  const addPendingApproval = useCallback(
    (approval: PendingApproval) => {
      setPendingApprovals((prev) => {
        if (prev.some((a) => a.approvalId === approval.approvalId)) return prev;
        return [...prev, approval];
      });
      storeAddPendingApproval(approval);
      onApprovalRequired?.(approval);

      // Sprint 99: No longer using dialog - approvals are shown inline via ApprovalMessageCard
      // This provides a more natural conversation flow experience

      // Update tool call status
      setToolCalls((prev) =>
        prev.map((tc) =>
          tc.toolCallId === approval.toolCallId
            ? { ...tc, status: 'requires_approval' }
            : tc
        )
      );
    },
    [storeAddPendingApproval, onApprovalRequired]
  );

  // Resolve approval - update status instead of removing (keeps history)
  const resolveApproval = useCallback((
    approvalId: string,
    status: 'approved' | 'rejected' | 'expired',
    rejectReason?: string
  ) => {
    setPendingApprovals((prev) =>
      prev.map((a) =>
        a.approvalId === approvalId
          ? {
              ...a,
              status,
              resolvedAt: new Date().toISOString(),
              rejectReason: rejectReason,
            }
          : a
      )
    );

    if (dialogApproval?.approvalId === approvalId) {
      setDialogApproval(null);
      storeSetDialogApproval(null);
    }
  }, [storeSetDialogApproval, dialogApproval]);

  // Remove expired approval completely (to allow new approvals)
  const removeExpiredApproval = useCallback((approvalId: string) => {
    setPendingApprovals((prev) =>
      prev.filter((a) => a.approvalId !== approvalId)
    );
    storeRemovePendingApproval(approvalId);
  }, [storeRemovePendingApproval]);

  const approveToolCall = useCallback(
    async (approvalId: string, comment?: string): Promise<boolean> => {
      try {
        const response = await fetch(`${apiUrl}/approvals/${approvalId}/approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ comment }),
        });

        if (!response.ok) {
          console.error('[useUnifiedChat] Approval failed:', await response.text());
          return false;
        }

        const result = await response.json();
        const approval = pendingApprovals.find((a) => a.approvalId === approvalId);

        if (approval) {
          setToolCalls((prev) =>
            prev.map((tc) =>
              tc.toolCallId === approval.toolCallId
                ? { ...tc, status: 'approved' }
                : tc
            )
          );
        }

        // Update status instead of removing - keeps history visible
        resolveApproval(approvalId, 'approved');
        return result.success;
      } catch (err) {
        console.error('[useUnifiedChat] Approval error:', err);
        return false;
      }
    },
    [apiUrl, pendingApprovals, resolveApproval]
  );

  const rejectToolCall = useCallback(
    async (approvalId: string, reason?: string): Promise<boolean> => {
      try {
        const response = await fetch(`${apiUrl}/approvals/${approvalId}/reject`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason }),
        });

        if (!response.ok) {
          console.error('[useUnifiedChat] Rejection failed:', await response.text());
          return false;
        }

        const result = await response.json();
        const approval = pendingApprovals.find((a) => a.approvalId === approvalId);

        if (approval) {
          setToolCalls((prev) =>
            prev.map((tc) =>
              tc.toolCallId === approval.toolCallId
                ? { ...tc, status: 'rejected' }
                : tc
            )
          );
        }

        // Update status instead of removing - keeps history visible
        resolveApproval(approvalId, 'rejected', reason);
        return result.success;
      } catch (err) {
        console.error('[useUnifiedChat] Rejection error:', err);
        return false;
      }
    },
    [apiUrl, pendingApprovals, resolveApproval]
  );

  const dismissDialog = useCallback(() => {
    setDialogApproval(null);
    storeSetDialogApproval(null);
  }, [storeSetDialogApproval]);

  // ==========================================================================
  // Shared State Management (STATE_SNAPSHOT/DELTA)
  // ==========================================================================

  const handleStateSnapshot = useCallback((snapshot: Record<string, unknown>, version: number) => {
    setSharedState(snapshot);
    setStateVersion(version);
    console.log(`[useUnifiedChat] State snapshot applied, version: ${version}`);
  }, []);

  const handleStateDelta = useCallback((delta: Record<string, unknown>, version: number, baseVersion: number) => {
    // Conflict detection
    if (baseVersion !== stateVersion) {
      console.warn(`[useUnifiedChat] State version conflict: expected ${baseVersion}, got ${stateVersion}`);
      // Request full snapshot on conflict - this would be handled by the backend
      return;
    }

    setSharedState((prev) => ({ ...prev, ...delta }));
    setStateVersion(version);
    console.log(`[useUnifiedChat] State delta applied, version: ${version}`);
  }, [stateVersion]);

  const updateSharedState = useCallback((path: string, value: unknown) => {
    setSharedState((prev) => {
      const keys = path.split('.');
      const result = { ...prev };
      let current = result as Record<string, unknown>;

      for (let i = 0; i < keys.length - 1; i++) {
        const key = keys[i];
        current[key] = { ...(current[key] as Record<string, unknown> || {}) };
        current = current[key] as Record<string, unknown>;
      }

      current[keys[keys.length - 1]] = value;
      return result;
    });
  }, []);

  // ==========================================================================
  // SSE Event Handler
  // ==========================================================================

  const handleSSEEvent = useCallback(
    (event: MessageEvent) => {
      const data = parseSSEData(event.data);
      if (!data) return;

      const eventType = data.type as AGUIEventType;

      switch (eventType) {
        case 'RUN_STARTED':
          setIsStreaming(true);
          storeSetStreaming(true);
          setError(null);
          setHeartbeat(null);  // S67-BF-1: Reset heartbeat on run start
          break;

        case 'RUN_FINISHED': {
          const success = data.finish_reason !== 'error';
          setIsStreaming(false);
          storeSetStreaming(false);
          setHeartbeat(null);  // S67-BF-1: Clear heartbeat on run finish
          finalizeCurrentMessage();
          onRunComplete?.(success, data.error as string | undefined);
          break;
        }

        case 'RUN_ERROR':
          setIsStreaming(false);
          storeSetStreaming(false);
          setError(new Error(data.error as string || 'Unknown error'));
          storeSetError(data.error as string || 'Unknown error');
          finalizeCurrentMessage();
          onRunComplete?.(false, data.error as string);
          break;

        case 'TEXT_MESSAGE_START': {
          const newMessage: ChatMessage = {
            id: (data.message_id as string) || generateMessageId(),
            role: (data.role as MessageRole) || 'assistant',
            content: '',
            timestamp: (data.timestamp as string) || new Date().toISOString(),
          };
          currentMessageRef.current = newMessage;
          setMessages((prev) => [...prev, newMessage]);
          storeAddMessage(newMessage);
          break;
        }

        case 'TEXT_MESSAGE_CONTENT':
          updateCurrentMessage((data.delta as string) || '');
          break;

        case 'TEXT_MESSAGE_END':
          finalizeCurrentMessage();
          break;

        case 'TOOL_CALL_START':
          startToolCall(
            data.tool_call_id as string,
            data.tool_name as string,
            {}
          );
          break;

        case 'TOOL_CALL_ARGS':
          updateToolCallArgs((data.args as Record<string, unknown>) || {});
          break;

        case 'TOOL_CALL_END':
          completeToolCall(
            data.tool_call_id as string,
            data.result,
            data.error as string | undefined
          );
          break;

        case 'STATE_SNAPSHOT':
          if (data.snapshot && typeof data.version === 'number') {
            handleStateSnapshot(
              data.snapshot as Record<string, unknown>,
              data.version as number
            );
          }
          break;

        case 'STATE_DELTA':
          if (data.delta && typeof data.version === 'number') {
            handleStateDelta(
              data.delta as Record<string, unknown>,
              data.version as number,
              (data.base_version as number) || stateVersion
            );
          }
          break;

        case 'CUSTOM': {
          const eventName = data.event_name as string;
          const payload = data.payload as Record<string, unknown>;

          // Handle MODE_DETECTED event
          if (eventName === 'MODE_DETECTED') {
            const mode = payload.mode as ExecutionMode;
            const confidence = payload.confidence as number;
            const reason = payload.reason as string | undefined;

            if (confidence >= 0.7) {
              dispatchModeDetection({
                mode,
                confidence,
                reason,
              });
            }
          }

          // Handle APPROVAL_REQUIRED event (backend sends lowercase 'approval_required')
          if (eventName === 'APPROVAL_REQUIRED' || eventName === 'approval_required') {
            addPendingApproval({
              approvalId: payload.approval_id as string,
              toolCallId: payload.tool_call_id as string,
              toolName: payload.tool_name as string,
              arguments: payload.arguments as Record<string, unknown>,
              riskLevel: payload.risk_level as RiskLevel,
              riskScore: payload.risk_score as number,
              reasoning: payload.reasoning as string,
              runId: payload.run_id as string,
              sessionId: payload.session_id as string,
              createdAt: payload.created_at as string,
              expiresAt: payload.expires_at as string,
            });
          }

          // Handle TOKEN_UPDATE event
          if (eventName === 'TOKEN_UPDATE') {
            setTokenUsage({
              used: payload.tokens_used as number || 0,
              limit: payload.tokens_limit as number || 4000,
            });
          }

          // Handle CHECKPOINT_CREATED event
          if (eventName === 'CHECKPOINT_CREATED') {
            const checkpoint: Checkpoint = {
              id: payload.checkpoint_id as string,
              timestamp: payload.timestamp as string,
              label: payload.label as string | undefined,
              canRestore: payload.can_restore as boolean ?? true,
              stepIndex: payload.step_index as number | undefined,
            };
            setCheckpoints((prev) => [...prev, checkpoint]);
            setCurrentCheckpoint(checkpoint.id);
            storeAddCheckpoint(checkpoint);
          }

          // Handle WORKFLOW_STATE event
          if (eventName === 'WORKFLOW_STATE') {
            const wfState = payload.workflow_state as WorkflowState;
            setWorkflowState(wfState);
            storeSetWorkflowState(wfState);
          }

          // S67-BF-1: Handle HEARTBEAT event
          if (eventName === 'heartbeat') {
            setHeartbeat({
              count: payload.count as number,
              elapsedSeconds: payload.elapsed_seconds as number,
              message: payload.message as string,
              status: payload.status as 'processing' | 'idle',
            });
          }

          // AG-UI #4/#5: Handle UI_COMPONENT event (Generative UI / Tool-based UI)
          if (eventName === 'ui_component') {
            const component = payload.component as Record<string, unknown>;
            const action = payload.action as string;

            // Support both 'create'/'render' for new components, 'update' for modifications
            if (action === 'create' || action === 'render' || action === 'update') {
              // Create a new message with the UI component
              const uiMessage: ChatMessage = {
                id: generateMessageId(),
                role: 'assistant',
                content: '', // Empty content - UI component will be rendered instead
                timestamp: new Date().toISOString(),
                customUI: {
                  componentId: component.component_id as string,
                  componentType: component.component_type as 'form' | 'chart' | 'card' | 'table' | 'custom',
                  props: component.props as Record<string, unknown>,
                  title: component.title as string | undefined,
                  description: component.description as string | undefined,
                  createdAt: component.created_at as string || new Date().toISOString(),
                },
              };
              setMessages((prev) => [...prev, uiMessage]);
              storeAddMessage(uiMessage);
              onMessage?.(uiMessage);
            }
          }

          // AG-UI #7: Handle PREDICTION events (Predictive Updates)
          if (eventName === 'prediction_confirmed') {
            console.log('[useUnifiedChat] Prediction confirmed:', payload.prediction_id);
            // Update optimistic state to confirmed
          }

          if (eventName === 'prediction_rolled_back') {
            console.log('[useUnifiedChat] Prediction rolled back:', payload.prediction_id);
            // Rollback optimistic state
          }

          if (eventName === 'prediction_conflicted') {
            console.log('[useUnifiedChat] Prediction conflicted:', payload.prediction_id, payload.reason);
            // Handle conflict - show indicator to user
          }

          // Workflow Mode: Handle STEP_PROGRESS event
          if (eventName === 'step_progress') {
            const stepProgress = {
              stepId: payload.step_id as string,
              stepName: payload.step_name as string,
              current: payload.current as number,
              total: payload.total as number,
              progress: payload.progress as number,
              status: payload.status as string,
            };
            console.log('[useUnifiedChat] Step progress:', stepProgress);
            // Update workflow state with step progress
            if (workflowState) {
              setWorkflowState((prev) => {
                if (!prev) return prev;
                const updatedSteps = prev.steps.map((step) =>
                  step.id === stepProgress.stepId
                    ? { ...step, status: stepProgress.status as 'pending' | 'running' | 'completed' | 'failed' | 'skipped' }
                    : step
                );
                return {
                  ...prev,
                  steps: updatedSteps,
                  progress: stepProgress.progress,
                };
              });
            }
          }
          break;
        }

        default:
          console.log('[useUnifiedChat] Unhandled SSE event:', eventType, data);
      }
    },
    [
      storeSetStreaming,
      storeSetError,
      storeAddMessage,
      storeAddCheckpoint,
      storeSetWorkflowState,
      finalizeCurrentMessage,
      updateCurrentMessage,
      startToolCall,
      updateToolCallArgs,
      completeToolCall,
      addPendingApproval,
      handleStateSnapshot,
      handleStateDelta,
      stateVersion,
      onRunComplete,
      onMessage,
      workflowState,
    ]
  );

  // ==========================================================================
  // Send Message / Run Agent
  // ==========================================================================

  const sendMessage = useCallback(
    async (content: string, fileIds?: string[]): Promise<void> => {
      // Cancel any existing run
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Reset error state
      setError(null);
      storeSetError(null);

      // Add user message
      const userMessage = addUserMessage(content);

      // Create abort controller
      abortControllerRef.current = new AbortController();

      // Build request payload
      const messagesPayload = messages
        .concat([userMessage])
        .map((m) => ({
          role: m.role,
          content: m.content,
        }));

      // S75-5: Build attachments payload from file IDs
      const attachmentsPayload = fileIds?.map((id) => ({
        file_id: id,
        type: 'file',
      }));

      const payload = {
        thread_id: threadId,
        run_id: generateRunId(),
        session_id: sessionId,
        mode: currentMode,
        messages: messagesPayload,
        tools: tools.map((t) => ({
          name: t.name,
          description: t.description,
          parameters: t.parameters,
        })),
        max_tokens: maxTokens,
        timeout,
        // S75-5: Include attachments in payload
        ...(attachmentsPayload && attachmentsPayload.length > 0 && { attachments: attachmentsPayload }),
      };

      // S75-5: Debug log for payload
      if (attachmentsPayload && attachmentsPayload.length > 0) {
        console.log('[S75-5] Sending message with attachments:', attachmentsPayload);
      }

      try {
        setIsStreaming(true);
        storeSetStreaming(true);

        const response = await fetch(apiUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'text/event-stream',
          },
          body: JSON.stringify(payload),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No response body');
        }

        const decoder = new TextDecoder();
        let buffer = '';

        updateConnectionStatus('connected');
        reconnectAttemptsRef.current = 0;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const eventData = line.slice(6);
              if (eventData) {
                handleSSEEvent({ data: eventData } as MessageEvent);
              }
            }
          }
        }
      } catch (err) {
        if ((err as Error).name === 'AbortError') {
          // Request was cancelled
          setIsStreaming(false);
          storeSetStreaming(false);
        } else {
          console.error('[useUnifiedChat] Send message error:', err);
          setError(err as Error);
          storeSetError((err as Error).message);
          setIsStreaming(false);
          storeSetStreaming(false);
          onRunComplete?.(false, (err as Error).message);

          // Attempt reconnect if enabled
          if (autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
            scheduleReconnect();
          }
        }
      } finally {
        abortControllerRef.current = null;
      }
    },
    [
      storeSetError,
      storeSetStreaming,
      threadId,
      sessionId,
      currentMode,
      messages,
      tools,
      maxTokens,
      timeout,
      apiUrl,
      addUserMessage,
      handleSSEEvent,
      updateConnectionStatus,
      autoReconnect,
      maxReconnectAttempts,
      onRunComplete,
    ]
  );

  // ==========================================================================
  // Cancel Stream
  // ==========================================================================

  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    storeSetStreaming(false);
    finalizeCurrentMessage();
  }, [storeSetStreaming, finalizeCurrentMessage]);

  // ==========================================================================
  // Reconnection Logic
  // ==========================================================================

  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    const backoffMs = Math.min(
      reconnectInterval * Math.pow(2, reconnectAttemptsRef.current),
      30000
    );

    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectAttemptsRef.current++;
      updateConnectionStatus('connecting');
      console.log(`[useUnifiedChat] Reconnect attempt ${reconnectAttemptsRef.current}`);
    }, backoffMs);
  }, [reconnectInterval, updateConnectionStatus]);

  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    updateConnectionStatus('connecting');
  }, [updateConnectionStatus]);

  // ==========================================================================
  // History Loading (Sprint 68: S68-5)
  // ==========================================================================

  /**
   * Load conversation history from backend.
   *
   * Fetches messages from the history API and replaces local state.
   * Backend is the source of truth; localStorage is used only as fallback.
   */
  const loadHistory = useCallback(async () => {
    if (!threadId) return;

    setHistoryLoading(true);
    try {
      // Build history URL with Guest ID header
      const guestId = localStorage.getItem('ipa_guest_user_id');

      const response = await fetch(`${apiUrl}/threads/${threadId}/history`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(guestId ? { 'X-Guest-Id': guestId } : {}),
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          // Thread not found - new conversation, nothing to load
          console.log('[useUnifiedChat] New thread, no history to load');
          return;
        }
        throw new Error(`Failed to load history: ${response.statusText}`);
      }

      const data = await response.json();

      // Convert API response to ChatMessage format
      if (data.messages && Array.isArray(data.messages)) {
        const historyMessages: ChatMessage[] = data.messages.map((msg: {
          id: string;
          role: MessageRole;
          content: string;
          tool_calls?: ToolCallState[];
          approval_state?: string;
          created_at: string;
        }) => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          toolCalls: msg.tool_calls || [],
          timestamp: msg.created_at,
          metadata: msg.approval_state ? { approvalState: msg.approval_state } : undefined,
        }));

        // Replace local messages with backend history
        setMessages(historyMessages);
        storeSetMessages(historyMessages);
        console.log(`[useUnifiedChat] Loaded ${historyMessages.length} messages from history`);
      }
    } catch (err) {
      console.error('[useUnifiedChat] Failed to load history:', err);
      // Non-critical - keep local messages if any, or start fresh
    } finally {
      setHistoryLoading(false);
    }
  }, [threadId, apiUrl, storeSetMessages]);

  // Load history on mount when threadId is available
  // S74-BF-1: Skip if using localStorage-based persistence
  useEffect(() => {
    if (threadId && !skipAutoLoadHistory) {
      loadHistory();
    }
  }, [threadId, loadHistory, skipAutoLoadHistory]);

  // ==========================================================================
  // Cleanup on Unmount
  // ==========================================================================

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  // ==========================================================================
  // Initialize store with thread/session IDs
  // ==========================================================================

  useEffect(() => {
    // Sync thread/session IDs to store if needed
    // This is handled by the parent component typically
  }, [threadId, sessionId]);

  // ==========================================================================
  // Return
  // ==========================================================================

  // S74-BF-1: Allow external message setting (for thread switching)
  const setMessagesExternal = useCallback((newMessages: ChatMessage[]) => {
    setMessages(newMessages);
    storeSetMessages(newMessages);
  }, [storeSetMessages]);

  return {
    // State
    messages,
    isConnected,
    isStreaming,
    error,

    // Actions
    sendMessage,
    cancelStream,
    clearMessages,
    setMessages: setMessagesExternal,  // S74-BF-1
    reconnect,

    // Mode integration
    currentMode,
    autoMode,
    manualOverride,
    isManuallyOverridden,
    setManualOverride,

    // Workflow state
    workflowState,

    // Approvals
    pendingApprovals,
    dialogApproval,
    approveToolCall,
    rejectToolCall,
    dismissDialog,
    removeExpiredApproval,

    // Tool calls
    toolCalls,

    // Checkpoints
    checkpoints,
    currentCheckpoint,

    // Metrics
    tokenUsage,

    // Shared state
    sharedState,
    updateSharedState,

    // Heartbeat (S67-BF-1)
    heartbeat,

    // History (S68-5)
    historyLoading,
    loadHistory,
  };
}

export default useUnifiedChat;
