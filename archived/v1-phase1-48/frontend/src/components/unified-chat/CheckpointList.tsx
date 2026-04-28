/**
 * CheckpointList - Checkpoint Management Component
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * S62-4: WorkflowSidePanel Component
 * Phase 16: Unified Agentic Chat Interface
 *
 * Displays available checkpoints with restore functionality.
 */

import { FC, useMemo, useState, useCallback } from 'react';
import { RotateCcw, Clock, BookmarkCheck, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import type { CheckpointListProps, Checkpoint } from '@/types/unified-chat';
import { cn } from '@/lib/utils';

/**
 * Format timestamp to relative time
 */
const formatRelativeTime = (timestamp: string): string => {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  return then.toLocaleDateString('zh-TW');
};

/**
 * CheckpointList Component
 *
 * Displays checkpoints with:
 * - Timestamp and optional label
 * - Current checkpoint indicator
 * - Restore button (if canRestore is true)
 * - Expandable list for many checkpoints
 */
export const CheckpointList: FC<CheckpointListProps> = ({
  checkpoints,
  currentCheckpoint,
  onRestore,
  maxVisible = 5,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [restoringId, setRestoringId] = useState<string | null>(null);

  // Sort by most recent first
  const sortedCheckpoints = useMemo(() => {
    return [...checkpoints].sort((a, b) => {
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    });
  }, [checkpoints]);

  // Determine which checkpoints to show
  const displayedCheckpoints = useMemo(() => {
    if (isExpanded) return sortedCheckpoints;
    return sortedCheckpoints.slice(0, maxVisible);
  }, [sortedCheckpoints, isExpanded, maxVisible]);

  const hasMore = sortedCheckpoints.length > maxVisible;

  // Handle restore with loading state
  const handleRestore = useCallback(
    async (checkpointId: string) => {
      setRestoringId(checkpointId);
      try {
        await onRestore(checkpointId);
      } finally {
        setRestoringId(null);
      }
    },
    [onRestore]
  );

  // If no checkpoints, show empty state
  if (checkpoints.length === 0) {
    return (
      <div className="text-sm text-gray-400 text-center py-4">
        <div className="text-2xl mb-2">📍</div>
        No checkpoints saved
      </div>
    );
  }

  return (
    <div className="space-y-2" data-testid="checkpoint-list">
      {/* Checkpoint List */}
      <div className="space-y-1">
        {displayedCheckpoints.map((checkpoint) => (
          <CheckpointItem
            key={checkpoint.id}
            checkpoint={checkpoint}
            isCurrent={checkpoint.id === currentCheckpoint}
            isRestoring={restoringId === checkpoint.id}
            onRestore={() => handleRestore(checkpoint.id)}
          />
        ))}
      </div>

      {/* Expand/Collapse Button */}
      {hasMore && (
        <Button
          variant="ghost"
          size="sm"
          className="w-full text-xs"
          onClick={() => setIsExpanded((prev) => !prev)}
        >
          {isExpanded ? (
            <>
              <ChevronUp className="h-3 w-3 mr-1" />
              Show less
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3 mr-1" />
              Show {sortedCheckpoints.length - maxVisible} more
            </>
          )}
        </Button>
      )}
    </div>
  );
};

/**
 * Individual Checkpoint Item
 */
interface CheckpointItemProps {
  checkpoint: Checkpoint;
  isCurrent: boolean;
  isRestoring: boolean;
  onRestore: () => void;
}

const CheckpointItem: FC<CheckpointItemProps> = ({
  checkpoint,
  isCurrent,
  isRestoring,
  onRestore,
}) => {
  return (
    <div
      className={cn(
        'flex items-center gap-2 p-2 rounded-lg transition-colors',
        isCurrent ? 'bg-green-50 border border-green-200' : 'bg-gray-100 hover:bg-gray-150'
      )}
      data-testid="checkpoint-item"
      data-checkpoint-id={checkpoint.id}
    >
      {/* Icon */}
      <div className="flex-shrink-0">
        <BookmarkCheck
          className={cn(
            'h-4 w-4',
            isCurrent ? 'text-green-600' : 'text-gray-400'
          )}
        />
      </div>

      {/* Checkpoint Info */}
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-gray-700 truncate">
          {checkpoint.label || `Checkpoint`}
        </div>
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <Clock className="h-3 w-3" />
          {formatRelativeTime(checkpoint.timestamp)}
          {checkpoint.stepIndex !== undefined && (
            <span className="ml-1">@ Step {checkpoint.stepIndex + 1}</span>
          )}
        </div>
      </div>

      {/* Current Indicator or Restore Button */}
      {isCurrent ? (
        <span className="text-xs text-green-600 font-medium">Current</span>
      ) : checkpoint.canRestore ? (
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs"
          onClick={onRestore}
          disabled={isRestoring}
        >
          {isRestoring ? (
            <div className="h-3 w-3 border border-gray-400 border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <RotateCcw className="h-3 w-3 mr-1" />
              Restore
            </>
          )}
        </Button>
      ) : null}
    </div>
  );
};

export default CheckpointList;
