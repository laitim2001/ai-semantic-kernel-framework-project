/**
 * OrchestratorChat - 8-Step Pipeline Orchestration Chat Interface
 *
 * Phase 45: Orchestration Core
 * Copied from UnifiedChat.tsx as a new page for pipeline-based orchestration.
 * Original UnifiedChat preserved as template/fallback.
 *
 * Original:
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * S62-1: UnifiedChatWindow Base Architecture
 * S62-3: AG-UI Integration (Updated)
 * Sprint 66: S66-3 - Default tool configuration for Agentic functionality
 * Sprint 69: S69-4 - Dashboard Layout Integration (h-full instead of h-screen)
 * Sprint 73: S73-1 - Token/Time Metrics Fix
 * Sprint 73: S73-BF-1 - Token estimation (frontend fallback)
 * Sprint 74: S74-3 - Chat History Panel Integration
 * Sprint 74: S74-BF-1 - Thread message persistence fix
 * Phase 16: Unified Agentic Chat Interface
 * Phase 19: UI Enhancement
 *
 * Main page component for the unified chat interface.
 * Integrates Chat and Workflow modes with adaptive layout.
 * Now uses useUnifiedChat hook for real Claude API calls with tool support.
 *
 * Layout Note (Sprint 69/74):
 *   - Uses h-full to fill AppLayout container instead of h-screen
 *   - ChatHeader remains as internal page header
 *   - ChatHistoryPanel on left for conversation history
 *   - Works alongside Sidebar navigation
 */

import { FC, useCallback, useMemo, useEffect, useState, useRef } from 'react';
import { ChatHeader } from '@/components/unified-chat/ChatHeader';
import { ChatArea } from '@/components/unified-chat/ChatArea';
import { ChatInput } from '@/components/unified-chat/ChatInput';
import { WorkflowSidePanel } from '@/components/unified-chat/WorkflowSidePanel';
import { StatusBar } from '@/components/unified-chat/StatusBar';
import { OrchestrationPanel } from '@/components/unified-chat/OrchestrationPanel';
// Sprint 99: ApprovalDialog replaced by inline ApprovalMessageCard in MessageList
// import { ApprovalDialog } from '@/components/unified-chat/ApprovalDialog';
import {
  ChatHistoryPanel,
  ChatHistoryToggleButton,
} from '@/components/unified-chat/ChatHistoryPanel';
import { useUnifiedChat } from '@/hooks/useUnifiedChat';
import { useExecutionMetrics } from '@/hooks/useExecutionMetrics';
import { useChatThreads } from '@/hooks/useChatThreads';
import { useFileUpload } from '@/hooks/useFileUpload';
import { useOrchestration } from '@/hooks/useOrchestration';
import { useSSEChat } from '@/hooks/useSSEChat';
import type { OrchestrationMetadata as _OrchestratorApiType } from '@/types/ag-ui'; // SSE replaces orchestratorApi
import { memoryApi } from '@/api/endpoints/memory';
import { sessionsApi } from '@/api/endpoints/sessions';
import { filesApi } from '@/api/endpoints/files';
import { useAuthStore } from '@/store/authStore';
import type { DialogQuestion } from '@/api/endpoints/orchestration';
import type { Attachment } from '@/types/unified-chat';
import type { OrchestrationMetadata } from '@/types/ag-ui';
import { MemoryHint } from '@/components/unified-chat/MemoryHint';
import { AgentTeamPanel } from '@/components/unified-chat/agent-team/AgentTeamPanel';
import { AgentDetailDrawer } from '@/components/unified-chat/agent-team/AgentDetailDrawer';
import { useAgentTeamStore } from '@/stores/agentTeamStore';
import { AgentRosterPanel } from '@/components/unified-chat/agent-team/AgentRosterPanel';
import { useExpertSelectionStore } from '@/stores/expertSelectionStore';
// Phase 45: Pipeline components
import { PipelineProgressPanel } from '@/components/unified-chat/PipelineProgressPanel';
import { StepDetailPanel } from '@/components/unified-chat/StepDetailPanel';
import { GuidedDialogPanel } from '@/components/unified-chat/GuidedDialogPanel';
import { useOrchestratorPipeline } from '@/hooks/useOrchestratorPipeline';
import { useOrchestratorHistory } from '@/hooks/useOrchestratorHistory';
import type { MemoryHintItem } from '@/components/unified-chat/MemoryHint';
import type {
  UnifiedChatProps,
  ExecutionMode,
  ExecutionMetrics,
} from '@/types/unified-chat';
import type { RiskLevel, ToolDefinition } from '@/types/ag-ui';
import { cn } from '@/lib/utils';

/**
 * Default tools for Agentic functionality
 * Sprint 66: S66-3 - Enable Claude SDK built-in tools
 *
 * Low-risk tools: Execute automatically
 * High-risk tools: Require HITL approval
 */
