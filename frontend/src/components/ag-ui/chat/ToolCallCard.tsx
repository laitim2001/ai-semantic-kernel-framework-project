/**
 * ToolCallCard - Tool Call Display Card
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-2: Chat Components
 *
 * Displays tool call information including name, arguments, status, and result.
 * Supports approval/rejection actions for HITL workflow.
 */

import { FC, useState, useMemo } from 'react';
import type { ToolCallState, ToolCallStatus } from '@/types/ag-ui';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

export interface ToolCallCardProps {
  /** Tool call state */
  toolCall: ToolCallState;
  /** Compact mode for inline display */
  compact?: boolean;
  /** Show arguments details */
  showArguments?: boolean;
  /** Show result details */
  showResult?: boolean;
  /** Callback for approval/rejection actions */
  onAction?: (toolCallId: string, action: 'approve' | 'reject') => void;
  /** Additional CSS classes */
  className?: string;
}

/** Status badge variant mapping */
const statusConfig: Record<ToolCallStatus, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; label: string }> = {
  pending: { variant: 'secondary', label: 'Pending' },
  executing: { variant: 'default', label: 'Executing' },
  completed: { variant: 'outline', label: 'Completed' },
  failed: { variant: 'destructive', label: 'Failed' },
  requires_approval: { variant: 'secondary', label: 'Requires Approval' },
  approved: { variant: 'default', label: 'Approved' },
  rejected: { variant: 'destructive', label: 'Rejected' },
};

/**
 * ToolCallCard Component
 *
 * Displays tool call details with status indicator and expandable sections.
 */
export const ToolCallCard: FC<ToolCallCardProps> = ({
  toolCall,
  compact = false,
  showArguments = true,
  showResult = true,
  onAction,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const { name, arguments: args, status, result, error, startedAt, completedAt } = toolCall;

  // Format arguments as JSON
  const formattedArgs = useMemo(() => {
    try {
      return JSON.stringify(args, null, 2);
    } catch {
      return String(args);
    }
  }, [args]);

  // Format result as JSON or text
  const formattedResult = useMemo(() => {
    if (result === undefined || result === null) return null;
    try {
      if (typeof result === 'object') {
        return JSON.stringify(result, null, 2);
      }
      return String(result);
    } catch {
      return String(result);
    }
  }, [result]);

  // Get status config
  const statusInfo = statusConfig[status] || statusConfig.pending;

  // Duration calculation
  const duration = useMemo(() => {
    if (!startedAt || !completedAt) return null;
    try {
      const ms = new Date(completedAt).getTime() - new Date(startedAt).getTime();
      return `${ms}ms`;
    } catch {
      return null;
    }
  }, [startedAt, completedAt]);

  // Compact mode rendering
  if (compact) {
    return (
      <div
        className={`flex items-center gap-2 p-2 bg-white rounded border text-sm ${className}`}
        data-testid={`tool-call-card-${toolCall.toolCallId}`}
      >
        <span className="font-mono text-purple-600 font-medium">{name}</span>
        <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
        {status === 'requires_approval' && onAction && (
          <div className="flex gap-1 ml-auto">
            <Button
              size="sm"
              variant="outline"
              onClick={() => onAction(toolCall.toolCallId, 'approve')}
              data-testid={`approve-${toolCall.toolCallId}`}
            >
              Approve
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={() => onAction(toolCall.toolCallId, 'reject')}
              data-testid={`reject-${toolCall.toolCallId}`}
            >
              Reject
            </Button>
          </div>
        )}
      </div>
    );
  }

  // Full mode rendering
  return (
    <div
      className={`border rounded-lg overflow-hidden ${className}`}
      data-testid={`tool-call-card-${toolCall.toolCallId}`}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between p-3 bg-gray-50 cursor-pointer hover:bg-gray-100"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <span className="font-mono text-purple-600 font-medium">{name}</span>
          <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
          {duration && (
            <span className="text-xs text-gray-500">{duration}</span>
          )}
        </div>
        <button
          className="text-gray-400 hover:text-gray-600"
          aria-label={isExpanded ? 'Collapse' : 'Expand'}
        >
          {isExpanded ? '▼' : '▶'}
        </button>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="p-3 space-y-3">
          {/* Arguments */}
          {showArguments && args && Object.keys(args).length > 0 && (
            <div>
              <div className="text-xs font-medium text-gray-500 mb-1">Arguments</div>
              <pre className="p-2 bg-gray-50 rounded text-xs font-mono overflow-x-auto max-h-40">
                {formattedArgs}
              </pre>
            </div>
          )}

          {/* Result */}
          {showResult && formattedResult && (
            <div>
              <div className="text-xs font-medium text-gray-500 mb-1">Result</div>
              <pre className="p-2 bg-green-50 rounded text-xs font-mono overflow-x-auto max-h-40">
                {formattedResult}
              </pre>
            </div>
          )}

          {/* Error */}
          {error && (
            <div>
              <div className="text-xs font-medium text-red-500 mb-1">Error</div>
              <pre className="p-2 bg-red-50 rounded text-xs font-mono text-red-700 overflow-x-auto">
                {error}
              </pre>
            </div>
          )}

          {/* Approval Actions */}
          {status === 'requires_approval' && onAction && (
            <div className="flex gap-2 pt-2 border-t">
              <Button
                variant="default"
                onClick={() => onAction(toolCall.toolCallId, 'approve')}
                data-testid={`approve-${toolCall.toolCallId}`}
              >
                Approve Tool Call
              </Button>
              <Button
                variant="destructive"
                onClick={() => onAction(toolCall.toolCallId, 'reject')}
                data-testid={`reject-${toolCall.toolCallId}`}
              >
                Reject
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ToolCallCard;
