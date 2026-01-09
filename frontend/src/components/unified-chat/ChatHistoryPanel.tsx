/**
 * ChatHistoryPanel - Conversation History Panel Component
 *
 * Sprint 74: S74-1 - Chat History Panel
 * Phase 19: UI Enhancement
 *
 * Displays a list of conversation threads similar to ChatGPT sidebar.
 * Supports:
 * - Thread list with title, last message, timestamp
 * - Active thread highlighting
 * - New chat creation
 * - Thread deletion with confirmation
 * - Collapsible panel
 */

import { useState } from 'react';
import {
  Plus,
  MessageSquare,
  Trash2,
  ChevronLeft,
  ChevronRight,
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
}

/**
 * Thread item component
 */
function ThreadItem({ thread, isActive, onSelect, onDelete }: ThreadItemProps) {
  const [showDelete, setShowDelete] = useState(false);

  return (
    <div
      onClick={onSelect}
      onMouseEnter={() => setShowDelete(true)}
      onMouseLeave={() => setShowDelete(false)}
      className={cn(
        'p-3 cursor-pointer transition-colors relative group',
        isActive
          ? 'bg-blue-50 border-r-2 border-blue-500'
          : 'hover:bg-gray-100'
      )}
    >
      <div className="flex items-start gap-2">
        <MessageSquare className="h-4 w-4 text-gray-400 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0 pr-6">
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
        </div>
      </div>

      {/* Delete button - shows on hover */}
      {showDelete && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (confirm('確定要刪除此對話嗎？')) {
              onDelete();
            }
          }}
          className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded hover:bg-red-100 text-gray-400 hover:text-red-500 transition-colors"
          aria-label="刪除對話"
        >
          <Trash2 className="h-4 w-4" />
        </button>
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
