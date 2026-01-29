/**
 * ToolCallItem Component
 *
 * Displays a single tool call with expandable input/output details.
 * Sprint 103: WorkerDetailDrawer
 * Sprint 104: Enhanced with real-time timer and animations
 */

import { FC, useState, useEffect, useRef } from 'react';
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
  Timer,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ToolCallInfo } from './types';

// =============================================================================
// Types
// =============================================================================

interface ToolCallItemProps {
  toolCall: ToolCallInfo;
  defaultExpanded?: boolean;
  /** Enable real-time elapsed timer for running tools */
  showLiveTimer?: boolean;
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
// Live Timer Hook (Sprint 104)
// =============================================================================

/**
 * Hook for real-time elapsed time tracking
 */
function useLiveTimer(startTime: string | undefined, isActive: boolean): number | null {
  const [elapsed, setElapsed] = useState<number | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (isActive && startTime) {
      const startMs = new Date(startTime).getTime();

      // Initial calculation
      setElapsed(Date.now() - startMs);

      // Update every 100ms for smooth display
      intervalRef.current = setInterval(() => {
        setElapsed(Date.now() - startMs);
      }, 100);

      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    } else {
      setElapsed(null);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    }
  }, [startTime, isActive]);

  return elapsed;
}

// =============================================================================
// Component
// =============================================================================

/**
 * ToolCallItem - Displays a single tool call with real-time updates
 *
 * Sprint 104 Enhancements:
 * - Real-time elapsed timer for running tools
 * - Status transition animations
 * - Improved visual feedback
 *
 * @param toolCall - Tool call information
 * @param defaultExpanded - Whether to expand by default
 * @param showLiveTimer - Enable live timer for running tools (default: true)
 */
export const ToolCallItem: FC<ToolCallItemProps> = ({
  toolCall,
  defaultExpanded = false,
  showLiveTimer = true,
}) => {
  const [isOpen, setIsOpen] = useState(defaultExpanded);
  const [prevStatus, setPrevStatus] = useState<ToolCallStatus>(toolCall.status);

  // Real-time timer for running tools
  const isRunning = toolCall.status === 'running';
  const liveElapsed = useLiveTimer(toolCall.startedAt, isRunning && showLiveTimer);

  // Track status changes for animation
  useEffect(() => {
    if (prevStatus !== toolCall.status) {
      setPrevStatus(toolCall.status);
    }
  }, [toolCall.status, prevStatus]);

  const statusConfig = STATUS_CONFIG[toolCall.status];
  const StatusIcon = statusConfig.icon;
  const ToolIcon = isMcpTool(toolCall.toolName) ? Cloud : Terminal;

  // Determine displayed duration
  const displayedDuration = isRunning && liveElapsed !== null
    ? liveElapsed
    : toolCall.durationMs;

  return (
    <Card
      className={cn(
        'overflow-hidden transition-all duration-300',
        // Status-based styling (Sprint 104)
        isRunning && 'ring-2 ring-blue-400/50 shadow-lg shadow-blue-500/10',
        toolCall.status === 'completed' && 'border-green-200 dark:border-green-800/50',
        toolCall.status === 'failed' && 'border-red-200 dark:border-red-800/50',
      )}
    >
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className={cn(
              'w-full justify-between p-3 h-auto hover:bg-accent rounded-none',
              // Running state background pulse
              isRunning && 'animate-pulse bg-blue-50/50 dark:bg-blue-950/30',
            )}
          >
            {/* Left side - Tool icon and name */}
            <div className="flex items-center gap-2 min-w-0">
              <ToolIcon className={cn(
                'h-4 w-4 flex-shrink-0 transition-colors',
                isRunning ? 'text-blue-500' : 'text-muted-foreground',
              )} />
              <span className="font-mono text-sm truncate">
                {toolCall.toolName}
              </span>
            </div>

            {/* Right side - Status and duration */}
            <div className="flex items-center gap-2 flex-shrink-0">
              {/* Live timer indicator */}
              {isRunning && showLiveTimer && (
                <Timer className="h-3 w-3 text-blue-500 animate-pulse" />
              )}

              <StatusIcon
                className={cn(
                  'h-4 w-4 transition-all',
                  statusConfig.color,
                  isRunning && 'animate-spin',
                  // Completion animation
                  toolCall.status === 'completed' && 'scale-110',
                )}
              />

              {/* Duration display - real-time for running, final for completed */}
              {(displayedDuration !== undefined && displayedDuration !== null) && (
                <span className={cn(
                  'text-xs font-mono tabular-nums min-w-[50px] text-right',
                  isRunning ? 'text-blue-500 font-medium' : 'text-muted-foreground',
                )}>
                  {formatDuration(displayedDuration)}
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
