/**
 * MemoryHint - Inline Memory Hint Component
 *
 * Sprint 140: Phase 40 - Memory Management
 *
 * Displays "found N related memories" hint above Chat input.
 * Expandable to show memory summaries. Dismissable.
 */

import { useState } from 'react';
import {
  Brain,
  ChevronDown,
  ChevronUp,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

export interface MemoryHintItem {
  id: string;
  content: string;
  created_at: string;
  score?: number;
}

export interface MemoryHintProps {
  /** Related memories to display */
  memories: MemoryHintItem[];
  /** Whether the hint is visible */
  isVisible: boolean;
  /** Callback to dismiss the hint */
  onDismiss?: () => void;
}

// =============================================================================
// Component
// =============================================================================

export function MemoryHint({
  memories,
  isVisible,
  onDismiss,
}: MemoryHintProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!isVisible || memories.length === 0) return null;

  return (
    <div
      className={cn(
        'mx-4 mb-2 rounded-lg border border-purple-200 bg-purple-50 text-sm',
        'animate-in fade-in slide-in-from-bottom-2 duration-300'
      )}
    >
      {/* Header row */}
      <div className="flex items-center justify-between px-3 py-2">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 text-purple-700 hover:text-purple-900 transition-colors"
        >
          <Brain className="h-3.5 w-3.5" />
          <span className="text-xs font-medium">
            找到 {memories.length} 條相關記憶
          </span>
          {isExpanded ? (
            <ChevronUp className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )}
        </button>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="p-0.5 rounded hover:bg-purple-100 text-purple-400 hover:text-purple-600 transition-colors"
            aria-label="關閉記憶提示"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* Expanded memory list */}
      {isExpanded && (
        <div className="px-3 pb-2 space-y-1.5 border-t border-purple-100 pt-2">
          {memories.map((memory) => {
            const preview =
              memory.content.length > 100
                ? memory.content.slice(0, 100) + '...'
                : memory.content;
            return (
              <div
                key={memory.id}
                className="px-2 py-1.5 rounded bg-white border border-purple-100 text-xs"
              >
                <p className="text-gray-700">{preview}</p>
                <div className="flex items-center gap-2 mt-1 text-gray-400">
                  <span>{formatRelativeTime(memory.created_at)}</span>
                  {memory.score !== undefined && (
                    <span>相關度 {(memory.score * 100).toFixed(0)}%</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default MemoryHint;
