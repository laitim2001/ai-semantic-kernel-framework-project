/**
 * ToolCallsPanel Component
 *
 * Displays a list of tool calls for a Worker.
 * Sprint 103: WorkerDetailDrawer
 */

import { FC } from 'react';
import { Wrench } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ToolCallItem } from './ToolCallItem';
import type { ToolCallInfo } from './types';

// =============================================================================
// Types
// =============================================================================

interface ToolCallsPanelProps {
  toolCalls: ToolCallInfo[];
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

/**
 * ToolCallsPanel - Displays all tool calls for a Worker
 *
 * @param toolCalls - Array of tool call information
 * @param className - Additional CSS classes
 */
export const ToolCallsPanel: FC<ToolCallsPanelProps> = ({
  toolCalls,
  className,
}) => {
  // Count by status
  const completedCount = toolCalls.filter(tc => tc.status === 'completed').length;
  const failedCount = toolCalls.filter(tc => tc.status === 'failed').length;
  const runningCount = toolCalls.filter(tc => tc.status === 'running').length;

  return (
    <div className={cn('space-y-3', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Wrench className="h-4 w-4 text-muted-foreground" />
          <span>Tool Calls ({toolCalls.length})</span>
        </div>

        {toolCalls.length > 0 && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {completedCount > 0 && (
              <span className="text-green-600 dark:text-green-400">
                {completedCount} completed
              </span>
            )}
            {runningCount > 0 && (
              <span className="text-blue-600 dark:text-blue-400">
                {runningCount} running
              </span>
            )}
            {failedCount > 0 && (
              <span className="text-red-600 dark:text-red-400">
                {failedCount} failed
              </span>
            )}
          </div>
        )}
      </div>

      {/* Tool calls list */}
      {toolCalls.length === 0 ? (
        <div className="text-center text-muted-foreground text-sm py-6 bg-muted/30 rounded-md">
          <Wrench className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>No tool calls yet</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1 scrollbar-thin">
          {toolCalls.map((toolCall, index) => (
            <ToolCallItem
              key={toolCall.toolCallId || `tc-${index}`}
              toolCall={toolCall}
              defaultExpanded={index === 0}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default ToolCallsPanel;
