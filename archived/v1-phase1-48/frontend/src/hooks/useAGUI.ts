/**
 * useAGUI - AG-UI Protocol Main Hook
 *
 * Sprint 60+: AG-UI Protocol Integration
 *
 * Unified React hook for AG-UI protocol functionality.
 * Manages SSE connection, messages, tool calls, approvals,
 * and integrates with useSharedState and useOptimisticState.
 */

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import type {
  AGUIEventType,
  ChatMessage,
  ToolCallState,
  ToolCallStatus,
  PendingApproval,
  RunAgentInput,
  ToolDefinition,
  SSEConnectionStatus,
  AGUIRunState,
  MessageRole,
  RiskLevel,
} from '@/types/ag-ui';
import { useSharedState, UseSharedStateReturn, UseSharedStateOptions } from './useSharedState';
import { useOptimisticState, UseOptimisticStateReturn, UseOptimisticStateOptions } from './useOptimisticState';

// =============================================================================
// Types
// =============================================================================

/** useAGUI Hook Options */
export interface UseAGUIOptions {
  /** Thread ID for conversation isolation */
  threadId: string;
  /** Session ID (optional, defaults to threadId) */
  sessionId?: string;
  /** API base URL */
  apiUrl?: string;
  /** SSE endpoint URL */
  sseEndpoint?: string;
  /** Approval API endpoint */
  approvalApiUrl?: string;
  /** Initial messages */
  initialMessages?: ChatMessage[];
  /** Available tools */
  tools?: ToolDefinition[];
  /** Execution mode */
  mode?: 'auto' | 'workflow' | 'chat' | 'hybrid';
  /** Max tokens for LLM response */
  maxTokens?: number;
  /** Request timeout in ms */
  timeout?: number;
  /** Shared state options */
  sharedStateOptions?: Partial<UseSharedStateOptions>;
  /** Optimistic state options */
  optimisticStateOptions?: Partial<UseOptimisticStateOptions>;
  /** Auto-reconnect on disconnect */
  autoReconnect?: boolean;
  /** Reconnect interval in ms */
  reconnectInterval?: number;
  /** Callback when message received */
  onMessage?: (message: ChatMessage) => void;
  /** Callback when tool call occurs */
  onToolCall?: (toolCall: ToolCallState) => void;
  /** Callback when approval required */
  onApprovalRequired?: (approval: PendingApproval) => void;
  /** Callback when run completes */
  onRunComplete?: (success: boolean, error?: string) => void;
  /** Callback on connection status change */
  onConnectionChange?: (status: SSEConnectionStatus) => void;
}

/** Heartbeat state for long-running operations (S67-BF-1) */
export interface HeartbeatState {
  count: number;
  elapsedSeconds: number;
  message: string;
  status: 'processing' | 'idle';
}

/** Sub-step status type (S69-3) */
export type SubStepStatusType = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';

/** Sub-step within a main step (S69-3) */
export interface SubStep {
  id: string;
  name: string;
  status: SubStepStatusType;
  progress?: number;
  message?: string;
  startedAt?: string;
  completedAt?: string;
}

/** Step progress event from backend (S69-3) */
export interface StepProgressEvent {
  stepId: string;
  stepName: string;
  current: number;
  total: number;
  progress: number;
  status: SubStepStatusType;
  substeps: SubStep[];
  metadata?: Record<string, unknown>;
}

/** Step progress state for tracking multiple steps (S69-3) */
export interface StepProgressState {
  steps: Map<string, StepProgressEvent>;
  currentStep: string | null;
}

/** useAGUI Hook Return Value */
export interface UseAGUIReturn {
  // Connection state
  connectionStatus: SSEConnectionStatus;
  isConnected: boolean;
  isStreaming: boolean;

  // Run state
  runState: AGUIRunState;
  isRunning: boolean;

  // Heartbeat state (S67-BF-1)
  heartbeat: HeartbeatState | null;

  // Step progress state (S69-3)
  stepProgress: StepProgressState;
  currentStepProgress: StepProgressEvent | null;

  // Messages
  messages: ChatMessage[];
  addUserMessage: (content: string) => ChatMessage;
  addAssistantMessage: (content: string, toolCalls?: ToolCallState[]) => ChatMessage;
  clearMessages: () => void;

