/**
 * MessageList - Message List Component
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * S62-3: ChatArea Component
 * Sprint 65: S65-4 - UI Polish & Accessibility
 * Phase 16: Unified Agentic Chat Interface
 *
 * Renders the list of chat messages with tool calls and inline approvals.
 * Enhanced with animations and accessibility features.
 */

import { FC, useMemo, useEffect, useState, useRef, useCallback } from 'react';
import type { ChatMessage, PendingApproval, UIComponentEvent } from '@/types/ag-ui';
import { MessageBubble } from '@/components/ag-ui/chat/MessageBubble';
import { CustomUIRenderer } from '@/components/ag-ui/advanced/CustomUIRenderer';
import { InlineApproval } from './InlineApproval';
import { cn } from '@/lib/utils';

// Check for reduced motion preference
const prefersReducedMotion = () => {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
};

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
  /** Sprint 65: S65-5 - Callback when a custom UI component emits an event */
  onUIEvent?: (event: UIComponentEvent) => void;
}

/**
 * MessageList Component
 *
 * Renders messages with:
 * - User and assistant message bubbles
 * - Embedded tool call cards
 * - Inline approval buttons for low/medium risk tool calls
 * - Streaming animation for the latest assistant message
 * - Entrance animations (respects prefers-reduced-motion)
 * - ARIA announcements for screen readers
 */
export const MessageList: FC<MessageListProps> = ({
  messages,
  isStreaming = false,
  streamingMessageId,
  pendingApprovals,
  onApprove,
  onReject,
  onUIEvent,
}) => {
  // Track new messages for animation
  const [animatedIds, setAnimatedIds] = useState<Set<string>>(new Set());
  const prevMessagesLength = useRef(messages.length);
  const reduceMotion = useMemo(() => prefersReducedMotion(), []);

  // Track new messages for entrance animation
  useEffect(() => {
    if (messages.length > prevMessagesLength.current) {
      const newMessageIds = messages
        .slice(prevMessagesLength.current)
        .map((m) => m.id)
        .filter((id): id is string => !!id);

      if (newMessageIds.length > 0) {
        setAnimatedIds((prev) => {
          const next = new Set(prev);
          newMessageIds.forEach((id) => next.add(id));
          return next;
        });

        // Remove from animated set after animation completes
        setTimeout(() => {
          setAnimatedIds((prev) => {
            const next = new Set(prev);
            newMessageIds.forEach((id) => next.delete(id));
            return next;
          });
        }, 400);
      }
    }
    prevMessagesLength.current = messages.length;
  }, [messages]);
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

  // Sprint 65: S65-5 - Handle custom UI events
  const handleUIEvent = useCallback(
    (event: UIComponentEvent) => {
      onUIEvent?.(event);
    },
    [onUIEvent]
  );

  // Animation classes
  const getAnimationClasses = (messageId: string | undefined) => {
    if (reduceMotion || !messageId) return '';
    if (animatedIds.has(messageId)) {
      return 'animate-message-enter';
    }
    return '';
  };

  return (
    <div
      className="space-y-2"
      data-testid="message-list"
      role="log"
      aria-live="polite"
      aria-label="Chat messages"
    >
      {/* Screen reader announcement for new messages */}
      <div className="sr-only" aria-live="assertive">
        {isStreaming && 'AI is typing a response...'}
      </div>

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

        // Message aria label
        const messageLabel =
          message.role === 'user'
            ? `You said: ${message.content?.substring(0, 50)}${message.content && message.content.length > 50 ? '...' : ''}`
            : `AI response: ${message.content?.substring(0, 50)}${message.content && message.content.length > 50 ? '...' : ''}`;

        return (
          <div
            key={message.id || index}
            className={cn(
              'transition-all duration-300',
              getAnimationClasses(message.id)
            )}
            role="article"
            aria-label={messageLabel}
          >
            {/* Sprint 65: S65-5 - Render CustomUIRenderer if message has customUI */}
            {message.customUI ? (
              <div className="mx-4 my-2">
                <CustomUIRenderer
                  definition={message.customUI}
                  onEvent={handleUIEvent}
                  className="max-w-2xl"
                />
              </div>
            ) : (
              /* Standard Message Bubble */
              <MessageBubble
                message={message}
                isStreaming={isCurrentlyStreaming}
                onToolCallAction={handleToolCallAction}
              />
            )}

            {/* Inline Approvals (for low/medium risk) - only show for non-customUI messages */}
            {!message.customUI && inlineApprovals.length > 0 && (
              <div
                className="ml-12 mt-2 space-y-2"
                role="group"
                aria-label="Tool call approvals"
              >
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
