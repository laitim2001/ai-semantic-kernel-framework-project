/**
 * ChatHistoryPanel - Conversation History Panel Component
 *
 * Sprint 74: S74-1 - Chat History Panel
 * Phase 19: UI Enhancement
 * Bug Fix: S74-BF-3 - Add thread rename functionality
 *
 * Displays a list of conversation threads similar to ChatGPT sidebar.
 * Supports:
 * - Thread list with title, last message, timestamp
 * - Active thread highlighting
 * - New chat creation
 * - Thread deletion with confirmation
 * - Thread renaming (S74-BF-3)
 * - Collapsible panel
 */

import { useState, useRef, useEffect } from 'react';
import {
  Plus,
  MessageSquare,
  Trash2,
  Pencil,
  ChevronLeft,
  ChevronRight,
  Check,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/utils';

/**
 * Chat thread data structure
 */
export interface ChatThread {
  id: string;
  title: string;
  lastMessage?: string;
  updatedAt: string;
  messageCount: number;
}

/**
 * Props for ChatHistoryPanel
 */
interface ChatHistoryPanelProps {
  /** List of chat threads */
  threads: ChatThread[];
  /** Currently active thread ID */
  activeThreadId: string | null;
  /** Callback when a thread is selected */
  onSelectThread: (id: string) => void;
  /** Callback when new chat is requested */
  onNewThread: () => void;
  /** Callback when a thread is deleted */
  onDeleteThread: (id: string) => void;
  /** Callback when a thread is renamed (S74-BF-3) */
  onRenameThread?: (id: string, newTitle: string) => void;
  /** Whether the panel is collapsed */
  isCollapsed?: boolean;
  /** Callback to toggle collapse state */
  onToggle?: () => void;
}

/**
 * Individual thread item props
 */
interface ThreadItemProps {
  thread: ChatThread;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onRename?: (newTitle: string) => void;
}

/**
 * Thread item component
 */
function ThreadItem({ thread, isActive, onSelect, onDelete, onRename }: ThreadItemProps) {
  const [showActions, setShowActions] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(thread.title);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when entering edit mode
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleStartEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditTitle(thread.title);
    setIsEditing(true);
  };

  const handleConfirmEdit = () => {
    const trimmed = editTitle.trim();
    if (trimmed && trimmed !== thread.title && onRename) {
      onRename(trimmed);
    }
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditTitle(thread.title);
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleConfirmEdit();
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  return (
    <div
      onClick={isEditing ? undefined : onSelect}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
      className={cn(
        'p-3 cursor-pointer transition-colors relative group',
        isActive
          ? 'bg-blue-50 border-r-2 border-blue-500'
          : 'hover:bg-gray-100',
        isEditing && 'cursor-default'
      )}
    >
      <div className="flex items-start gap-2">
        <MessageSquare className="h-4 w-4 text-gray-400 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0 pr-12">
          {isEditing ? (
            <div className="flex items-center gap-1">
              <input
                ref={inputRef}
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onKeyDown={handleKeyDown}
                onClick={(e) => e.stopPropagation()}
                className="w-full text-sm px-1.5 py-0.5 border border-blue-400 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                maxLength={50}
              />
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleConfirmEdit();
                }}
                className="p-0.5 rounded hover:bg-green-100 text-green-600"
                aria-label="確認"
              >
                <Check className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleCancelEdit();
                }}
                className="p-0.5 rounded hover:bg-red-100 text-red-500"
                aria-label="取消"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : (
            <>
              <div className="font-medium text-sm text-gray-900 truncate">
                {thread.title}
              </div>
              {thread.lastMessage && (
                <div className="text-xs text-gray-500 truncate mt-0.5">
                  {thread.lastMessage}
                </div>
              )}
              <div className="text-xs text-gray-400 mt-1">
                {formatRelativeTime(thread.updatedAt)}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Action buttons - shows on hover (when not editing) */}
      {showActions && !isEditing && (
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-0.5">
          {onRename && (
            <button
              onClick={handleStartEdit}
              className="p-1.5 rounded hover:bg-blue-100 text-gray-400 hover:text-blue-500 transition-colors"
              aria-label="重命名對話"
            >
              <Pencil className="h-3.5 w-3.5" />
            </button>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (confirm('確定要刪除此對話嗎？')) {
                onDelete();
              }
            }}
            className="p-1.5 rounded hover:bg-red-100 text-gray-400 hover:text-red-500 transition-colors"
            aria-label="刪除對話"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * Chat History Panel Component
 */
export function ChatHistoryPanel({
  threads,
  activeThreadId,
  onSelectThread,
  onNewThread,
  onDeleteThread,
  onRenameThread,
  isCollapsed = false,
  onToggle,
}: ChatHistoryPanelProps) {
  return (
    <div
      className={cn(
        'border-r border-gray-200 flex flex-col bg-gray-50 transition-all duration-300',
        isCollapsed ? 'w-0 overflow-hidden' : 'w-64'
      )}
    >
      {/* Header with New Chat button */}
      <div className="p-3 border-b border-gray-200 flex items-center gap-2 shrink-0">
        <Button
          onClick={onNewThread}
          className="flex-1"
          size="sm"
        >
          <Plus className="h-4 w-4 mr-2" />
          新對話
        </Button>
        {onToggle && (
          <button
            onClick={onToggle}
            className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
            aria-label="收起對話記錄"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Thread List */}
      <div className="flex-1 overflow-y-auto">
        {threads.length === 0 ? (
          <div className="p-4 text-center text-gray-500 text-sm">
            <MessageSquare className="h-8 w-8 mx-auto mb-2 text-gray-300" />
            <p>暫無對話記錄</p>
            <p className="text-xs mt-1">點擊「新對話」開始</p>
          </div>
        ) : (
          threads.map((thread) => (
            <ThreadItem
              key={thread.id}
              thread={thread}
              isActive={activeThreadId === thread.id}
              onSelect={() => onSelectThread(thread.id)}
              onDelete={() => onDeleteThread(thread.id)}
              onRename={onRenameThread ? (newTitle) => onRenameThread(thread.id, newTitle) : undefined}
            />
          ))
        )}
      </div>
    </div>
  );
}

/**
 * Collapsed toggle button - use when panel is collapsed
 */
export function ChatHistoryToggleButton({
  onClick,
}: {
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="p-2 border-r border-gray-200 hover:bg-gray-100 transition-colors"
      aria-label="展開對話記錄"
    >
      <ChevronRight className="h-4 w-4" />
    </button>
  );
}

export default ChatHistoryPanel;