  // Tool calls
  toolCalls: ToolCallState[];
  getToolCall: (id: string) => ToolCallState | undefined;

  // Approvals
  pendingApprovals: PendingApproval[];
  approveToolCall: (approvalId: string, comment?: string) => Promise<boolean>;
  rejectToolCall: (approvalId: string, comment?: string) => Promise<boolean>;

  // Execution control
  runAgent: (input?: Partial<RunAgentInput>) => Promise<void>;
  cancelRun: () => void;

  // State integration
  sharedState: UseSharedStateReturn;
  optimisticState: UseOptimisticStateReturn;

  // Reconnection
  reconnect: () => void;
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
    console.warn('Failed to parse SSE data:', data);
    return null;
  }
};

// =============================================================================
// Main Hook
// =============================================================================

/**
 * useAGUI - Main AG-UI Protocol Hook
 *
 * Provides complete AG-UI functionality including:
 * - SSE connection management
 * - Message streaming and handling
 * - Tool call tracking
 * - HITL approval workflow
 * - State synchronization
 */
export function useAGUI(options: UseAGUIOptions): UseAGUIReturn {
  const {
    threadId,
    sessionId = threadId,
    apiUrl = '/api/v1/ag-ui',
    sseEndpoint: _sseEndpoint,
    approvalApiUrl = '/api/v1/ag-ui/approvals',
    initialMessages = [],
    tools = [],
    mode = 'auto',
    maxTokens,
    timeout,
    sharedStateOptions,
    optimisticStateOptions,
    autoReconnect: _autoReconnect = true,
    reconnectInterval: _reconnectInterval = 3000,
    onMessage,
    onToolCall,
    onApprovalRequired,
    onRunComplete,
    onConnectionChange,
  } = options;

  // ==========================================================================
  // State
  // ==========================================================================

  const [connectionStatus, setConnectionStatus] = useState<SSEConnectionStatus>('disconnected');
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [toolCalls, setToolCalls] = useState<ToolCallState[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [runState, setRunState] = useState<AGUIRunState>({
    runId: null,
    status: 'idle',
  });
  const [isStreaming, setIsStreaming] = useState(false);
  const [heartbeat, setHeartbeat] = useState<HeartbeatState | null>(null);  // S67-BF-1
  const [stepProgress, setStepProgress] = useState<StepProgressState>({  // S69-3
    steps: new Map(),
    currentStep: null,
  });

  // Refs
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const currentMessageRef = useRef<ChatMessage | null>(null);
  const currentToolCallRef = useRef<ToolCallState | null>(null);

  // ==========================================================================
  // Integrated Hooks
  // ==========================================================================

  const sharedState = useSharedState({
    sessionId,
    apiUrl: `${apiUrl}/state`,
    ...sharedStateOptions,
  });

  const optimisticState = useOptimisticState({
    initialState: {},
    apiUrl,
    ...optimisticStateOptions,
  });

  // ==========================================================================
  // Computed Values
  // ==========================================================================

  const isConnected = useMemo(
    () => connectionStatus === 'connected',
    [connectionStatus]
  );

  const isRunning = useMemo(
    () => runState.status === 'running',
    [runState.status]
  );

  // S69-3: Current step progress getter
  const currentStepProgress = useMemo(
    (): StepProgressEvent | null => {
      if (!stepProgress.currentStep) return null;
      return stepProgress.steps.get(stepProgress.currentStep) || null;
    },
    [stepProgress]
  );

  // ==========================================================================
  // Connection Status Update
  // ==========================================================================

  const updateConnectionStatus = useCallback(
    (status: SSEConnectionStatus) => {
      setConnectionStatus(status);
      onConnectionChange?.(status);
    },
    [onConnectionChange]
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
      onMessage?.(message);
      return message;
    },
    [onMessage]
  );

  // Add assistant message programmatically (for external use)
  const addAssistantMessage = useCallback(
    (content: string, toolCalls?: ToolCallState[]): ChatMessage => {
      const message: ChatMessage = {
        id: generateMessageId(),
        role: 'assistant',
        content,
        timestamp: new Date().toISOString(),
        toolCalls,
      };

      setMessages((prev) => [...prev, message]);
      onMessage?.(message);
      return message;
    },
    [onMessage]
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
    }

    // Update content with delta
    currentMessageRef.current.content += delta;

    // Capture current values before setState callback (async safety)
    const messageId = currentMessageRef.current.id;
    const newContent = currentMessageRef.current.content;

    setMessages((prev) =>
      prev.map((m) =>
        m.id === messageId
          ? { ...m, content: newContent }
          : m
      )
    );
  }, []);

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
  }, []);

  // ==========================================================================
  // Tool Call Management
  // ==========================================================================

  const startToolCall = useCallback(
    (toolCallId: string, name: string, args: Record<string, unknown> = {}) => {
      const toolCall: ToolCallState = {
        id: generateMessageId(),
        toolCallId,
        name,
        arguments: args,
        status: 'executing',
        startedAt: new Date().toISOString(),
      };

      currentToolCallRef.current = toolCall;
      setToolCalls((prev) => [...prev, toolCall]);
      onToolCall?.(toolCall);
    },
    [onToolCall]
  );

  const updateToolCallArgs = useCallback((args: Record<string, unknown>) => {
    if (!currentToolCallRef.current) return;

    currentToolCallRef.current.arguments = {
      ...currentToolCallRef.current.arguments,
      ...args,
    };

    setToolCalls((prev) =>
      prev.map((tc) =>
        tc.toolCallId === currentToolCallRef.current!.toolCallId
          ? { ...tc, arguments: currentToolCallRef.current!.arguments }
          : tc
      )
    );
  }, []);

  const completeToolCall = useCallback(
    (toolCallId: string, result: unknown, error?: string) => {
      const status: ToolCallStatus = error ? 'failed' : 'completed';
      const completedAt = new Date().toISOString();

      setToolCalls((prev) =>
        prev.map((tc) =>
          tc.toolCallId === toolCallId
            ? { ...tc, status, result, error, completedAt }
            : tc
        )
      );

      if (currentToolCallRef.current?.toolCallId === toolCallId) {
        const updated = {
          ...currentToolCallRef.current,
          status,
          result,
          error,
          completedAt,
        };
        onToolCall?.(updated);
        currentToolCallRef.current = null;
      }
    },
    [onToolCall]
  );

  const getToolCall = useCallback(
    (id: string): ToolCallState | undefined => {
      return toolCalls.find((tc) => tc.id === id || tc.toolCallId === id);
    },
    [toolCalls]
  );

  // ==========================================================================
  // Approval Management
  // ==========================================================================

  const addPendingApproval = useCallback(
    (approval: PendingApproval) => {
      setPendingApprovals((prev) => [...prev, approval]);
      onApprovalRequired?.(approval);

      // Update tool call status
      setToolCalls((prev) =>
        prev.map((tc) =>
          tc.toolCallId === approval.toolCallId
            ? { ...tc, status: 'requires_approval' }
            : tc
        )
      );
    },
    [onApprovalRequired]
  );

  const removePendingApproval = useCallback((approvalId: string) => {
    setPendingApprovals((prev) =>
      prev.filter((a) => a.approvalId !== approvalId)
    );
  }, []);

  const approveToolCall = useCallback(
    async (approvalId: string, comment?: string): Promise<boolean> => {
      try {
        const response = await fetch(`${approvalApiUrl}/${approvalId}/approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ comment }),
        });

        if (!response.ok) {
          console.error('Approval failed:', await response.text());
          return false;
        }

        const result = await response.json();
        removePendingApproval(approvalId);

        // Update tool call status
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

        return result.success;
      } catch (error) {
        console.error('Approval error:', error);
        return false;
      }
    },
    [approvalApiUrl, pendingApprovals, removePendingApproval]
  );

  const rejectToolCall = useCallback(
    async (approvalId: string, comment?: string): Promise<boolean> => {
      try {
        const response = await fetch(`${approvalApiUrl}/${approvalId}/reject`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ comment }),
        });

        if (!response.ok) {
          console.error('Rejection failed:', await response.text());
          return false;
        }

        const result = await response.json();
        removePendingApproval(approvalId);

        // Update tool call status
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

        return result.success;
      } catch (error) {
        console.error('Rejection error:', error);
        return false;
      }
    },
    [approvalApiUrl, pendingApprovals, removePendingApproval]
  );

  // ==========================================================================
  // SSE Event Handlers
  // ==========================================================================

  const handleSSEEvent = useCallback(
    (event: MessageEvent) => {
      const data = parseSSEData(event.data);
      if (!data) return;

      const eventType = data.type as AGUIEventType;

      switch (eventType) {
        case 'RUN_STARTED':
          setRunState({
            runId: data.run_id as string,
            status: 'running',
            startedAt: data.timestamp as string,
          });
          setIsStreaming(true);
          setHeartbeat(null);  // S67-BF-1: Reset heartbeat on run start
          break;

        case 'RUN_FINISHED': {
          const success = data.finish_reason !== 'error';
          setRunState((prev) => ({
            ...prev,
            status: success ? 'completed' : 'error',
            error: data.error as string | undefined,
            finishedAt: data.timestamp as string,
          }));
          setIsStreaming(false);
          setHeartbeat(null);  // S67-BF-1: Clear heartbeat on run finish
          setStepProgress({ steps: new Map(), currentStep: null });  // S69-3: Clear step progress
          finalizeCurrentMessage();
          onRunComplete?.(success, data.error as string | undefined);
          break;
        }

        case 'RUN_ERROR':
          setRunState((prev) => ({
            ...prev,
            status: 'error',
            error: data.error as string,
            finishedAt: data.timestamp as string,
          }));
          setIsStreaming(false);
          finalizeCurrentMessage();
          onRunComplete?.(false, data.error as string);
          break;

        case 'TEXT_MESSAGE_START': {
          // Initialize new message
          const newMessage: ChatMessage = {
            id: data.message_id as string || generateMessageId(),
            role: (data.role as MessageRole) || 'assistant',
            content: '',
            timestamp: data.timestamp as string || new Date().toISOString(),
          };
          currentMessageRef.current = newMessage;
          setMessages((prev) => [...prev, newMessage]);
          break;
        }

        case 'TEXT_MESSAGE_CONTENT':
          updateCurrentMessage(data.delta as string || '');
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
          updateToolCallArgs(data.args as Record<string, unknown> || {});
          break;

        case 'TOOL_CALL_END':
          completeToolCall(
            data.tool_call_id as string,
            data.result,
            data.error as string | undefined
          );
          break;

        case 'STATE_SNAPSHOT':
          // Handle state snapshot through sharedState
          if (data.snapshot) {
            sharedState.applyDiffs([{
              path: '',
              operation: 'replace',
              newValue: data.snapshot,
            }]);
          }
          break;

        case 'STATE_DELTA':
          // Handle state delta
          if (data.delta && Array.isArray(data.delta)) {
            sharedState.applyDiffs(
              (data.delta as Array<{ path: string; operation: string; value?: unknown }>).map((d) => ({
                path: d.path,
                operation: d.operation === 'set' ? 'replace' : d.operation === 'delete' ? 'remove' : 'add',
                newValue: d.value,
              }))
            );
          }
          break;

        case 'CUSTOM': {
          // Handle custom events (including approval requests and heartbeats)
          const eventName = data.event_name as string;
          if (eventName === 'APPROVAL_REQUIRED') {
            const payload = data.payload as Record<string, unknown>;
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
          } else if (eventName === 'heartbeat') {
            // S67-BF-1: Handle heartbeat events for long-running operations
            const payload = data.payload as Record<string, unknown>;
            setHeartbeat({
              count: payload.count as number,
              elapsedSeconds: payload.elapsed_seconds as number,
              message: payload.message as string,
              status: payload.status as 'processing' | 'idle',
            });
          } else if (eventName === 'step_progress') {
            // S69-3: Handle step progress events for hierarchical progress display
            const payload = data.payload as Record<string, unknown>;
            const progressEvent: StepProgressEvent = {
              stepId: payload.step_id as string,
              stepName: payload.step_name as string,
              current: payload.current as number,
              total: payload.total as number,
              progress: payload.progress as number,
              status: payload.status as SubStepStatusType,
              substeps: (payload.substeps as Array<Record<string, unknown>> || []).map((ss) => ({
                id: ss.id as string,
                name: ss.name as string,
                status: ss.status as SubStepStatusType,
                progress: ss.progress as number | undefined,
                message: ss.message as string | undefined,
                startedAt: ss.started_at as string | undefined,
                completedAt: ss.completed_at as string | undefined,
              })),
              metadata: payload.metadata as Record<string, unknown> | undefined,
            };

            setStepProgress((prev) => {
              const newSteps = new Map(prev.steps);
              newSteps.set(progressEvent.stepId, progressEvent);

              return {
                steps: newSteps,
                currentStep: progressEvent.status === 'running' ? progressEvent.stepId : prev.currentStep,
              };
            });
          }
          break;
        }

        default:
          console.log('Unhandled SSE event:', eventType, data);
      }
    },
    [
      finalizeCurrentMessage,
      updateCurrentMessage,
      startToolCall,
      updateToolCallArgs,
      completeToolCall,
      addPendingApproval,
      sharedState,
      onRunComplete,
    ]
  );

  // ==========================================================================
  // Run Agent
  // ==========================================================================

  const runAgent = useCallback(
    async (input?: Partial<RunAgentInput>): Promise<void> => {
      // Cancel any existing run
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Reset state
      setRunState({
        runId: input?.runId || generateRunId(),
        status: 'running',
        startedAt: new Date().toISOString(),
      });
      setIsStreaming(true);
      currentMessageRef.current = null;

      // Create abort controller for this run
      abortControllerRef.current = new AbortController();

      // Build messages array - include prompt as user message if provided
      const messagesPayload = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      // If prompt is provided and not already in messages, add it as user message
      if (input?.prompt) {
        const hasPromptInMessages = messagesPayload.some(
          (m) => m.role === 'user' && m.content === input.prompt
        );
        if (!hasPromptInMessages) {
          messagesPayload.push({
            role: 'user',
            content: input.prompt,
          });
        }
      }

      // Build request payload
      const payload = {
        thread_id: threadId,
        run_id: input?.runId || runState.runId || generateRunId(),
        session_id: sessionId,
        mode: input?.mode || mode,
        messages: messagesPayload,
        tools: (input?.tools || tools).map((t) => ({
          name: t.name,
          description: t.description,
          parameters: t.parameters,
        })),
        max_tokens: input?.maxTokens || maxTokens,
        timeout: input?.timeout || timeout,
        metadata: input?.metadata,
      };

      try {
        // Use fetch with EventSource-like handling
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

        // Read SSE stream
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No response body');
        }

        const decoder = new TextDecoder();
        let buffer = '';

        updateConnectionStatus('connected');

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE events from buffer
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data) {
                handleSSEEvent({ data } as MessageEvent);
              }
            }
          }
        }
      } catch (error) {
        if ((error as Error).name === 'AbortError') {
          setRunState((prev) => ({
            ...prev,
            status: 'cancelled',
            finishedAt: new Date().toISOString(),
          }));
        } else {
          console.error('Run agent error:', error);
          setRunState((prev) => ({
            ...prev,
            status: 'error',
            error: (error as Error).message,
            finishedAt: new Date().toISOString(),
          }));
          onRunComplete?.(false, (error as Error).message);
        }
      } finally {
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    },
    [
      threadId,
      sessionId,
      mode,
      messages,
      tools,
      maxTokens,
      timeout,
      apiUrl,
      runState.runId,
      handleSSEEvent,
      updateConnectionStatus,
      onRunComplete,
    ]
  );

  const cancelRun = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    setRunState((prev) => ({
      ...prev,
      status: 'cancelled',
      finishedAt: new Date().toISOString(),
    }));
  }, []);

  // ==========================================================================
  // Reconnection Logic
  // ==========================================================================

  const reconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    updateConnectionStatus('connecting');
    // The actual reconnection will happen through runAgent when needed
  }, [updateConnectionStatus]);

  // ==========================================================================
  // Cleanup on Unmount
  // ==========================================================================

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // ==========================================================================
  // Return
  // ==========================================================================

  return {
    // Connection state
    connectionStatus,
    isConnected,
    isStreaming,

    // Run state
    runState,
    isRunning,

    // Heartbeat state (S67-BF-1)
    heartbeat,

    // Step progress state (S69-3)
    stepProgress,
    currentStepProgress,

    // Messages
    messages,
    addUserMessage,
    addAssistantMessage,
    clearMessages,

    // Tool calls
    toolCalls,
    getToolCall,

    // Approvals
    pendingApprovals,
    approveToolCall,
    rejectToolCall,

    // Execution control
    runAgent,
    cancelRun,

    // State integration
    sharedState,
    optimisticState,

    // Reconnection
    reconnect,
  };
}

export default useAGUI;
