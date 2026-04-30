/**
 * ModeIndicator - Mode Status Display Component
 *
 * Sprint 63: Mode Switching & State Management
 * S63-3: Real Mode Detection
 * Phase 16: Unified Agentic Chat Interface
 *
 * Displays the current execution mode (Chat/Workflow) with
 * visual indicators and tooltip showing switch details.
 */

import { FC } from 'react';
import { MessageSquare, GitBranch, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/Tooltip';
import { Badge } from '@/components/ui/Badge';
import type { ExecutionMode } from '@/types/unified-chat';

/** Props for ModeIndicator component */
export interface ModeIndicatorProps {
  /** Current effective mode */
  currentMode: ExecutionMode;
  /** Whether mode is manually overridden */
  isManuallyOverridden: boolean;
  /** Reason for the last mode switch */
  switchReason: string | null;
  /** Confidence level of the last auto-detection (0-1) */
  switchConfidence: number;
  /** ISO timestamp of the last mode switch */
  lastSwitchAt: string | null;
  /** Optional click handler for mode toggle */
  onClick?: () => void;
  /** Optional className for styling */
  className?: string;
}

/**
 * ModeIndicator Component
 *
 * Shows the current mode with an icon, badge, and tooltip
 * displaying switch details (reason, confidence, timestamp).
 *
 * @example
 * ```tsx
 * <ModeIndicator
 *   currentMode="workflow"
 *   isManuallyOverridden={false}
 *   switchReason="Complex task detected"
 *   switchConfidence={0.92}
 *   lastSwitchAt="2026-01-07T10:30:00Z"
 * />
 * ```
 */
export const ModeIndicator: FC<ModeIndicatorProps> = ({
  currentMode,
  isManuallyOverridden,
  switchReason,
  switchConfidence,
  lastSwitchAt,
  onClick,
  className,
}) => {
  const isChat = currentMode === 'chat';
  const Icon = isChat ? MessageSquare : GitBranch;

  // Format confidence as percentage
  const confidencePercent = Math.round(switchConfidence * 100);

  // Format timestamp for display
  const formatTimestamp = (isoString: string | null): string => {
    if (!isoString) return 'N/A';
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return 'N/A';
    }
  };

  // Determine badge variant based on mode
  const badgeVariant = isChat ? 'secondary' : 'default';

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={onClick}
            className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-md transition-colors',
              'hover:bg-accent hover:text-accent-foreground',
              'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
              onClick ? 'cursor-pointer' : 'cursor-default',
              className
            )}
            disabled={!onClick}
            aria-label={`Current mode: ${currentMode}${isManuallyOverridden ? ' (manual)' : ' (auto)'}`}
          >
            <Icon className={cn('h-4 w-4', isChat ? 'text-blue-500' : 'text-purple-500')} />
            <Badge variant={badgeVariant} className="capitalize">
              {currentMode}
            </Badge>
            {isManuallyOverridden && (
              <span className="text-xs text-muted-foreground">(manual)</span>
            )}
          </button>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-xs">
          <div className="space-y-2">
            {/* Mode status */}
            <div className="flex items-center gap-2">
              <Icon className="h-4 w-4" />
              <span className="font-medium capitalize">{currentMode} Mode</span>
              {isManuallyOverridden && (
                <Badge variant="outline" className="text-xs">Manual</Badge>
              )}
            </div>

            {/* Divider */}
            <hr className="border-border" />

            {/* Switch details */}
            <div className="space-y-1 text-sm">
              {/* Reason */}
              {switchReason && (
                <div className="flex items-start gap-2">
                  <span className="text-muted-foreground shrink-0">Reason:</span>
                  <span className="text-foreground">{switchReason}</span>
                </div>
              )}

              {/* Confidence */}
              {!isManuallyOverridden && switchConfidence > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Confidence:</span>
                  <div className="flex items-center gap-1">
                    <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className={cn(
                          'h-full rounded-full',
                          confidencePercent >= 90
                            ? 'bg-green-500'
                            : confidencePercent >= 70
                            ? 'bg-yellow-500'
                            : 'bg-red-500'
                        )}
                        style={{ width: `${confidencePercent}%` }}
                      />
                    </div>
                    <span className="text-xs">{confidencePercent}%</span>
                  </div>
                </div>
              )}

              {/* Timestamp */}
              {lastSwitchAt && (
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Switched at:</span>
                  <span className="text-xs font-mono">{formatTimestamp(lastSwitchAt)}</span>
                </div>
              )}
            </div>

            {/* Auto-detection hint */}
            {!isManuallyOverridden && (
              <div className="flex items-center gap-1 text-xs text-muted-foreground pt-1">
                <RefreshCw className="h-3 w-3" />
                <span>Auto-detected by IntentRouter</span>
              </div>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

export default ModeIndicator;
