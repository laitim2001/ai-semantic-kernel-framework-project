/**
 * ChatArea - Main Conversation Area Component
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * S62-3: ChatArea Component
 * Phase 16: Unified Agentic Chat Interface
 *
 * Main chat area displaying messages, tool calls, and inline approvals.
 */

import { FC, useRef, useEffect } from 'react';
import type { ChatAreaProps } from '@/types/unified-chat';
import { MessageList } from './MessageList';
import { StreamingIndicator } from '@/components/ag-ui/chat/StreamingIndicator';

/**
 * ChatArea Component
 *
 * Container for the conversation area with:
 * - Message list with auto-scroll
 * - Streaming indicator during AI responses
 * - Empty state for new conversations
 *
 * Adapts to available width based on parent container (Chat vs Workflow mode).
 */
export const ChatArea: FC<ChatAreaProps> = ({
  messages,
  isStreaming,
  streamingMessageId,
  pendingApprovals,
  onApprove,
  onReject,
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages or streaming updates
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  // Check if there are any messages
  const hasMessages = messages.length > 0;

  return (
    <div
      className="flex-1 flex flex-col overflow-hidden bg-white"
      data-testid="chat-area"
    >
      {/* Messages Container */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto"
      >
        {hasMessages ? (
          <div className="p-4 space-y-1">
            <MessageList
              messages={messages}
              isStreaming={isStreaming}
              streamingMessageId={streamingMessageId}
              pendingApprovals={pendingApprovals}
              onApprove={onApprove}
              onReject={onReject}
            />

            {/* Streaming Indicator */}
            {isStreaming && !streamingMessageId && (
              <div className="flex justify-start pl-4 py-2">
                <StreamingIndicator isStreaming={isStreaming} />
              </div>
            )}

            {/* Scroll anchor */}
            <div ref={messagesEndRef} />
          </div>
        ) : (
          <EmptyState />
        )}
      </div>
    </div>
  );
};

/**
 * Empty State Component
 *
 * Displayed when there are no messages in the conversation.
 */
const EmptyState: FC = () => (
  <div className="flex items-center justify-center h-full text-gray-400">
    <div className="text-center px-8 max-w-md">
      <div className="text-6xl mb-6">💬</div>
      <h2 className="text-xl font-medium text-gray-600 mb-3">
        Start a conversation
      </h2>
      <p className="text-sm text-gray-400 leading-relaxed">
        Type a message below to begin chatting with the AI assistant.
        You can ask questions, request help with tasks, or start a workflow.
      </p>
      <div className="mt-6 flex justify-center gap-4 text-xs text-gray-400">
        <div className="flex items-center gap-1">
          <span className="text-lg">💡</span>
          <span>Ask questions</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-lg">📋</span>
          <span>Run workflows</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-lg">🔧</span>
          <span>Execute tools</span>
        </div>
      </div>
    </div>
  </div>
);

export default ChatArea;
