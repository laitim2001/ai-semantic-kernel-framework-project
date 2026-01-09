/**
 * UnifiedChat - Unified Agentic Chat Interface Page
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

import { FC, useCallback, useMemo, useEffect, useState } from 'react';
import { ChatHeader } from '@/components/unified-chat/ChatHeader';
import { ChatArea } from '@/components/unified-chat/ChatArea';
import { ChatInput } from '@/components/unified-chat/ChatInput';
import { WorkflowSidePanel } from '@/components/unified-chat/WorkflowSidePanel';
import { StatusBar } from '@/components/unified-chat/StatusBar';
import {
  ChatHistoryPanel,
  ChatHistoryToggleButton,
} from '@/components/unified-chat/ChatHistoryPanel';
import { useUnifiedChat } from '@/hooks/useUnifiedChat';
import { useExecutionMetrics } from '@/hooks/useExecutionMetrics';
import { useChatThreads } from '@/hooks/useChatThreads';
import { useFileUpload } from '@/hooks/useFileUpload';
import { filesApi } from '@/api/endpoints/files';
import { useAuthStore } from '@/store/authStore';
import type { Attachment } from '@/types/unified-chat';
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
 * UnifiedChat Page Component
 *
 * Main unified chat interface with:
 * - Chat history panel on left (Sprint 74)
 * - Adaptive layout (Chat mode: full width, Workflow mode: with side panel)
 * - Mode toggle in header
 * - Chat area for messages
 * - Status bar at bottom
 */
// Simple ID generator for session/thread IDs
const generateId = () =>
  `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;

export const UnifiedChat: FC<UnifiedChatProps> = ({
  initialThreadId,
  initialSessionId,
  tools = [],
  apiUrl,
}) => {
  // S75-BF-1: Get user ID for isolation
  const user = useAuthStore((state) => state.user);
  const userId = user?.id || GUEST_USER_ID;
  const activeThreadKey = useMemo(() => `${ACTIVE_THREAD_KEY_PREFIX}${userId}`, [userId]);

  // S74-3: Chat history panel collapse state
  const [historyCollapsed, setHistoryCollapsed] = useState(false);

  // S74-2/3: Thread management
  // S74-BF-1: Add getMessages and saveMessages for thread switching
  const {
    threads,
    createThread,
    updateThread,
    deleteThread,
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
    toolCalls,
    checkpoints,
    currentCheckpoint,
    tokenUsage,
    approveToolCall,
    rejectToolCall,
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
    getUploadedFileIds,
  } = useFileUpload({
    maxFiles: 10,
    onUploadComplete: (attachment) => {
      console.log('[UnifiedChat] File uploaded:', attachment.file.name);
    },
    onUploadError: (attachment, error) => {
      console.error('[UnifiedChat] File upload failed:', attachment.file.name, error);
    },
  });

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
    time: executionTime,
    toolCallCount: toolCalls.length,
    messageCount: messages.length,
  }), [estimatedTokens, tokenUsage.limit, executionTime, toolCalls.length, messages.length]);

  // Risk state (derived from pending approvals)
  const riskLevel: RiskLevel = useMemo(() => {
    if (pendingApprovals.length === 0) return 'low';
    const maxRisk = pendingApprovals.reduce((max, a) => {
      const levels: RiskLevel[] = ['low', 'medium', 'high', 'critical'];
      return levels.indexOf(a.riskLevel) > levels.indexOf(max) ? a.riskLevel : max;
    }, 'low' as RiskLevel);
    return maxRisk;
  }, [pendingApprovals]);

  const riskScore = useMemo(() => {
    if (pendingApprovals.length === 0) return 0.1;
    return Math.max(...pendingApprovals.map(a => a.riskScore));
  }, [pendingApprovals]);

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
    } else {
      clearMessages();
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
  useEffect(() => {
    if (!activeThreadId || messages.length === 0) return;

    const userMessages = messages.filter((m) => m.role === 'user');
    if (userMessages.length === 0) return;

    const firstUserMessage = userMessages[0];
    const lastMessage = messages[messages.length - 1];

    updateThread(activeThreadId, {
      title: generateTitle(firstUserMessage.content),
      lastMessage: lastMessage.content.slice(0, 50),
      messageCount: messages.length,
    });
  }, [activeThreadId, messages, updateThread, generateTitle]);

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
  const handleSend = useCallback(async (content: string, fileIds?: string[]) => {
    // Auto-create thread if none active
    let threadToUse = activeThreadId;
    if (!threadToUse) {
      threadToUse = createThread(generateTitle(content));
      setActiveThreadId(threadToUse);
    }

    // S75-4: If there are pending uploads, upload them first
    if (attachments.some((a) => a.status === 'pending')) {
      await uploadAll();
    }

    // Get all uploaded file IDs
    const allFileIds = fileIds || getUploadedFileIds();

    // Send message (with optional file IDs for backend to process)
    // TODO: S75-5 - Pass fileIds to backend when it supports attachments
    sendMessage(content).catch((err) => {
      console.error('[UnifiedChat] Failed to send message:', err);
    });

    // Clear attachments after sending
    if (allFileIds.length > 0) {
      clearAttachments();
    }
  }, [activeThreadId, createThread, generateTitle, sendMessage, attachments, uploadAll, getUploadedFileIds, clearAttachments]);

  // S75-4: Handle file attachment
  const handleAttach = useCallback((files: File[]) => {
    addFiles(files);
    // Auto-upload immediately
    uploadAll();
  }, [addFiles, uploadAll]);

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
  const handleApprove = useCallback(async (toolCallId: string) => {
    console.log('[UnifiedChat] Approving tool call:', toolCallId);
    try {
      await approveToolCall(toolCallId);
    } catch (err) {
      console.error('[UnifiedChat] Failed to approve tool call:', err);
    }
  }, [approveToolCall]);

  // Handle tool call rejection
  const handleReject = useCallback(async (toolCallId: string, reason?: string) => {
    console.log('[UnifiedChat] Rejecting tool call:', toolCallId, reason);
    try {
      await rejectToolCall(toolCallId, reason);
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

  // Determine effective mode (currentMode from hook already handles manual override)
  const effectiveMode = currentMode;

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
              'flex-1 flex flex-col bg-white',
              effectiveMode === 'workflow' && 'border-r'
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

            {/* Messages Area - Using ChatArea component with tool support */}
            <ChatArea
              messages={messages}
              isStreaming={isStreaming}
              pendingApprovals={pendingApprovals}
              onApprove={handleApprove}
              onReject={handleReject}
              onDownload={handleDownload}
            />
          </div>

          {/* Workflow Side Panel (Only visible in Workflow mode) */}
          {effectiveMode === 'workflow' && (
            <WorkflowSidePanel
              workflowState={workflowState}
              toolCalls={toolCalls}
              checkpoints={checkpoints}
              onRestoreCheckpoint={handleRestore}
            />
          )}
        </main>

        {/* Input Area - S75-4: Added file attachment support */}
        <ChatInput
          onSend={handleSend}
          isStreaming={isStreaming || isUploading}
          onCancel={handleCancel}
          placeholder={
            effectiveMode === 'chat'
              ? 'Type a message...'
              : 'Describe your task...'
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
        />
      </div>
    </div>
  );
};

export default UnifiedChat;
