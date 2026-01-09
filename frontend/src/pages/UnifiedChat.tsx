/**
 * UnifiedChat - Unified Agentic Chat Interface Page
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * S62-1: UnifiedChatWindow Base Architecture
 * S62-3: AG-UI Integration (Updated)
 * Sprint 66: S66-3 - Default tool configuration for Agentic functionality
 * Sprint 69: S69-4 - Dashboard Layout Integration (h-full instead of h-screen)
 * Sprint 73: S73-1 - Token/Time Metrics Fix
 * Sprint 74: S74-3 - Chat History Panel Integration
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

// localStorage key for active thread ID
const ACTIVE_THREAD_KEY = 'ipa_active_thread_id';

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
  // S74-3: Chat history panel collapse state
  const [historyCollapsed, setHistoryCollapsed] = useState(false);

  // S74-2/3: Thread management
  const {
    threads,
    createThread,
    updateThread,
    deleteThread,
    generateTitle,
  } = useChatThreads();

  // S74-3: Active thread ID - try to restore from localStorage
  const [activeThreadId, setActiveThreadId] = useState<string | null>(() => {
    if (initialThreadId) return initialThreadId;
    try {
      return localStorage.getItem(ACTIVE_THREAD_KEY);
    } catch {
      return null;
    }
  });

  // Persist active thread ID to localStorage
  useEffect(() => {
    if (activeThreadId) {
      try {
        localStorage.setItem(ACTIVE_THREAD_KEY, activeThreadId);
      } catch {
        // Ignore storage errors
      }
    }
  }, [activeThreadId]);

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

  // S73-1: Start/stop timer based on streaming state
  useEffect(() => {
    if (isStreaming) {
      startTimer();
    } else {
      stopTimer();
    }
  }, [isStreaming, startTimer, stopTimer]);

  // Derive metrics from hook state
  // S73-1: Use executionTime from useExecutionMetrics instead of hardcoded value
  const metrics: ExecutionMetrics = useMemo(() => ({
    tokens: {
      used: tokenUsage.used,
      limit: tokenUsage.limit,
      percentage: (tokenUsage.used / tokenUsage.limit) * 100,
    },
    time: executionTime,
    toolCallCount: toolCalls.length,
    messageCount: messages.length,
  }), [tokenUsage, executionTime, toolCalls.length, messages.length]);

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
  const handleNewThread = useCallback(() => {
    const newId = createThread();
    setActiveThreadId(newId);
    clearMessages();
    resetTimer();
  }, [createThread, clearMessages, resetTimer]);

  // S74-3: Handle thread selection
  const handleSelectThread = useCallback((id: string) => {
    if (id === activeThreadId) return;
    setActiveThreadId(id);
    clearMessages();
    resetTimer();
    // Note: Messages will be loaded via useUnifiedChat when threadId changes
  }, [activeThreadId, clearMessages, resetTimer]);

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

  // S74-3: Handle send message with auto thread creation
  const handleSend = useCallback((content: string) => {
    // Auto-create thread if none active
    let threadToUse = activeThreadId;
    if (!threadToUse) {
      threadToUse = createThread(generateTitle(content));
      setActiveThreadId(threadToUse);
    }

    sendMessage(content).catch((err) => {
      console.error('[UnifiedChat] Failed to send message:', err);
    });
  }, [activeThreadId, createThread, generateTitle, sendMessage]);

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

        {/* Input Area */}
        <ChatInput
          onSend={handleSend}
          isStreaming={isStreaming}
          onCancel={handleCancel}
          placeholder={
            effectiveMode === 'chat'
              ? 'Type a message...'
              : 'Describe your task...'
          }
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
