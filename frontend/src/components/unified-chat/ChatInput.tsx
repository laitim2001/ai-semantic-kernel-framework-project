/**
 * ChatInput - Unified Chat Input Component
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * S62-1: UnifiedChatWindow Base Architecture
 *
 * Input area for sending messages with optional file attachments.
 */

import { FC, useState, useCallback, KeyboardEvent, useRef, useEffect } from 'react';
import { Send, Paperclip, Square, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import type { ChatInputProps } from '@/types/unified-chat';
import { cn } from '@/lib/utils';

/**
 * ChatInput Component
 *
 * Provides a text input area with:
 * - Auto-resizing textarea
 * - Send button (Enter to send, Shift+Enter for newline)
 * - Cancel button during streaming
 * - Optional file attachment support
 */
export const ChatInput: FC<ChatInputProps> = ({
  onSend,
  disabled = false,
  isStreaming = false,
  onCancel,
  placeholder = 'Type a message...',
  attachments = [],
  onAttach,
  onRemoveAttachment,
}) => {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-focus on mount
  useEffect(() => {
    if (!disabled) {
      textareaRef.current?.focus();
    }
  }, [disabled]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [value]);

  // Check if can submit
  const canSubmit = value.trim().length > 0 && !disabled && !isStreaming;

  // Handle send
  const handleSend = useCallback(() => {
    if (!canSubmit) return;

    const content = value.trim();
    setValue('');
    onSend(content);

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [value, canSubmit, onSend]);

  // Handle key down (Enter to send, Shift+Enter for newline)
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  // Handle file attachment click
  const handleAttachClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  // Handle file selection
  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0 && onAttach) {
        onAttach(Array.from(files));
        // Reset input
        e.target.value = '';
      }
    },
    [onAttach]
  );

  return (
    <div className="border-t bg-white" data-testid="chat-input">
      {/* Attachments Preview (future) */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 px-4 pt-2">
          {attachments.map((file) => (
            <div
              key={file.id}
              className="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded text-sm"
            >
              <span className="truncate max-w-[100px]">{file.name}</span>
              {onRemoveAttachment && (
                <button
                  type="button"
                  onClick={() => onRemoveAttachment(file.id)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  &times;
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Input Area */}
      <div className="flex items-end gap-2 p-4">
        {/* Attach Button */}
        {onAttach && (
          <>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-10 w-10 shrink-0"
              onClick={handleAttachClick}
              disabled={disabled || isStreaming}
              data-testid="attach-button"
            >
              <Paperclip className="h-5 w-5" />
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={handleFileChange}
            />
          </>
        )}

        {/* Text Input */}
        <div className="flex-1 relative">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isStreaming ? 'AI is responding...' : placeholder}
            disabled={disabled || isStreaming}
            className={cn(
              'min-h-[44px] max-h-[200px] resize-none py-3 pr-12',
              'focus:ring-2 focus:ring-blue-500 focus:border-transparent',
              isStreaming && 'bg-gray-50'
            )}
            rows={1}
            data-testid="chat-textarea"
          />

          {/* Streaming indicator inside textarea */}
          {isStreaming && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
            </div>
          )}
        </div>

        {/* Send/Cancel Button */}
        {isStreaming && onCancel ? (
          <Button
            type="button"
            variant="destructive"
            size="icon"
            className="h-10 w-10 shrink-0"
            onClick={onCancel}
            data-testid="cancel-button"
          >
            <Square className="h-5 w-5" />
          </Button>
        ) : (
          <Button
            type="button"
            variant="default"
            size="icon"
            className="h-10 w-10 shrink-0"
            onClick={handleSend}
            disabled={!canSubmit}
            data-testid="send-button"
          >
            <Send className="h-5 w-5" />
          </Button>
        )}
      </div>

      {/* Keyboard Hint */}
      <div className="px-4 pb-2 text-xs text-gray-400">
        Press <kbd className="px-1 py-0.5 bg-gray-100 rounded text-gray-500">Enter</kbd> to send,{' '}
        <kbd className="px-1 py-0.5 bg-gray-100 rounded text-gray-500">Shift+Enter</kbd> for new line
      </div>
    </div>
  );
};

export default ChatInput;