const DEFAULT_TOOLS: ToolDefinition[] = [
  // === Low-Risk Tools (Auto-execute) ===
  {
    name: 'Read',
    description: 'Read file contents from the filesystem',
    parameters: {
      type: 'object',
      properties: {
        file_path: {
          type: 'string',
          description: 'Absolute path to the file to read',
        },
      },
      required: ['file_path'],
    },
  },
  {
    name: 'Glob',
    description: 'Find files matching a glob pattern',
    parameters: {
      type: 'object',
      properties: {
        pattern: {
          type: 'string',
          description: 'Glob pattern to match (e.g., "**/*.ts")',
        },
        path: {
          type: 'string',
          description: 'Directory to search in',
        },
      },
      required: ['pattern'],
    },
  },
  {
    name: 'Grep',
    description: 'Search for patterns in files',
    parameters: {
      type: 'object',
      properties: {
        pattern: {
          type: 'string',
          description: 'Regex pattern to search for',
        },
        path: {
          type: 'string',
          description: 'File or directory to search in',
        },
      },
      required: ['pattern'],
    },
  },
  {
    name: 'WebSearch',
    description: 'Search the web for information',
    parameters: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Search query',
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'WebFetch',
    description: 'Fetch content from a URL',
    parameters: {
      type: 'object',
      properties: {
        url: {
          type: 'string',
          description: 'URL to fetch',
        },
        prompt: {
          type: 'string',
          description: 'What to extract from the page',
        },
      },
      required: ['url', 'prompt'],
    },
  },

  // === High-Risk Tools (Require HITL approval) ===
  {
    name: 'Write',
    description: 'Write content to a file (HIGH RISK - requires approval)',
    parameters: {
      type: 'object',
      properties: {
        file_path: {
          type: 'string',
          description: 'Absolute path to the file',
        },
        content: {
          type: 'string',
          description: 'Content to write',
        },
      },
      required: ['file_path', 'content'],
    },
  },
  {
    name: 'Edit',
    description: 'Edit a file by replacing text (HIGH RISK - requires approval)',
    parameters: {
      type: 'object',
      properties: {
        file_path: {
          type: 'string',
          description: 'Absolute path to the file',
        },
        old_string: {
          type: 'string',
          description: 'Text to replace',
        },
        new_string: {
          type: 'string',
          description: 'Replacement text',
        },
      },
      required: ['file_path', 'old_string', 'new_string'],
    },
  },
  {
    name: 'Bash',
    description: 'Execute a shell command (HIGH RISK - requires approval)',
    parameters: {
      type: 'object',
      properties: {
        command: {
          type: 'string',
          description: 'Command to execute',
        },
      },
      required: ['command'],
    },
  },
];

// localStorage key prefix for active thread ID (user ID will be appended)
const ACTIVE_THREAD_KEY_PREFIX = 'ipa_active_thread_id_';
const GUEST_USER_ID = 'guest';

/**
 * OrchestratorChat Page Component
 *
 * Main orchestrator chat interface with:
 * - Chat history panel on left (Sprint 74)
 * - Adaptive layout (Chat mode: full width, Workflow mode: with side panel)
 * - Mode toggle in header
 * - Chat area for messages
 * - Status bar at bottom
 */
