/**
 * ToolCallTracker - Tool Execution Timeline Component
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * S62-4: WorkflowSidePanel Component
 * Phase 16: Unified Agentic Chat Interface
 *
 * Displays a timeline of tool call executions with status and timing.
 */

import { FC, useMemo } from 'react';
import { Check, Loader2, X, Clock, AlertTriangle, Hourglass } from 'lucide-react';
import type { ToolCallTrackerProps, TrackedToolCall } from '@/types/unified-chat';
import type { ToolCallStatus } from '@/types/ag-ui';
import { cn } from '@/lib/utils';

/**
 * Get status configuration for tool call
 */
const getStatusConfig = (status: ToolCallStatus) => {
  switch (status) {
    case 'completed':
      return {
        icon: Check,
        color: 'text-green-600',
        bgColor: 'bg-green-100',
        label: 'Completed',
      };
    case 'executing':
      return {
        icon: Loader2,
        color: 'text-blue-600',
        bgColor: 'bg-blue-100',
        label: 'Running',
        animate: true,
      };
    case 'failed':
      return {
        icon: X,
        color: 'text-red-600',
        bgColor: 'bg-red-100',
        label: 'Failed',
      };
    case 'requires_approval':
    case 'pending':
      return {
        icon: Hourglass,
        color: 'text-yellow-600',
        bgColor: 'bg-yellow-100',
        label: status === 'requires_approval' ? 'Needs Approval' : 'Pending',
      };
    case 'approved':
      return {
        icon: Check,
        color: 'text-green-600',
        bgColor: 'bg-green-100',
        label: 'Approved',
      };
    case 'rejected':
      return {
        icon: AlertTriangle,
        color: 'text-orange-600',
        bgColor: 'bg-orange-100',
        label: 'Rejected',
      };
    default:
      return {
        icon: Clock,
        color: 'text-gray-400',
        bgColor: 'bg-gray-100',
        label: 'Unknown',
      };
  }
};

/**
 * Format duration in milliseconds
 */
const formatDuration = (ms?: number): string => {
  if (ms === undefined || ms === null) return '--';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
};

/**
 * ToolCallTracker Component
 *
 * Displays a timeline of tool calls with:
 * - Tool name and status icon
 * - Execution duration (if showTimings enabled)
 * - Error messages for failed calls
 */
export const ToolCallTracker: FC<ToolCallTrackerProps> = ({
  toolCalls,
  maxVisible = 10,
  showTimings = false,
}) => {
  // Sort by most recent first and limit
  const displayedCalls = useMemo(() => {
    const sorted = [...toolCalls].sort((a, b) => {
      const timeA = a.startedAt ? new Date(a.startedAt).getTime() : 0;
      const timeB = b.startedAt ? new Date(b.startedAt).getTime() : 0;
      return timeB - timeA;
    });
    return sorted.slice(0, maxVisible);
  }, [toolCalls, maxVisible]);

  // If no tool calls, show empty state
  if (toolCalls.length === 0) {
    return (
      <div className="text-sm text-gray-400 text-center py-4">
        <div className="text-2xl mb-2">🔧</div>
        No tool calls yet
      </div>
    );
  }

  const hiddenCount = toolCalls.length - displayedCalls.length;

  return (
    <div className="space-y-2" data-testid="tool-call-tracker">
      {/* Tool Call List */}
      <div className="space-y-1">
        {displayedCalls.map((toolCall, index) => (
          <ToolCallItem
            key={toolCall.id || toolCall.toolCallId || index}
            toolCall={toolCall}
            showTiming={showTimings}
          />
        ))}
      </div>

      {/* Hidden count indicator */}
      {hiddenCount > 0 && (
        <div className="text-xs text-gray-400 text-center pt-2">
          +{hiddenCount} more tool calls
        </div>
      )}
    </div>
  );
};

/**
 * Individual Tool Call Item
 */
interface ToolCallItemProps {
  toolCall: TrackedToolCall;
  showTiming: boolean;
}

const ToolCallItem: FC<ToolCallItemProps> = ({ toolCall, showTiming }) => {
  const config = getStatusConfig(toolCall.status);
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'flex items-center gap-2 p-2 rounded-lg',
        config.bgColor
      )}
      data-testid="tool-call-item"
      data-status={toolCall.status}
    >
      {/* Status Icon */}
      <div className="flex-shrink-0">
        <Icon
          className={cn(
            'h-4 w-4',
            config.color,
            config.animate && 'animate-spin'
          )}
        />
      </div>

      {/* Tool Info */}
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-gray-700 truncate">
          {toolCall.name}
        </div>
        {toolCall.error && (
          <div className="text-xs text-red-600 truncate" title={toolCall.error}>
            {toolCall.error}
          </div>
        )}
      </div>

      {/* Duration */}
      {showTiming && (
        <div className="flex-shrink-0 text-xs text-gray-500">
          {formatDuration(toolCall.duration)}
        </div>
      )}
    </div>
  );
};

export default ToolCallTracker;
