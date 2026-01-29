/**
 * OverallProgress Component
 *
 * Displays the overall progress bar for the Agent Swarm,
 * with status-based colors and animation.
 *
 * Sprint 102: AgentSwarmPanel + WorkerCard
 */

import { FC } from 'react';
import { cn } from '@/lib/utils';
import type { OverallProgressProps, SwarmStatus } from './types';

// =============================================================================
// Constants
// =============================================================================

const STATUS_COLORS: Record<SwarmStatus, string> = {
  initializing: 'bg-yellow-500',
  executing: 'bg-blue-500',
  aggregating: 'bg-purple-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
};

// =============================================================================
// Component
// =============================================================================

/**
 * OverallProgress - Progress bar showing overall swarm completion
 *
 * @param progress - Progress percentage (0-100)
 * @param status - Current swarm status (affects color)
 * @param animated - Whether to show animation during execution
 */
export const OverallProgress: FC<OverallProgressProps> = ({
  progress,
  status,
  animated = true,
}) => {
  // Clamp progress between 0 and 100
  const clampedProgress = Math.max(0, Math.min(100, progress));

  return (
    <div className="space-y-1">
      {/* Label row */}
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">Overall Progress</span>
        <span className="font-medium">{clampedProgress}%</span>
      </div>

      {/* Progress bar */}
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-secondary">
        <div
          className={cn(
            'h-full transition-all duration-300 ease-out',
            STATUS_COLORS[status],
            animated && status === 'executing' && 'animate-pulse'
          )}
          style={{ width: `${clampedProgress}%` }}
        />
      </div>
    </div>
  );
};

export default OverallProgress;
