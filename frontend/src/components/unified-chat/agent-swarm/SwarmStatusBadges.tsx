/**
 * SwarmStatusBadges Component
 *
 * Displays a compact row of badges showing all workers' status.
 * Useful for quick overview when the full panel is collapsed.
 *
 * Sprint 102: AgentSwarmPanel + WorkerCard
 */

import { FC } from 'react';
import { Badge } from '@/components/ui/Badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/Tooltip';
import {
  CheckCircle,
  Clock,
  PlayCircle,
  XCircle,
  Pause,
  User,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SwarmStatusBadgesProps, WorkerStatus } from './types';

// =============================================================================
// Constants
// =============================================================================

interface StatusConfigItem {
  icon: LucideIcon;
  color: string;
}

const STATUS_CONFIG: Record<WorkerStatus, StatusConfigItem> = {
  pending: { icon: Clock, color: 'text-gray-400' },
  running: { icon: PlayCircle, color: 'text-blue-500' },
  paused: { icon: Pause, color: 'text-yellow-500' },
  completed: { icon: CheckCircle, color: 'text-green-500' },
  failed: { icon: XCircle, color: 'text-red-500' },
};

// =============================================================================
// Component
// =============================================================================

/**
 * SwarmStatusBadges - Compact status badges for all workers
 *
 * @param workers - Array of worker summaries
 * @param onWorkerClick - Handler when a badge is clicked
 */
export const SwarmStatusBadges: FC<SwarmStatusBadgesProps> = ({
  workers,
  onWorkerClick,
}) => {
  if (workers.length === 0) {
    return null;
  }

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex flex-wrap gap-2 justify-center py-2">
        {workers.map((worker, index) => {
          const statusConfig = STATUS_CONFIG[worker.status];
          const StatusIcon = statusConfig.icon;
          const displayIndex = String(index + 1).padStart(2, '0');

          return (
            <Tooltip key={worker.workerId}>
              <TooltipTrigger asChild>
                <Badge
                  variant="outline"
                  className={cn(
                    'cursor-pointer hover:bg-accent transition-colors',
                    'flex items-center gap-1 px-2 py-1'
                  )}
                  onClick={() => onWorkerClick?.(worker)}
                >
                  <User className="h-3 w-3" />
                  <span className="font-mono text-xs">{displayIndex}</span>
                  <StatusIcon className={cn('h-3 w-3', statusConfig.color)} />
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <div className="text-xs">
                  <div className="font-medium">{worker.workerName}</div>
                  <div className="text-muted-foreground capitalize">
                    {worker.status} - {worker.progress}%
                  </div>
                  {worker.currentAction && (
                    <div className="text-muted-foreground mt-1 max-w-[200px] truncate">
                      {worker.currentAction}
                    </div>
                  )}
                </div>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    </TooltipProvider>
  );
};

export default SwarmStatusBadges;
