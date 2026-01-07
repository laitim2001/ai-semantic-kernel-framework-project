/**
 * MessageList - Message List Component
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * S62-3: ChatArea Component
 * Phase 16: Unified Agentic Chat Interface
 *
 * Renders the list of chat messages with tool calls and inline approvals.
 */

import { FC, useMemo } from 'react';
import type { ChatMessage, PendingApproval } from '@/types/ag-ui';
import { MessageBubble } from '@/components/ag-ui/chat/MessageBubble';
import { InlineApproval } from './InlineApproval';

export interface MessageListProps {
  /** List of messages to display */
  messages: ChatMessage[];
  /** Whether the AI is currently streaming a response */
  isStreaming?: boolean;
  /** ID of the message currently being streamed */
  streamingMessageId?: string | null;
  /** List of pending tool call approvals */
  pendingApprovals: PendingApproval[];
  /** Callback when a tool call is approved */
  onApprove: (toolCallId: string) => void;
  /** Callback when a tool call is rejected */
  onReject: (toolCallId: string, reason?: string) => void;
}

/**
 * MessageList Component
 *
 * Renders messages with:
 * - User and assistant message bubbles
 * - Embedded tool call cards
 * - Inline approval buttons for low/medium risk tool calls
 * - Streaming animation for the latest assistant message
 */
export const MessageList: FC<MessageListProps> = ({
  messages,
  isStreaming = false,
  streamingMessageId,
  pendingApprovals,
  onApprove,
  onReject,
}) => {
  // Create a map of tool call IDs to pending approvals for quick lookup
  const approvalsByToolCallId = useMemo(() => {
    const map = new Map<string, PendingApproval>();
    for (const approval of pendingApprovals) {
      map.set(approval.toolCallId, approval);
    }
    return map;
  }, [pendingApprovals]);

  // Handle tool call action from MessageBubble
  const handleToolCallAction = (toolCallId: string, action: 'approve' | 'reject') => {
    if (action === 'approve') {
      onApprove(toolCallId);
    } else {
      onReject(toolCallId);
    }
  };

  return (
    <div className="space-y-2" data-testid="message-list">
      {messages.map((message, index) => {
        const isLastMessage = index === messages.length - 1;
        const isCurrentlyStreaming =
          isStreaming &&
          isLastMessage &&
          message.role === 'assistant' &&
          (streamingMessageId === message.id || !streamingMessageId);

        // Check if this message has any tool calls that need approval
        const messageToolCallApprovals = message.toolCalls
          ?.map((tc) => approvalsByToolCallId.get(tc.toolCallId))
          .filter((a): a is PendingApproval => a !== undefined) ?? [];

        // Filter to only show inline approvals for low/medium risk
        const inlineApprovals = messageToolCallApprovals.filter(
          (a) => a.riskLevel === 'low' || a.riskLevel === 'medium'
        );

        return (
          <div key={message.id || index}>
            {/* Message Bubble */}
            <MessageBubble
              message={message}
              isStreaming={isCurrentlyStreaming}
              onToolCallAction={handleToolCallAction}
            />

            {/* Inline Approvals (for low/medium risk) */}
            {inlineApprovals.length > 0 && (
              <div className="ml-12 mt-2 space-y-2">
                {inlineApprovals.map((approval) => (
                  <InlineApproval
                    key={approval.approvalId}
                    approval={approval}
                    onApprove={() => onApprove(approval.toolCallId)}
                    onReject={(reason) => onReject(approval.toolCallId, reason)}
                  />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default MessageList;
