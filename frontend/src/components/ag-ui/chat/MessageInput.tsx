/**
 * MessageInput - Chat Message Input Component
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-2: Chat Components
 *
 * Input field for composing and sending chat messages.
 * Supports multi-line input with Enter to send and Shift+Enter for new line.
 */

import { FC, useState, useCallback, KeyboardEvent, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';

export interface MessageInputProps {
  /** Callback when message is sent */
  onSend: (content: string) => void;
  /** Whether input is disabled */
  disabled?: boolean;
  /** Placeholder text */
  placeholder?: string;
  /** Maximum character length */
  maxLength?: number;
  /** Whether currently streaming (shows cancel option) */
  isStreaming?: boolean;
  /** Callback to cancel streaming */
  onCancel?: () => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * MessageInput Component
 *
 * Provides a text input area with send button for chat interactions.
 * Auto-resizes based on content and handles keyboard shortcuts.
 */
export const MessageInput: FC<MessageInputProps> = ({
  onSend,
  disabled = false,
  placeholder = 'Type a message...',
  maxLength = 4000,
  isStreaming = false,
  onCancel,
  className = '',
}) => {
  const [content, setContent] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [content]);

  // Handle send action
  const handleSend = useCallback(() => {
    const trimmedContent = content.trim();
    if (!trimmedContent || disabled) return;

    onSend(trimmedContent);
    setContent('');

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [content, disabled, onSend]);

  // Handle keyboard events
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      // Enter to send (without Shift)
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  // Character count
  const charCount = content.length;
  const isNearLimit = charCount > maxLength * 0.9;
  const isOverLimit = charCount > maxLength;

  return (
    <div className={`flex flex-col gap-2 ${className}`} data-testid="message-input">
      <div className="flex gap-2 items-end">
        {/* Textarea */}
        <div className="flex-1 relative">
          <Textarea
            ref={textareaRef}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled || isStreaming}
            className="min-h-[44px] max-h-[200px] resize-none pr-12"
            data-testid="message-input-textarea"
            aria-label="Message input"
            rows={1}
          />
          {/* Character count */}
          {isNearLimit && (
            <span
              className={`absolute bottom-2 right-3 text-xs ${
                isOverLimit ? 'text-red-500' : 'text-gray-400'
              }`}
            >
              {charCount}/{maxLength}
            </span>
          )}
        </div>

        {/* Action Button */}
        {isStreaming ? (
          <Button
            variant="destructive"
            onClick={onCancel}
            disabled={!onCancel}
            data-testid="cancel-button"
            aria-label="Cancel streaming"
          >
            Cancel
          </Button>
        ) : (
          <Button
            onClick={handleSend}
            disabled={disabled || !content.trim() || isOverLimit}
            data-testid="send-button"
            aria-label="Send message"
          >
            Send
          </Button>
        )}
      </div>

      {/* Hint text */}
      <div className="text-xs text-gray-400 px-1">
        Press <kbd className="px-1 py-0.5 bg-gray-100 rounded text-gray-600">Enter</kbd> to send,{' '}
        <kbd className="px-1 py-0.5 bg-gray-100 rounded text-gray-600">Shift + Enter</kbd> for new line
      </div>
    </div>
  );
};

export default MessageInput;
