/**
 * StatusBar - Unified Chat Status Bar Component
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * S62-1: UnifiedChatWindow Base Architecture
 * Sprint 65: Enhanced metrics display with tool statistics
 *
 * Bottom status bar showing mode, risk level, metrics, and checkpoint status.
 */

import { FC, useMemo } from 'react';
import {
  Clock,
  Coins,
  RotateCcw,
  Shield,
  AlertTriangle,
  AlertOctagon,
  CheckCircle2,
  Wrench,
  MessageSquare,
  Loader2,
} from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/Tooltip';
import type { StatusBarProps, ExecutionMetrics } from '@/types/unified-chat';
import type { RiskLevel } from '@/types/ag-ui';
import { cn } from '@/lib/utils';

/**
 * Get risk level display config
 */
const getRiskConfig = (level: RiskLevel) => {
  switch (level) {
    case 'low':
      return {
        icon: CheckCircle2,
        label: 'Low',
        color: 'text-green-600',
        bgColor: 'bg-green-100',
      };
    case 'medium':
      return {
        icon: Shield,
        label: 'Medium',
        color: 'text-yellow-600',
        bgColor: 'bg-yellow-100',
      };
    case 'high':
      return {
        icon: AlertTriangle,
        label: 'High',
        color: 'text-orange-600',
        bgColor: 'bg-orange-100',
      };
    case 'critical':
      return {
        icon: AlertOctagon,
        label: 'Critical',
        color: 'text-red-600',
        bgColor: 'bg-red-100',
      };
    default:
      return {
        icon: Shield,
        label: 'Unknown',
        color: 'text-gray-600',
        bgColor: 'bg-gray-100',
      };
  }
};

/**
 * Format duration in milliseconds to human-readable string
 */
const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
};

/**
 * Format token count with K suffix for large numbers
 */
