/**
 * CurrentTask Component
 *
 * Displays the current task description for a Worker.
 * Supports expand/collapse for long text.
 *
 * Sprint 103: WorkerDetailDrawer
 */

import { FC, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { ClipboardList, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

interface CurrentTaskProps {
  taskDescription: string;
  maxLength?: number;
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

/**
 * CurrentTask - Displays the current task description
 *
 * @param taskDescription - The task description text
 * @param maxLength - Max characters before truncation (default: 200)
 * @param className - Additional CSS classes
 */
export const CurrentTask: FC<CurrentTaskProps> = ({
  taskDescription,
  maxLength = 200,
  className,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Check if text needs truncation
  const needsTruncation = taskDescription.length > maxLength;

  // Get display text
  const displayText = isExpanded || !needsTruncation
    ? taskDescription
    : `${taskDescription.slice(0, maxLength)}...`;

  if (!taskDescription) {
    return (
      <div className={cn('space-y-2', className)}>
        <div className="flex items-center gap-2 text-sm font-medium">
          <ClipboardList className="h-4 w-4 text-muted-foreground" />
          <span>Current Task</span>
        </div>
        <p className="text-sm text-muted-foreground italic">
          No task description available
        </p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <ClipboardList className="h-4 w-4 text-muted-foreground" />
          <span>Current Task</span>
        </div>
        {needsTruncation && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 text-xs px-2"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? (
              <>
                <ChevronUp className="h-3 w-3 mr-1" />
                Collapse
              </>
            ) : (
              <>
                <ChevronDown className="h-3 w-3 mr-1" />
                Expand
              </>
            )}
          </Button>
        )}
      </div>

      {/* Task description */}
      <div className="bg-muted/50 rounded-md p-3">
        <p className="text-sm leading-relaxed whitespace-pre-wrap">
          {displayText}
        </p>
      </div>
    </div>
  );
};

export default CurrentTask;