// Simple ID generator for session/thread IDs
const generateId = () =>
  `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;

export const OrchestratorChat: FC<UnifiedChatProps> = ({
  initialThreadId,
  initialSessionId,
  tools = [],
  apiUrl,
}) => {
  // S75-BF-1: Get user ID for isolation
  const user = useAuthStore((state) => state.user);
  const userId = user?.id || GUEST_USER_ID;
  // Phase 41: Use email for stable storage key across logins
  const userKey = user?.email || userId;
  const activeThreadKey = useMemo(() => `${ACTIVE_THREAD_KEY_PREFIX}${userKey}`, [userKey]);

  // Phase 45: 8-step pipeline hook
  const pipeline = useOrchestratorPipeline();

  // Sprint 169: Historical pipeline data for right panel
  const [selectedHistorySessionId, setSelectedHistorySessionId] = useState<string | null>(null);
  const { historicalPanelData, isLoadingHistory } = useOrchestratorHistory(selectedHistorySessionId);

  // S74-3: Chat history panel collapse state
  const [historyCollapsed, setHistoryCollapsed] = useState(false);

  // Phase 45: Track assistant message ID for pipeline response sync
  const pipelineAssistantIdRef = useRef<string | null>(null);

  // Sprint 99: Phase 28 Orchestration state
  // Phase 41: orchestrationEnabled now controls pipeline routing
  const [orchestrationEnabled, _setOrchestrationEnabled] = useState(true);
  const [showOrchestrationPanel, _setShowOrchestrationPanel] = useState(true);
  const [dialogQuestions, setDialogQuestions] = useState<DialogQuestion[] | null>(null);
  // Phase 41: Track orchestrator pipeline session ID
  const [orchestratorSessionId, setOrchestratorSessionId] = useState<string | null>(null);
  const [isPipelineSending] = useState(false); // kept for non-SSE fallback
  // Sprint 145: SSE streaming hook
  const { sendSSE, isStreaming: isSSEStreaming } = useSSEChat();
  // Sprint 146: Swarm store for AgentTeamPanel
  const agentTeamStatus = useAgentTeamStore((s) => s.agentTeamStatus);
  const _agentTeamReset = useAgentTeamStore((s) => s.reset);
  void _agentTeamReset; // used on session change (future)
  void useAgentTeamStore; // accessed via getState() in SSE handlers
  const agentTeamSelectedDetail = useAgentTeamStore((s) => s.selectedAgentDetail);
  const agentTeamIsDrawerOpen = useAgentTeamStore((s) => s.isDrawerOpen);
  const agentTeamCloseDrawer = useAgentTeamStore((s) => s.closeDrawer);
  const [showAgentTeamPanel, setShowAgentTeamPanel] = useState(false);
  // Sprint 146: HITL approval state
  const [pendingApproval, setPendingApproval] = useState<{
    approvalId: string;
    action: string;
    riskLevel: string;
    description: string;
    details?: Record<string, unknown>;
  } | null>(null);
  // Sprint 144: User-controlled pipeline mode
  const [pipelineMode, setPipelineMode] = useState<'chat' | 'workflow' | 'team'>('chat');
  const [suggestedMode, setSuggestedMode] = useState<string | null>(null);
  // Phase 41: Track typewriter animation state
  const [typewriterContent, setTypewriterContent] = useState<string | null>(null);
  const [typewriterMessageId, setTypewriterMessageId] = useState<string | null>(null);
  // Phase 41 S143-1: Memory hint state
  const [relatedMemories, setRelatedMemories] = useState<MemoryHintItem[]>([]);
  const [showMemoryHint, setShowMemoryHint] = useState(true);
  const isFirstMessage = useRef(true);

  // Suppress unused warnings (will be used when UI toggles are added)
  void _setOrchestrationEnabled;
  void _setShowOrchestrationPanel;

  // S74-2/3: Thread management
  // S74-BF-1: Add getMessages and saveMessages for thread switching
  // S74-BF-3: Add getThread for checking manual rename
  const {
    threads,
    createThread,
    updateThread,
    deleteThread,
    getThread,
    generateTitle,
    getMessages,
    saveMessages,
  } = useChatThreads();

  // S74-3: Active thread ID - try to restore from localStorage (user-isolated)
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);

  // S75-BF-1: Load active thread ID when user changes
  // S75-BF-3: Messages are loaded by the activeThreadId change effect below
  useEffect(() => {
    if (initialThreadId) {
      setActiveThreadId(initialThreadId);
      return;
    }
    try {
      const saved = localStorage.getItem(activeThreadKey);
      setActiveThreadId(saved);
    } catch {
      setActiveThreadId(null);
    }
  }, [activeThreadKey, initialThreadId]);

  // Persist active thread ID to localStorage (user-isolated)
  useEffect(() => {
    if (activeThreadId) {
      try {
        localStorage.setItem(activeThreadKey, activeThreadId);
      } catch {
        // Ignore storage errors
      }
    }
  }, [activeThreadId, activeThreadKey]);

  // Generate IDs if not provided
  // Use active thread ID or generate new one
  const threadId = useMemo(
    () => activeThreadId || initialThreadId || generateId(),
    [activeThreadId, initialThreadId]
  );
  const sessionId = useMemo(
    () => initialSessionId || generateId(),
    [initialSessionId]
  );

  // Determine which tools to use - props override or defaults
  const effectiveTools = useMemo(
    () => (tools && tools.length > 0 ? tools : DEFAULT_TOOLS),
    [tools]
  );

  // Use the unified chat hook for real AG-UI integration with tools
  const {
    messages,
    isConnected,
    isStreaming,
    error,
    sendMessage,
    cancelStream,
    clearMessages,
    setMessages,  // S74-BF-1: For loading messages when switching threads
    currentMode,
    autoMode,
    manualOverride: _manualOverride, // Reserved for mode switch UI
    isManuallyOverridden,
    setManualOverride,
    workflowState, // Now used by WorkflowSidePanel
    pendingApprovals,
    // Sprint 99: dialogApproval and dismissDialog no longer needed
    // Approvals are now shown inline via ApprovalMessageCard in MessageList
    toolCalls,
    checkpoints,
    currentCheckpoint,
    tokenUsage,
    approveToolCall,
    rejectToolCall,
    removeExpiredApproval,  // Sprint 99: For cleaning up expired approvals
    heartbeat,  // S67-BF-1: Heartbeat state for Rate Limit handling
  } = useUnifiedChat({
    threadId,
    sessionId,
    apiUrl,
    tools: effectiveTools,
    modePreference: 'chat',
    skipAutoLoadHistory: true,  // S74-BF-1: Use localStorage-based persistence instead
    onRunComplete: (success, errorMsg) => {
      if (!success && errorMsg) {
        console.error('[UnifiedChat] Run failed:', errorMsg);
      }
    },
  });

  // Derive connection status for UI
  const connection = isConnected ? 'connected' : (isStreaming ? 'connecting' : 'disconnected');

  // S73-1: Use execution metrics hook for timer functionality
  const {
    time: executionTime,
    startTimer,
    stopTimer,
    resetTimer,
  } = useExecutionMetrics();

  // S75-4: File upload management
  const {
    attachments,
    isUploading,
    addFiles,
    removeAttachment,
    uploadAll,
    clearAttachments,
    // Note: getUploadedFileIds removed - using uploadAll return value instead (S75-5 Fix)
  } = useFileUpload({
    maxFiles: 10,
    onUploadComplete: (attachment) => {
      console.log('[UnifiedChat] File uploaded:', attachment.file.name);
    },
    onUploadError: (attachment, error) => {
      console.error('[UnifiedChat] File upload failed:', attachment.file.name, error);
    },
  });

  // Sprint 99: Track pending orchestration message for later execution
  const pendingOrchestrationMessage = useRef<string | null>(null);
  // Sprint 99: Track current messages for orchestration callbacks
  // (setMessages doesn't support functional updates, so we need a ref)
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  // Sprint 99: Phase 28 Orchestration hook (kept for OrchestrationPanel debug view)
  const {
    state: orchestrationState,
    startOrchestration: _startOrchestration, // Phase 41: replaced by direct pipeline call
    respondToDialog,
    proceedWithExecution,
    reset: resetOrchestration,
  } = useOrchestration({
    sessionId,
    userId,
    includeRiskAssessment: true,
    autoExecute: true, // FIX-006: Auto-execute after orchestration when no approval needed
    onRoutingComplete: (decision) => {
      console.log('[UnifiedChat] Routing complete:', decision.intent_category, decision.routing_layer);
    },
    onDialogQuestions: (questions) => {
      console.log('[UnifiedChat] Dialog questions received:', questions.length);
      setDialogQuestions(questions);
    },
    onApprovalRequired: (assessment) => {
      console.log('[UnifiedChat] Approval required:', assessment.level, assessment.score);
    },
    onExecutionComplete: (result) => {
      console.log('[UnifiedChat] Orchestration execution complete:', result.success);
      // Add execution result as assistant message
      if (result.content) {
        const assistantMessage = {
          id: `orch-${Date.now()}`,
          role: 'assistant' as const,
          content: result.content,
          timestamp: new Date().toISOString(),
        };
        setMessages([...messagesRef.current, assistantMessage]);
      } else if (result.error) {
        // Show error message if execution failed
        const errorMessage = {
          id: `orch-err-${Date.now()}`,
          role: 'assistant' as const,
          content: `執行失敗: ${result.error}`,
          timestamp: new Date().toISOString(),
        };
        setMessages([...messagesRef.current, errorMessage]);
      }
      // Clear pending message
      pendingOrchestrationMessage.current = null;
    },
    onError: (error) => {
      console.error('[UnifiedChat] Orchestration error:', error);
      // Add error message to chat
      const errorMessage = {
        id: `orch-err-${Date.now()}`,
        role: 'assistant' as const,
        content: `Orchestration 錯誤: ${error}`,
        timestamp: new Date().toISOString(),
      };
      setMessages([...messagesRef.current, errorMessage]);
      pendingOrchestrationMessage.current = null;
    },
  });
  void _startOrchestration; // Phase 41: replaced by direct pipeline call

  // Phase 41: Typewriter effect — progressively reveal assistant response
  useEffect(() => {
    if (!typewriterContent || !typewriterMessageId) return;

    let index = 0;
    let rafId = 0;
    let lastTime = 0;
    const speed = 15; // ms per character

    const animate = (timestamp: number) => {
      if (!lastTime) lastTime = timestamp;
      const elapsed = timestamp - lastTime;

      if (elapsed >= speed) {
        const charsToAdd = Math.max(1, Math.floor(elapsed / speed));
        index = Math.min(index + charsToAdd, typewriterContent.length);
        lastTime = timestamp;

        // Update the specific message content
        const currentMsgs = messagesRef.current;
        const msgIdx = currentMsgs.findIndex(m => m.id === typewriterMessageId);
        if (msgIdx >= 0) {
          const updated = [...currentMsgs];
          updated[msgIdx] = { ...updated[msgIdx], content: typewriterContent.slice(0, index) };
          setMessages(updated);
        }

        if (index >= typewriterContent.length) {
          setTypewriterContent(null);
          setTypewriterMessageId(null);
          return;
        }
      }

      rafId = requestAnimationFrame(animate);
    };

    rafId = requestAnimationFrame(animate);

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typewriterContent, typewriterMessageId]);

  // S75-4: Convert hook attachments to typed Attachment array
  const typedAttachments: Attachment[] = useMemo(() => {
    return attachments.map((a) => ({
      ...a,
      serverFileId: a.serverResponse?.id,
    }));
  }, [attachments]);

  // S73-1: Start/stop timer based on streaming state
  useEffect(() => {
    if (isStreaming) {
      startTimer();
    } else {
      stopTimer();
    }
  }, [isStreaming, startTimer, stopTimer]);

  // S73-BF-1: Estimate token usage from messages (frontend estimation)
  // Claude tokenizer: ~4 chars per token for English, ~1.5-2 for Chinese
  // Using a conservative estimate of ~3 chars per token on average
  const estimatedTokens = useMemo(() => {
    if (tokenUsage.used > 0) {
      // If backend sends actual usage, use that
      return tokenUsage.used;
    }
    // Otherwise estimate from message content
    const totalChars = messages.reduce((sum, msg) => {
      return sum + (msg.content?.length || 0);
    }, 0);
    // Estimate: ~3 characters per token (conservative for mixed content)
    return Math.ceil(totalChars / 3);
  }, [messages, tokenUsage.used]);

  // Derive metrics from hook state
  // S73-1: Use executionTime from useExecutionMetrics instead of hardcoded value
  // S73-BF-1: Use estimated tokens when backend doesn't send TOKEN_UPDATE
  const metrics: ExecutionMetrics = useMemo(() => ({
    tokens: {
      used: estimatedTokens,
      limit: tokenUsage.limit,
      percentage: (estimatedTokens / tokenUsage.limit) * 100,
    },
    time: pipeline.totalMs
      ? { total: pipeline.totalMs, isRunning: pipeline.isRunning, formatted: `${(pipeline.totalMs / 1000).toFixed(1)}s` }
      : executionTime,
    toolCallCount: toolCalls.length,
    messageCount: messages.length,
  }), [estimatedTokens, tokenUsage.limit, executionTime, pipeline.totalMs, toolCalls.length, messages.length]);

  // Risk state — prefer pipeline risk_assessment step metadata, fallback to pending approvals
  const riskLevel: RiskLevel = useMemo(() => {
    const riskStep = pipeline.steps.find(s => s.name === 'risk_assessment' && s.status === 'completed');
    if (riskStep?.metadata) {
      const level = (riskStep.metadata.level as string || '').toLowerCase();
      if (['low', 'medium', 'high', 'critical'].includes(level)) return level as RiskLevel;
    }
    if (pendingApprovals.length === 0) return 'low';
    const maxRisk = pendingApprovals.reduce((max, a) => {
      const levels: RiskLevel[] = ['low', 'medium', 'high', 'critical'];
      return levels.indexOf(a.riskLevel) > levels.indexOf(max) ? a.riskLevel : max;
    }, 'low' as RiskLevel);
    return maxRisk;
  }, [pipeline.steps, pendingApprovals]);

  const riskScore = useMemo(() => {
    const riskStep = pipeline.steps.find(s => s.name === 'risk_assessment' && s.status === 'completed');
    if (riskStep?.metadata?.score != null) return riskStep.metadata.score as number;
    if (pendingApprovals.length === 0) return 0.1;
    return Math.max(...pendingApprovals.map(a => a.riskScore));
  }, [pipeline.steps, pendingApprovals]);

  // Checkpoint state
  const hasCheckpoint = checkpoints.length > 0;
  const canRestore = hasCheckpoint && currentCheckpoint !== null;

  // Handle mode change from header
  const handleModeChange = useCallback((mode: ExecutionMode) => {
    setManualOverride(mode);
  }, [setManualOverride]);

  // S74-3: Handle new thread creation
  // S75-BF-4: Cancel streaming before switching threads to prevent message leakage
  const handleNewThread = useCallback(() => {
    // Cancel any ongoing streaming to prevent messages from appearing in wrong thread
    if (isStreaming) {
      cancelStream();
    }

    // Save current thread's messages before switching (if any)
    if (activeThreadId && messages.length > 0) {
      saveMessages(activeThreadId, messages);
    }

    const newId = createThread();
    setActiveThreadId(newId);
    clearMessages();
    resetTimer();
  }, [isStreaming, cancelStream, activeThreadId, messages, saveMessages, createThread, clearMessages, resetTimer]);

  // S74-3: Handle thread selection
  // S74-BF-1: Load messages from localStorage when switching threads
  // S75-BF-4: Cancel streaming before switching threads to prevent message leakage
  const handleSelectThread = useCallback((id: string) => {
    if (id === activeThreadId) return;

    // Cancel any ongoing streaming to prevent messages from appearing in wrong thread
    if (isStreaming) {
      cancelStream();
    }

    // Save current thread's messages before switching
    if (activeThreadId && messages.length > 0) {
      saveMessages(activeThreadId, messages);
    }

    // Switch to new thread
    setActiveThreadId(id);
    resetTimer();

    // Load messages for the selected thread
    const savedMessages = getMessages(id);
    if (savedMessages.length > 0) {
      setMessages(savedMessages);
      // Sprint 169: Auto-load historical pipeline for the latest assistant message
      const lastAssistant = [...savedMessages].reverse().find(
        (m) => m.role === 'assistant' && m.orchestrationMetadata?.sessionId
      );
      setSelectedHistorySessionId(lastAssistant?.orchestrationMetadata?.sessionId || null);
    } else {
      clearMessages();
      setSelectedHistorySessionId(null);
    }
  }, [isStreaming, cancelStream, activeThreadId, messages, saveMessages, getMessages, setMessages, clearMessages, resetTimer]);

  // S74-3: Handle thread deletion
  const handleDeleteThread = useCallback((id: string) => {
    deleteThread(id);
    // If we deleted the active thread, clear the selection
    if (id === activeThreadId) {
      const remaining = threads.filter((t) => t.id !== id);
      if (remaining.length > 0) {
        setActiveThreadId(remaining[0].id);
      } else {
        setActiveThreadId(null);
      }
      clearMessages();
      resetTimer();
    }
  }, [deleteThread, activeThreadId, threads, clearMessages, resetTimer]);

  // S74-3: Update thread metadata when messages change
  // S74-BF-3: Only auto-generate title if thread has default title ('新對話')
  // This preserves user's manual rename
  useEffect(() => {
    if (!activeThreadId || messages.length === 0) return;

    const userMessages = messages.filter((m) => m.role === 'user');
    if (userMessages.length === 0) return;

    const firstUserMessage = userMessages[0];
    const lastMessage = messages[messages.length - 1];

    // Get current thread to check if title was manually set
    const currentThread = getThread(activeThreadId);
    const isDefaultTitle = !currentThread || currentThread.title === '新對話';

    // Only update title if it's still the default
    updateThread(activeThreadId, {
      ...(isDefaultTitle && { title: generateTitle(firstUserMessage.content) }),
      lastMessage: lastMessage.content.slice(0, 50),
      messageCount: messages.length,
    });
  }, [activeThreadId, messages, updateThread, generateTitle, getThread]);

  // S74-BF-1: Auto-save messages to localStorage when they change
  useEffect(() => {
    if (!activeThreadId || messages.length === 0) return;
    // Debounce-like: only save when not streaming to avoid excessive writes
    if (!isStreaming) {
      saveMessages(activeThreadId, messages);
    }
  }, [activeThreadId, messages, isStreaming, saveMessages]);

  // S74-BF-1: Load messages on initial mount if activeThreadId exists
  // Note: S75-BF-3 now handles loading messages when activeThreadId is restored
  // This effect is kept as a fallback for edge cases where activeThreadId is set
  // before the restore effect runs (e.g., from props)
  useEffect(() => {
    if (activeThreadId && messages.length === 0) {
      const savedMessages = getMessages(activeThreadId);
      if (savedMessages.length > 0) {
        setMessages(savedMessages);
      }
    }
    // Only run when activeThreadId changes, not on every messages change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeThreadId]);

  // S74-3: Handle send message with auto thread creation
  // S75-4: Updated to handle file attachments
  // S75-5 Fix: Use uploadAll return value to avoid React state sync issue
  // Sprint 99: Phase 28 - Optional orchestration flow before sending
  const handleSend = useCallback(async (content: string, fileIds?: string[]) => {
    // Sprint 165: Reset expert roster on new message
    useExpertSelectionStore.getState().reset();

    // Auto-create thread if none active
    let threadToUse = activeThreadId;
    if (!threadToUse) {
      threadToUse = createThread(generateTitle(content));
      setActiveThreadId(threadToUse);
    }

    // S75-5 Fix: Get file IDs directly from uploadAll return value
    let allFileIds: string[] = fileIds || [];

    if (!fileIds && attachments.length > 0) {
      allFileIds = await uploadAll();
      console.log('[S75-5] Uploaded file IDs:', allFileIds);
    }

    // Phase 45: 8-step pipeline as the sole response channel
    if (orchestrationEnabled) {
      console.log('[OrchestratorChat] Pipeline send:', content.slice(0, 50));

      // Add user message to chat immediately
      const userMessage = {
        id: `user-${Date.now()}`,
        role: 'user' as const,
        content: content,
        timestamp: new Date().toISOString(),
      };
      const messagesWithUser = [...messagesRef.current, userMessage];
      setMessages(messagesWithUser);

      // Create assistant message placeholder (will be updated by useEffect watching pipeline.responseText)
      const assistantMessageId = `pipeline-${Date.now()}`;
      pipelineAssistantIdRef.current = assistantMessageId;

      const assistantMessage = {
        id: assistantMessageId,
        role: 'assistant' as const,
        content: '...',
        timestamp: new Date().toISOString(),
        orchestrationMetadata: {
          executionMode: pipelineMode,
        } as OrchestrationMetadata,
      };
      setMessages([...messagesWithUser, assistantMessage]);

      // Trigger the 8-step pipeline (sole response channel)
      // Team mode requires explicit user action (CC design: agents are user-driven)
      pipeline.sendMessage(content, userId, { force_team: pipelineMode === 'team' });

      // Phase 45: Old SSE flow disabled — pipeline.sendMessage() is the sole channel
      // Response text is synced to chat via useEffect watching pipeline.responseText

      if (allFileIds.length > 0) clearAttachments();
      return;
    }

    // Phase 45: Old SSE dead code removed — pipeline.sendMessage() is the sole channel
    // Fallback: Direct send without orchestration (AG-UI SSE path)
    sendMessage(content, allFileIds.length > 0 ? allFileIds : undefined).catch((err) => {
      console.error('[UnifiedChat] Failed to send message:', err);
    });

    // Clear attachments after sending
    if (allFileIds.length > 0) {
      clearAttachments();
    }
  }, [
    activeThreadId, createThread, generateTitle, sendMessage, attachments,
    uploadAll, clearAttachments, orchestrationEnabled, orchestratorSessionId,
    userId
  ]);

  // Phase 45: Sync pipeline.responseText → assistant message in chat
  useEffect(() => {
    const msgId = pipelineAssistantIdRef.current;
    if (!msgId) return;

    const displayText = pipeline.responseText
      || (pipeline.isRunning ? 'Pipeline 執行中...' : '')
      || (pipeline.error ? `Error: ${pipeline.error}` : '');

    if (!displayText) return;

    const updated = messagesRef.current.map(m =>
      m.id === msgId ? { ...m, content: displayText } : m
    );
    setMessages(updated);
  }, [pipeline.responseText, pipeline.isRunning, pipeline.error]);

  // Phase 45: When pipeline completes, finalize assistant message
  useEffect(() => {
    const msgId = pipelineAssistantIdRef.current;
    if (!msgId || pipeline.isRunning || pipeline.totalMs === 0) return;

    const finalContent = pipeline.responseText || '(Pipeline completed with no response text)';
    // Derive mode: prefer selectedRoute, fallback to intent from step metadata
    const intentStep = pipeline.steps.find(s => s.name === 'intent_analysis');
    const intentLabel = intentStep?.metadata?.intent as string | undefined;
    const routeLabel = pipeline.selectedRoute || intentLabel || 'chat';

    const updated = messagesRef.current.map(m =>
      m.id === msgId
        ? {
            ...m,
            content: finalContent,
            orchestrationMetadata: {
              ...((m as Record<string, unknown>).orchestrationMetadata as Record<string, unknown> || {}),
              executionMode: routeLabel,
              processingTimeMs: pipeline.totalMs,
              sessionId: pipeline.sessionId || undefined,
            } as OrchestrationMetadata,
          }
        : m
    );
    setMessages(updated);
  }, [pipeline.totalMs, pipeline.isRunning, pipeline.responseText, pipeline.selectedRoute]);

  // Sprint 169: Clear historical data when pipeline starts running
  useEffect(() => {
    if (pipeline.isRunning) {
      setSelectedHistorySessionId(null);
    }
  }, [pipeline.isRunning]);

  // Sprint 169: Compute effective panel data (live vs historical)
  const effectivePanelData = useMemo(() => {
    // Priority 1: Live pipeline data while running or just completed
    if (pipeline.isRunning || (pipeline.totalMs > 0 && !historicalPanelData)) {
      return {
        steps: pipeline.steps,
        currentStepIndex: pipeline.currentStepIndex,
        selectedRoute: pipeline.selectedRoute,
        totalMs: pipeline.totalMs,
        isRunning: pipeline.isRunning,
        agents: pipeline.agents,
        routeReasoning: pipeline.routeReasoning,
        isHistorical: false,
      };
    }
    // Priority 2: Historical data from API
    if (historicalPanelData) {
      return {
        steps: historicalPanelData.steps,
        currentStepIndex: -1,
        selectedRoute: historicalPanelData.selectedRoute,
        totalMs: historicalPanelData.totalMs,
        isRunning: false,
        agents: historicalPanelData.agents,
        routeReasoning: historicalPanelData.routeReasoning,
        isHistorical: true,
      };
    }
    // Priority 3: Empty/idle state
    return {
      steps: pipeline.steps,
      currentStepIndex: -1,
      selectedRoute: null,
      totalMs: 0,
      isRunning: false,
      agents: [] as typeof pipeline.agents,
      routeReasoning: null,
      isHistorical: false,
    };
  }, [pipeline.isRunning, pipeline.totalMs, pipeline.steps, pipeline.currentStepIndex,
      pipeline.selectedRoute, pipeline.agents, pipeline.routeReasoning, historicalPanelData]);

  // Phase 41 S143-2: Handle session resume from ChatHistoryPanel
  const handleResumeSession = useCallback(async (resumedSessionId: string) => {
    console.log('[UnifiedChat] Resuming session:', resumedSessionId);
    // Update orchestrator session ID
    setOrchestratorSessionId(resumedSessionId);

    // Load conversation history
    try {
      const historyResponse = await sessionsApi.getSessionMessages(resumedSessionId);
      const historyMessages = (historyResponse.messages || []).map((msg, idx) => ({
        id: msg.id || `resumed-${resumedSessionId}-${idx}`,
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp,
        orchestrationMetadata: msg.metadata?.orchestration
          ? (msg.metadata.orchestration as OrchestrationMetadata)
          : undefined,
      }));
      setMessages(historyMessages);
      isFirstMessage.current = false;
    } catch (err) {
      console.error('[UnifiedChat] Failed to load session history:', err);
    }
  }, [setMessages]);

  // Sprint 99: Handle orchestration approval - proceed with message
  const handleOrchestrationApprove = useCallback(async () => {
    console.log('[UnifiedChat] Orchestration approved, proceeding with execution');
    await proceedWithExecution();
  }, [proceedWithExecution]);

  // Sprint 99: Handle orchestration rejection
  const handleOrchestrationReject = useCallback(() => {
    console.log('[UnifiedChat] Orchestration rejected');
    resetOrchestration();
    setDialogQuestions(null);
  }, [resetOrchestration]);

  // Sprint 99: Handle dialog response
  const handleDialogResponse = useCallback(async (responses: Record<string, string>) => {
    console.log('[UnifiedChat] Dialog response:', responses);
    await respondToDialog(responses);
  }, [respondToDialog]);

  // Sprint 99: Handle skip dialog - execute directly without completing dialog
  const handleSkipDialog = useCallback(async () => {
    console.log('[UnifiedChat] Skipping dialog, executing directly');
    setDialogQuestions(null);
    await proceedWithExecution();
  }, [proceedWithExecution]);

  // S75-4: Handle file attachment
  // Note: Files are added to queue and uploaded when message is sent (handleSend)
  // This avoids race conditions with React's async state updates
  const handleAttach = useCallback((files: File[]) => {
    addFiles(files);
    // Do NOT call uploadAll() here - it would use stale attachments state
    // Upload happens in handleSend when user sends the message
  }, [addFiles]);

  // Handle cancel streaming
  const handleCancel = useCallback(() => {
    cancelStream();
  }, [cancelStream]);

  // Handle checkpoint restore
  const handleRestore = useCallback((checkpointId?: string) => {
    console.log('[UnifiedChat] Restore checkpoint triggered:', checkpointId);
    // TODO: Implement checkpoint restoration via API
  }, []);

  // Handle tool call approval
  const handleApprove = useCallback(async (approvalId: string) => {
    console.log('[UnifiedChat] Approving tool call:', approvalId);
    try {
      await approveToolCall(approvalId);
    } catch (err) {
      console.error('[UnifiedChat] Failed to approve tool call:', err);
    }
  }, [approveToolCall]);

  // Handle tool call rejection
  const handleReject = useCallback(async (approvalId: string, reason?: string) => {
    console.log('[UnifiedChat] Rejecting tool call:', approvalId, reason);
    try {
      await rejectToolCall(approvalId, reason);
    } catch (err) {
      console.error('[UnifiedChat] Failed to reject tool call:', err);
    }
  }, [rejectToolCall]);

  // Sprint 76: Handle file download
  const handleDownload = useCallback(async (fileId: string) => {
    console.log('[UnifiedChat] Downloading file:', fileId);
    try {
      await filesApi.download(fileId);
    } catch (err) {
      console.error('[UnifiedChat] Failed to download file:', err);
      throw err; // Re-throw to let UI handle error state
    }
  }, []);

  // Determine effective mode — always 'chat' (workflow removed; route shown in StatusBar)
  const effectiveMode: ExecutionMode = 'chat';
  // Pipeline route for StatusBar display (direct_answer/subagent/team)
  const pipelineRoute = pipeline.selectedRoute;

  return (
    <div
      className="flex h-full bg-gray-50"
      data-testid="unified-chat-page"
      data-thread-id={threadId}
      data-session-id={sessionId}
    >
      {/* S74-3: Chat History Panel */}
      <ChatHistoryPanel
        threads={threads}
        activeThreadId={activeThreadId}
        onSelectThread={handleSelectThread}
        onNewThread={handleNewThread}
        onDeleteThread={handleDeleteThread}
        onRenameThread={(id, newTitle) => updateThread(id, { title: newTitle })}
        onResumeSession={handleResumeSession}
        isCollapsed={historyCollapsed}
        onToggle={() => setHistoryCollapsed(!historyCollapsed)}
      />

      {/* Toggle button when history panel is collapsed */}
      {historyCollapsed && (
        <ChatHistoryToggleButton
          onClick={() => setHistoryCollapsed(false)}
        />
      )}

      {/* Main Chat Container */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <ChatHeader
          title="IPA Assistant"
          currentMode={effectiveMode}
          autoMode={autoMode}
          isManuallyOverridden={isManuallyOverridden}
          connection={connection}
          onModeChange={handleModeChange}
        />

        {/* Main Content Area */}
        <main className={cn('flex-1 flex overflow-hidden')}>
          {/* Chat Area with Tool Call Display */}
          <div
            className={cn(
              'flex-1 flex flex-col bg-white'
            )}
          >
            {/* Error Display */}
            {error && (
              <div className="px-4 py-2 bg-red-50 border-b border-red-200">
                <p className="text-sm text-red-600">
                  <span className="font-medium">Error:</span> {error.message}
                </p>
              </div>
            )}

            {/* Sprint 146: HITL Inline Approval */}
            {pendingApproval && (
              <div className="mx-4 my-2 p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <div className="text-red-500 text-xl mt-0.5">&#9888;</div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-red-800 text-sm">
                      {pendingApproval.riskLevel} 風險操作需要審批
                    </h4>
                    <p className="text-sm text-red-700 mt-1">{pendingApproval.description}</p>
                    {pendingApproval.details && (
                      <p className="text-xs text-red-600 mt-1">
                        {JSON.stringify(pendingApproval.details)}
                      </p>
                    )}
                    <div className="flex gap-2 mt-3">
                      <button
                        className="px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                        onClick={async () => {
                          try {
                            const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';
                            const authToken = useAuthStore.getState().token;
                            const hdrs: Record<string, string> = { 'Content-Type': 'application/json' };
                            if (authToken) hdrs['Authorization'] = `Bearer ${authToken}`;
                            await fetch(`${API_BASE}/orchestrator/approval/${pendingApproval.approvalId}`, {
                              method: 'POST',
                              headers: hdrs,
                              body: JSON.stringify({ action: 'approve' }),
                            });
                          } catch { /* non-critical */ }
                          setPendingApproval(null);
                        }}
                      >
                        批准
                      </button>
                      <button
                        className="px-3 py-1.5 bg-gray-200 text-gray-700 text-sm rounded hover:bg-gray-300"
                        onClick={async () => {
                          try {
                            const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';
                            const authToken = useAuthStore.getState().token;
                            const hdrs: Record<string, string> = { 'Content-Type': 'application/json' };
                            if (authToken) hdrs['Authorization'] = `Bearer ${authToken}`;
                            await fetch(`${API_BASE}/orchestrator/approval/${pendingApproval.approvalId}`, {
                              method: 'POST',
                              headers: hdrs,
                              body: JSON.stringify({ action: 'reject' }),
                            });
                          } catch { /* non-critical */ }
                          setPendingApproval(null);
                        }}
                      >
                        拒絕
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Messages Area - Using ChatArea component with tool support */}
            <ChatArea
              messages={messages}
              isStreaming={isStreaming}
              pendingApprovals={pendingApprovals}
              onApprove={handleApprove}
              onReject={handleReject}
              onExpired={removeExpiredApproval}
              onDownload={handleDownload}
            />
          </div>

          {/* Phase 45: Pipeline Progress + Step Detail + Agent Team (right side, stacked) */}
          <div className="w-[380px] border-l bg-white dark:bg-gray-950 overflow-y-auto hidden lg:flex flex-col">
            <PipelineProgressPanel
              steps={effectivePanelData.steps}
              currentStepIndex={effectivePanelData.currentStepIndex}
              selectedRoute={effectivePanelData.selectedRoute}
              totalMs={effectivePanelData.totalMs}
              isRunning={effectivePanelData.isRunning}
            />
            {/* Sprint 169: Historical mode indicator */}
            {effectivePanelData.isHistorical && (
              <div className="px-3 py-1.5 text-xs text-amber-700 bg-amber-50 dark:text-amber-400 dark:bg-amber-950/30 border-b flex items-center gap-1.5">
                <span>&#128203;</span>
                <span>歷史記錄</span>
              </div>
            )}
            <div className="flex-1 border-t overflow-y-auto">
              <StepDetailPanel
                steps={effectivePanelData.steps}
                agents={effectivePanelData.agents}
                selectedRoute={effectivePanelData.selectedRoute}
                routeReasoning={effectivePanelData.routeReasoning}
              />
              {/* Agent Team Panel — shown below step details when team/subagent route active */}
              {agentTeamStatus && (
                <div className="border-t">
                  <AgentTeamPanel
                    agentTeamStatus={agentTeamStatus}
                    onAgentClick={(agent) => {
                      useAgentTeamStore.getState().selectAgent(agent);
                    }}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Agent Detail Drawer (overlay) — uses store-accumulated data, no API fetch */}
          {agentTeamIsDrawerOpen && agentTeamSelectedDetail && (
            <AgentDetailDrawer
              open={agentTeamIsDrawerOpen}
              onClose={agentTeamCloseDrawer}
              teamId={agentTeamStatus?.teamId || ''}
              agent={agentTeamStatus?.agents.find(
                a => a.agentId === agentTeamSelectedDetail?.agentId
              ) || null}
              workerDetail={agentTeamSelectedDetail}
            />
          )}
        </main>

        {/* Phase 41 S143-1: MemoryHint above ChatInput */}
        {relatedMemories.length > 0 && (
          <MemoryHint
            memories={relatedMemories}
            isVisible={showMemoryHint}
            onDismiss={() => setShowMemoryHint(false)}
          />
        )}

        {/* Phase 45: Guided Dialog Panel (when pipeline pauses for missing info) */}
        {pipeline.dialogPause && (
          <div className="mx-4 mb-2">
            <GuidedDialogPanel
              dialogPause={pipeline.dialogPause}
              onSubmit={pipeline.respondDialog}
              onSkip={() => {
                // Skip dialog — re-run pipeline with original task as-is
                const storedTask = sessionStorage.getItem(`pipeline-task-${pipeline.sessionId}`) || '';
                if (storedTask) pipeline.sendMessage(storedTask, undefined, { force_team: pipelineMode === 'team' });
              }}
            />
          </div>
        )}

        {/* Phase 45: HITL Pause Banner (when pipeline pauses for approval) */}
        {pipeline.hitlPause && (
          <div className="mx-4 mb-2 p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-red-500">&#9888;</span>
              <span className="font-medium text-sm text-red-800">
                {pipeline.hitlPause.riskLevel.toUpperCase()} 風險 — 需要人工審批
              </span>
            </div>
            <div className="flex gap-2">
              <button
                className="px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                onClick={() => pipeline.resumeApproval('approved')}
              >
                批准
              </button>
              <button
                className="px-3 py-1.5 bg-red-600 text-white text-sm rounded hover:bg-red-700"
                onClick={() => pipeline.resumeApproval('rejected')}
              >
                拒絕
              </button>
            </div>
          </div>
        )}

        {/* Sprint 144: Mode Selector + Suggested Mode Banner */}
        {suggestedMode && suggestedMode !== pipelineMode && (
          <div className="mx-4 mb-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg flex items-center justify-between text-sm">
            <span className="text-amber-800">
              路由建議切換到 <strong>{suggestedMode}</strong> 模式
            </span>
            <button
              className="px-2 py-1 bg-amber-100 hover:bg-amber-200 text-amber-900 rounded text-xs font-medium"
              onClick={() => {
                setPipelineMode(suggestedMode as 'chat' | 'workflow' | 'team');
                setSuggestedMode(null);
              }}
            >
              切換
            </button>
          </div>
        )}
        <div className="flex items-center gap-1 px-4 pb-1">
          {(['chat', 'team'] as const).map((m) => (
            <button
              key={m}
              onClick={() => { setPipelineMode(m); setSuggestedMode(null); }}
              className={`px-3 py-1 text-xs rounded-full font-medium transition-colors ${
                pipelineMode === m
                  ? m === 'chat'
                    ? 'bg-blue-100 text-blue-800 ring-1 ring-blue-300'
                    : 'bg-orange-100 text-orange-800 ring-1 ring-orange-300'
                  : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
              }`}
            >
              {m === 'chat' ? 'Chat' : 'Team'}
            </button>
          ))}
          <span className="text-[10px] text-muted-foreground ml-1">
            {pipelineMode === 'chat' ? 'AI 自動選擇模式' : '強制啟用專家團隊'}
          </span>
        </div>

        {/* Sprint 165: Expert Roster Preview */}
        <AgentRosterPanel />

        {/* Input Area - S75-4: Added file attachment support */}
        <ChatInput
          onSend={handleSend}
          isStreaming={isStreaming || isUploading || isPipelineSending || isSSEStreaming || pipeline.isRunning}
          onCancel={handleCancel}
          placeholder={
            pipelineMode === 'team'
              ? 'Describe the incident for the agent team...'
              : 'Type a message...'
          }
          attachments={typedAttachments}
          onAttach={handleAttach}
          onRemoveAttachment={removeAttachment}
        />

        {/* Status Bar */}
        <StatusBar
          mode={effectiveMode}
          modeSource={isManuallyOverridden ? 'manual' : 'auto'}
          riskLevel={riskLevel}
          riskScore={riskScore}
          metrics={metrics}
          hasCheckpoint={hasCheckpoint}
          canRestore={canRestore}
          onRestore={handleRestore}
          heartbeat={heartbeat}  // S67-BF-1
          pipelineRoute={pipelineRoute}
        />
      </div>

      {/* Sprint 99: HITL approvals now shown inline via ApprovalMessageCard in MessageList */}
    </div>
  );
};

export default OrchestratorChat;
