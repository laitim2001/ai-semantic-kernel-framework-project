/**
 * MessageBubble - Chat Message Bubble Component
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-2: Chat Components
 *
 * Displays individual chat messages with role-based styling.
 * Supports user, assistant, system, and tool message types.
 */

import { FC, useMemo } from 'react';
import type { ChatMessage } from '@/types/ag-ui';
import { ToolCallCard } from './ToolCallCard';

export interface MessageBubbleProps {
  /** Chat message to display */
  message: ChatMessage;
  /** Whether this message is currently streaming */
  isStreaming?: boolean;
  /** Callback when tool call action is triggered */
  onToolCallAction?: (toolCallId: string, action: 'approve' | 'reject') => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * MessageBubble Component
 *
 * Renders a chat message with appropriate styling based on the role.
 * Includes embedded tool call cards for tool-related messages.
 */
export const MessageBubble: FC<MessageBubbleProps> = ({
  message,
  isStreaming = false,
  onToolCallAction,
  className = '',
}) => {
  const { role, content, timestamp, toolCalls } = message;

  // Role-based styling
  const bubbleStyles = useMemo(() => {
    switch (role) {
      case 'user':
        return {
          container: 'justify-end',
          bubble: 'bg-blue-600 text-white rounded-br-sm',
          label: 'text-right text-blue-600',
          icon: 'U',
        };
      case 'assistant':
        return {
          container: 'justify-start',
          bubble: 'bg-gray-100 text-gray-900 rounded-bl-sm',
          label: 'text-left text-gray-600',
          icon: 'AI',
        };
      case 'system':
        return {
          container: 'justify-center',
          bubble: 'bg-yellow-50 text-yellow-800 border border-yellow-200 text-sm',
          label: 'text-center text-yellow-600',
          icon: 'S',
        };
      case 'tool':
        return {
          container: 'justify-start',
          bubble: 'bg-purple-50 text-purple-900 border border-purple-200',
          label: 'text-left text-purple-600',
          icon: 'T',
        };
      default:
        return {
          container: 'justify-start',
          bubble: 'bg-gray-100 text-gray-900',
          label: 'text-left text-gray-600',
          icon: '?',
        };
    }
  }, [role]);

  // Format timestamp
  const formattedTime = useMemo(() => {
    if (!timestamp) return '';
    try {
      return new Date(timestamp).toLocaleTimeString('zh-TW', {
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return '';
    }
  }, [timestamp]);

  return (
    <div
      className={`flex ${bubbleStyles.container} mb-4 ${className}`}
      data-testid={`message-bubble-${role}`}
      data-message-id={message.id}
    >
      <div className={`max-w-[80%] ${role === 'system' ? 'max-w-[90%]' : ''}`}>
        {/* Role Label */}
        <div className={`text-xs mb-1 ${bubbleStyles.label}`}>
          <span className="font-medium">
            {role === 'user' ? 'You' : role === 'assistant' ? 'AI Assistant' : role === 'system' ? 'System' : 'Tool'}
          </span>
          {formattedTime && <span className="ml-2 opacity-60">{formattedTime}</span>}
        </div>

        {/* Message Bubble */}
        <div
          className={`px-4 py-3 rounded-2xl ${bubbleStyles.bubble} ${isStreaming ? 'animate-pulse' : ''}`}
        >
          {/* Content */}
          <div className="whitespace-pre-wrap break-words">
            {content || (isStreaming ? '...' : '')}
          </div>

          {/* Embedded Tool Calls */}
          {toolCalls && toolCalls.length > 0 && (
            <div className="mt-3 space-y-2">
              {toolCalls.map((toolCall) => (
                <ToolCallCard
                  key={toolCall.id || toolCall.toolCallId}
                  toolCall={toolCall}
                  compact
                  onAction={onToolCallAction}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
