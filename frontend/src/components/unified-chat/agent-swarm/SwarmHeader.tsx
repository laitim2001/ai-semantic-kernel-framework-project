/**
 * SwarmHeader Component
 *
 * Displays the header section of the Agent Swarm panel,
 * including mode, status, worker count, and start time.
 *
 * Sprint 102: AgentSwarmPanel + WorkerCard
 */

import { FC } from 'react';
import { Badge } from '@/components/ui/Badge';
import {
  Bug,
  Clock,
  PlayCircle,
  CheckCircle,
  XCircle,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SwarmHeaderProps, SwarmMode, SwarmStatus } from './types';

// =============================================================================
// Constants
// =============================================================================

const MODE_LABELS: Record<SwarmMode, string> = {
  sequential: 'Sequential',
  parallel: 'Parallel',
  pipeline: 'Pipeline',
  hierarchical: 'Hierarchical',
  hybrid: 'Hybrid',
};

interface StatusConfigItem {
  icon: typeof Clock;
  color: string;
  label: string;
}

const STATUS_CONFIG: Record<SwarmStatus, StatusConfigItem> = {
  initializing: {
    icon: Loader2,
    color: 'text-yellow-500',
    label: 'Initializing',
  },
  executing: {
    icon: PlayCircle,
    color: 'text-blue-500',
    label: 'Executing',
  },
  aggregating: {
    icon: Clock,
    color: 'text-purple-500',
    label: 'Aggregating',
  },
  completed: {
    icon: CheckCircle,
    color: 'text-green-500',
    label: 'Completed',
  },
  failed: {
    icon: XCircle,
    color: 'text-red-500',
    label: 'Failed',
  },
};

// =============================================================================
// Component
// =============================================================================

/**
 * SwarmHeader - Header section of the Agent Swarm panel
 *
 * @param mode - The swarm execution mode
 * @param status - Current swarm status
 * @param totalWorkers - Total number of workers in the swarm
 * @param startedAt - ISO timestamp when the swarm started
 */
export const SwarmHeader: FC<SwarmHeaderProps> = ({
  mode,
  status,
  totalWorkers,
  startedAt,
}) => {
  const statusConfig = STATUS_CONFIG[status];
  const StatusIcon = statusConfig.icon;

  /**
   * Format ISO timestamp to locale time string
   */
  const formatTime = (isoString?: string): string => {
    if (!isoString) return '--:--:--';
    try {
      const date = new Date(isoString);
      // Check if date is valid (Invalid Date returns NaN for getTime())
      if (isNaN(date.getTime())) {
        return '--:--:--';
      }
      return date.toLocaleTimeString();
    } catch {
      return '--:--:--';
    }
  };

  return (
    <div className="space-y-2">
      {/* Title row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bug className="h-4 w-4 text-amber-500" />
          <span className="font-semibold text-sm">
            AGENT SWARM ({totalWorkers} {totalWorkers === 1 ? 'Worker' : 'Workers'})
          </span>
        </div>
        <Badge variant="outline" className="text-xs">
          {MODE_LABELS[mode]}
        </Badge>
      </div>

      {/* Status row */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <StatusIcon
            className={cn(
              'h-3 w-3',
              statusConfig.color,
              status === 'initializing' && 'animate-spin'
            )}
          />
          <span>{statusConfig.label}</span>
        </div>
        {startedAt && (
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span>Started: {formatTime(startedAt)}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default SwarmHeader;