const formatTokens = (count: number): string => {
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K`;
  }
  return count.toString();
};

/**
 * StatusBar Component
 *
 * Displays:
 * - Current mode (Chat/Workflow) with source indicator
 * - Risk level with color-coded badge
 * - Token usage (used/limit) with warning colors
 * - Tool call statistics (Sprint 65)
 * - Execution time with running indicator
 * - Checkpoint restore button (if available)
 */
export const StatusBar: FC<StatusBarProps> = ({
  mode,
  modeSource,
  riskLevel,
  riskScore,
  metrics,
  hasCheckpoint,
  canRestore,
  onRestore,
}) => {
  const riskConfig = getRiskConfig(riskLevel);
  const RiskIcon = riskConfig.icon;

  // Calculate token percentage for color coding
  const tokenPercentage = metrics.tokens.percentage;
  const tokenColorClass = useMemo(() => {
    if (tokenPercentage >= 90) return 'text-red-600';
    if (tokenPercentage >= 75) return 'text-orange-600';
    if (tokenPercentage >= 50) return 'text-yellow-600';
    return 'text-gray-600';
  }, [tokenPercentage]);

  // Tool statistics color
  const toolStats = metrics.toolStats;
  const hasActiveTools = toolStats && toolStats.pending > 0;
  const hasFailedTools = toolStats && toolStats.failed > 0;

  return (
    <TooltipProvider>
      <footer
        className="flex items-center justify-between px-4 py-2 border-t bg-gray-50 text-sm"
        data-testid="status-bar"
      >
        {/* Left Section: Mode and Risk */}
        <div className="flex items-center gap-4">
          {/* Mode Indicator */}
          <div className="flex items-center gap-1.5">
            <span className="text-gray-500">Mode:</span>
            <Badge variant="outline" className="font-medium">
              {mode === 'chat' ? 'Chat' : 'Workflow'}
            </Badge>
            {modeSource === 'manual' && (
              <span className="text-xs text-gray-400">(manual)</span>
            )}
          </div>

          {/* Risk Indicator */}
          <div className="flex items-center gap-1.5">
            <span className="text-gray-500">Risk:</span>
            <div
              className={cn(
                'flex items-center gap-1 px-2 py-0.5 rounded-full',
                riskConfig.bgColor
              )}
            >
              <RiskIcon className={cn('h-3.5 w-3.5', riskConfig.color)} />
              <span className={cn('text-xs font-medium', riskConfig.color)}>
                {riskConfig.label}
              </span>
            </div>
            {riskScore !== undefined && (
              <span className="text-xs text-gray-400">
                ({(riskScore * 100).toFixed(0)}%)
              </span>
            )}
          </div>
        </div>

        {/* Right Section: Metrics and Checkpoint */}
        <div className="flex items-center gap-4">
          {/* Token Usage with Tooltip */}
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1.5 cursor-help">
                <Coins className={cn('h-4 w-4', tokenPercentage >= 75 ? 'text-orange-500' : 'text-gray-400')} />
                <span className="text-gray-500">Tokens:</span>
                <span className={tokenColorClass}>
                  {formatTokens(metrics.tokens.used)}/{formatTokens(metrics.tokens.limit)}
                </span>
                {tokenPercentage >= 90 && (
                  <AlertTriangle className="h-3.5 w-3.5 text-red-500" />
                )}
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p>Token usage: {tokenPercentage}%</p>
              <p className="text-xs text-gray-400">
                {metrics.tokens.used.toLocaleString()} / {metrics.tokens.limit.toLocaleString()}
              </p>
            </TooltipContent>
          </Tooltip>

          {/* Tool Statistics (Sprint 65) */}
          {toolStats && (
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-1.5 cursor-help">
                  {hasActiveTools ? (
                    <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
                  ) : (
                    <Wrench className={cn('h-4 w-4', hasFailedTools ? 'text-red-500' : 'text-gray-400')} />
                  )}
                  <span className="text-gray-500">Tools:</span>
                  <span className={cn(
                    hasFailedTools ? 'text-red-600' : hasActiveTools ? 'text-blue-600' : 'text-gray-600'
                  )}>
                    {toolStats.completed}/{toolStats.total}
                  </span>
                  {hasFailedTools && (
                    <span className="text-xs text-red-500">({toolStats.failed} failed)</span>
                  )}
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <div className="space-y-1">
                  <p>Tool Calls</p>
                  <div className="text-xs space-y-0.5">
                    <p className="text-green-500">Completed: {toolStats.completed}</p>
                    {toolStats.pending > 0 && (
                      <p className="text-blue-500">Pending: {toolStats.pending}</p>
                    )}
                    {toolStats.failed > 0 && (
                      <p className="text-red-500">Failed: {toolStats.failed}</p>
                    )}
                  </div>
                </div>
              </TooltipContent>
            </Tooltip>
          )}

          {/* Message Count (Sprint 65) */}
          {metrics.messageStats && (
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-1.5 cursor-help">
                  <MessageSquare className="h-4 w-4 text-gray-400" />
                  <span className="text-gray-600">{metrics.messageStats.total}</span>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <div className="space-y-1">
                  <p>Messages</p>
                  <div className="text-xs space-y-0.5">
                    <p>User: {metrics.messageStats.user}</p>
                    <p>Assistant: {metrics.messageStats.assistant}</p>
                    {metrics.messageStats.tool > 0 && (
                      <p>Tool: {metrics.messageStats.tool}</p>
                    )}
                  </div>
                </div>
              </TooltipContent>
            </Tooltip>
          )}

          {/* Execution Time */}
          <div className="flex items-center gap-1.5">
            <Clock className={cn('h-4 w-4', metrics.time.isRunning ? 'text-blue-500' : 'text-gray-400')} />
            <span className="text-gray-500">Time:</span>
            <span className={metrics.time.isRunning ? 'text-blue-600' : 'text-gray-600'}>
              {formatDuration(metrics.time.total)}
            </span>
            {metrics.time.isRunning && (
              <span className="inline-block w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
            )}
          </div>

          {/* Checkpoint Indicator */}
          {hasCheckpoint && (
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              {canRestore && onRestore ? (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs"
                  onClick={onRestore}
                  data-testid="restore-button"
                >
                  <RotateCcw className="h-3 w-3 mr-1" />
                  Restore
                </Button>
              ) : (
                <span className="text-xs text-green-600">Saved</span>
              )}
            </div>
          )}
        </div>
      </footer>
    </TooltipProvider>
  );
};

export default StatusBar;
