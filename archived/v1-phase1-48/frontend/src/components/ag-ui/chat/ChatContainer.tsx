/**
 * ChatContainer - Complete Chat Interface Container
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-2: Chat Components
 *
 * Main chat interface that combines all chat components.
 * Integrates with useAGUI hook for complete AG-UI functionality.
 */

import { FC, useRef, useEffect, useCallback } from 'react';
import type { ToolDefinition, ChatMessage, PendingApproval } from '@/types/ag-ui';
import { useAGUI } from '@/hooks/useAGUI';
import { MessageBubble } from './MessageBubble';
import { MessageInput } from './MessageInput';
import { StreamingIndicator } from './StreamingIndicator';
import { Badge } from '@/components/ui/Badge';

export interface ChatContainerProps {
  /** Thread ID for conversation isolation */
  threadId: string;
  /** Session ID (optional) */
  sessionId?: string;
  /** Available tools */
  tools?: ToolDefinition[];
  /** Execution mode */
  mode?: 'auto' | 'workflow' | 'chat' | 'hybrid';
  /** API base URL */
  apiUrl?: string;
  /** Callback when error occurs */
  onError?: (error: Error) => void;
  /** Callback when message is sent */
  onMessageSent?: (message: ChatMessage) => void;
  /** Callback when approval is required */
  onApprovalRequired?: (approval: PendingApproval) => void;
  /** Show connection status */
  showStatus?: boolean;
  /** Show debug info */
  debug?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * ChatContainer Component
 *
 * Complete chat interface with message list, input, and status indicators.
 * Automatically manages SSE connection and message streaming.
 */
export const ChatContainer: FC<ChatContainerProps> = ({
  threadId,
  sessionId,
  tools = [],
  mode = 'auto',
  apiUrl,
  onError,
  onMessageSent,
  onApprovalRequired,
  showStatus = true,
  debug = false,
  className = '',
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize AG-UI hook
  const {
    connectionStatus,
    isConnected,
    isStreaming,
    runState,
    isRunning,
    messages,
    addUserMessage,
    toolCalls,
    pendingApprovals,
    approveToolCall,
    rejectToolCall,
    runAgent,
    cancelRun,
  } = useAGUI({
    threadId,
    sessionId,
    tools,
    mode,
    apiUrl,
    onApprovalRequired,
    onRunComplete: (success, error) => {
      if (!success && error && onError) {
        onError(new Error(error));
      }
    },
  });

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  // Handle send message
  const handleSend = useCallback(
    async (content: string) => {
      const message = addUserMessage(content);
      onMessageSent?.(message);

      try {
        await runAgent({ prompt: content });
      } catch (error) {
        onError?.(error as Error);
      }
    },
    [addUserMessage, runAgent, onMessageSent, onError]
  );

  // Handle tool call action
  const handleToolCallAction = useCallback(
    async (toolCallId: string, action: 'approve' | 'reject') => {
      const approval = pendingApprovals.find((a) => a.toolCallId === toolCallId);
      if (!approval) return;

      if (action === 'approve') {
        await approveToolCall(approval.approvalId);
      } else {
        await rejectToolCall(approval.approvalId);
      }
    },
    [pendingApprovals, approveToolCall, rejectToolCall]
  );

  // Connection status indicator
  const statusBadgeVariant = {
    disconnected: 'secondary' as const,
    connecting: 'secondary' as const,
    connected: 'default' as const,
    error: 'destructive' as const,
  };

  return (
    <div
      className={`flex flex-col h-full bg-white rounded-lg border ${className}`}
      data-testid="chat-container"
    >
      {/* Header */}
      {showStatus && (
        <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
          <div className="flex items-center gap-2">
            <span className="font-medium">Chat</span>
            <Badge variant={statusBadgeVariant[connectionStatus]}>
              {connectionStatus}
            </Badge>
            {isRunning && (
              <Badge variant="default">Running</Badge>
            )}
          </div>
          <div className="text-xs text-gray-500">
            Thread: {threadId.slice(0, 8)}...
          </div>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center">
              <div className="text-4xl mb-2">💬</div>
              <div>Start a conversation</div>
              <div className="text-sm">Type a message below to begin</div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, index) => (
              <MessageBubble
                key={message.id || index}
                message={message}
                isStreaming={isStreaming && index === messages.length - 1 && message.role === 'assistant'}
                onToolCallAction={handleToolCallAction}
              />
            ))}
          </>
        )}

        {/* Streaming Indicator */}
        {isStreaming && (
          <div className="flex justify-start mb-4">
            <StreamingIndicator isStreaming={isStreaming} />
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Pending Approvals Banner */}
      {pendingApprovals.length > 0 && (
        <div className="px-4 py-2 bg-yellow-50 border-t border-yellow-200">
          <div className="flex items-center gap-2 text-yellow-800">
            <span className="text-sm font-medium">
              {pendingApprovals.length} pending approval{pendingApprovals.length > 1 ? 's' : ''}
            </span>
            <Badge variant="secondary">Action Required</Badge>
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="border-t p-4">
        <MessageInput
          onSend={handleSend}
          disabled={!isConnected && connectionStatus !== 'disconnected'}
          isStreaming={isStreaming}
          onCancel={cancelRun}
          placeholder={
            isStreaming
              ? 'AI is responding...'
              : 'Type a message...'
          }
        />
      </div>

      {/* Debug Panel */}
      {debug && (
        <div className="border-t p-2 bg-gray-50 text-xs font-mono">
          <div>Thread: {threadId}</div>
          <div>Status: {connectionStatus}</div>
          <div>Run State: {runState.status}</div>
          <div>Messages: {messages.length}</div>
          <div>Tool Calls: {toolCalls.length}</div>
          <div>Pending Approvals: {pendingApprovals.length}</div>
        </div>
      )}
    </div>
  );
};

export default ChatContainer;
