/**
 * ToolCallItem Component
 *
 * Displays a single tool call with expandable input/output details.
 * Sprint 103: WorkerDetailDrawer
 */

import { FC, useState } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/Collapsible';
import {
  Cloud,
  Terminal,
  CheckCircle,
  Clock,
  XCircle,
  Loader2,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ToolCallInfo } from './types';

// =============================================================================
// Types
// =============================================================================

interface ToolCallItemProps {
  toolCall: ToolCallInfo;
  defaultExpanded?: boolean;
}

// =============================================================================
// Constants
// =============================================================================

type ToolCallStatus = 'pending' | 'running' | 'completed' | 'failed';

interface StatusConfigItem {
  icon: typeof Clock;
  color: string;
  label: string;
}

const STATUS_CONFIG: Record<ToolCallStatus, StatusConfigItem> = {
  pending: { icon: Clock, color: 'text-gray-500', label: 'Pending' },
  running: { icon: Loader2, color: 'text-blue-500', label: 'Running' },
  completed: { icon: CheckCircle, color: 'text-green-500', label: 'Completed' },
  failed: { icon: XCircle, color: 'text-red-500', label: 'Failed' },
};

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Format duration in milliseconds to human-readable string
 */
function formatDuration(ms?: number): string {
  if (ms === undefined || ms === null) return '--';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

/**
 * Format JSON object for display
 */
function formatJson(obj: Record<string, unknown>): string {
  try {
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
}

/**
 * Check if tool is an MCP tool
 */
function isMcpTool(toolName: string): boolean {
  return toolName.includes(':') || toolName.startsWith('mcp_');
}

// =============================================================================
// Component
// =============================================================================

/**
 * ToolCallItem - Displays a single tool call
 *
 * @param toolCall - Tool call information
 * @param defaultExpanded - Whether to expand by default
 */
export const ToolCallItem: FC<ToolCallItemProps> = ({
  toolCall,
  defaultExpanded = false,
}) => {
  const [isOpen, setIsOpen] = useState(defaultExpanded);

  const statusConfig = STATUS_CONFIG[toolCall.status];
  const StatusIcon = statusConfig.icon;
  const ToolIcon = isMcpTool(toolCall.toolName) ? Cloud : Terminal;

  return (
    <Card className="overflow-hidden">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className="w-full justify-between p-3 h-auto hover:bg-accent rounded-none"
          >
            {/* Left side - Tool icon and name */}
            <div className="flex items-center gap-2 min-w-0">
              <ToolIcon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
              <span className="font-mono text-sm truncate">
                {toolCall.toolName}
              </span>
            </div>

            {/* Right side - Status and duration */}
            <div className="flex items-center gap-2 flex-shrink-0">
              <StatusIcon
                className={cn(
                  'h-4 w-4',
                  statusConfig.color,
                  toolCall.status === 'running' && 'animate-spin'
                )}
              />
              {toolCall.durationMs !== undefined && (
                <span className="text-xs text-muted-foreground font-mono">
                  {formatDuration(toolCall.durationMs)}
                </span>
              )}
              {isOpen ? (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
          </Button>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <CardContent className="p-3 pt-0 space-y-3 border-t">
            {/* Input */}
            <div>
              <div className="text-xs font-medium text-muted-foreground mb-1">
                Input:
              </div>
              <pre className="text-xs bg-muted p-2 rounded-md overflow-x-auto max-h-32 scrollbar-thin">
                {formatJson(toolCall.inputArgs)}
              </pre>
            </div>

            {/* Output */}
            {toolCall.outputResult && Object.keys(toolCall.outputResult).length > 0 && (
              <div>
                <div className="text-xs font-medium text-muted-foreground mb-1">
                  Output:
                </div>
                <pre className="text-xs bg-muted p-2 rounded-md overflow-x-auto max-h-40 scrollbar-thin">
                  {formatJson(toolCall.outputResult)}
                </pre>
              </div>
            )}

            {/* Error */}
            {toolCall.error && (
              <div>
                <div className="text-xs font-medium text-red-500 mb-1">
                  Error:
                </div>
                <pre className="text-xs bg-red-50 dark:bg-red-950/50 p-2 rounded-md text-red-600 dark:text-red-400 overflow-x-auto">
                  {toolCall.error}
                </pre>
              </div>
            )}

            {/* Timestamps */}
            {(toolCall.startedAt || toolCall.completedAt) && (
              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                {toolCall.startedAt && (
                  <span>Started: {new Date(toolCall.startedAt).toLocaleTimeString()}</span>
                )}
                {toolCall.completedAt && (
                  <span>Completed: {new Date(toolCall.completedAt).toLocaleTimeString()}</span>
                )}
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
};

export default ToolCallItem;
