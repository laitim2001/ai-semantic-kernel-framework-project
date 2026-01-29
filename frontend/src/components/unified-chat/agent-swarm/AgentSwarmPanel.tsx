/**
 * AgentSwarmPanel Component
 *
 * Main panel for displaying Agent Swarm status.
 * Integrates SwarmHeader, OverallProgress, and WorkerCardList.
 *
 * Sprint 102: AgentSwarmPanel + WorkerCard
 */

import { FC } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { cn } from '@/lib/utils';
import { SwarmHeader } from './SwarmHeader';
import { OverallProgress } from './OverallProgress';
import { WorkerCardList } from './WorkerCardList';
import type { AgentSwarmPanelProps } from './types';

// =============================================================================
// Skeleton Component (inline for loading state)
// =============================================================================

const Skeleton: FC<{ className?: string }> = ({ className }) => (
  <div
    className={cn('animate-pulse rounded-md bg-muted', className)}
  />
);

// =============================================================================
// Loading State Component
// =============================================================================

const LoadingState: FC<{ className?: string }> = ({ className }) => (
  <Card className={cn('w-full', className)}>
    <CardHeader className="pb-2">
      <Skeleton className="h-4 w-48" />
      <Skeleton className="h-3 w-32 mt-2" />
    </CardHeader>
    <CardContent className="space-y-4">
      {/* Progress skeleton */}
      <div className="space-y-1">
        <div className="flex justify-between">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-3 w-8" />
        </div>
        <Skeleton className="h-2 w-full" />
      </div>
      {/* Card skeletons */}
      <div className="border-t pt-4 space-y-2">
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-28 w-full" />
      </div>
    </CardContent>
  </Card>
);

// =============================================================================
// Empty State Component
// =============================================================================

const EmptyState: FC<{ className?: string }> = ({ className }) => (
  <Card className={cn('w-full', className)}>
    <CardContent className="py-8 text-center text-muted-foreground">
      <div className="flex flex-col items-center gap-2">
        <svg
          className="h-12 w-12 opacity-50"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <p className="text-sm font-medium">No active Agent Swarm</p>
        <p className="text-xs opacity-75">
          A swarm will appear when multi-agent coordination starts
        </p>
      </div>
    </CardContent>
  </Card>
);

// =============================================================================
// Main Component
// =============================================================================

/**
 * AgentSwarmPanel - Main panel showing swarm status
 *
 * @param swarmStatus - Current swarm status data (null if no active swarm)
 * @param onWorkerClick - Handler when a worker card is clicked
 * @param isLoading - Whether data is loading
 * @param className - Additional CSS classes
 */
export const AgentSwarmPanel: FC<AgentSwarmPanelProps> = ({
  swarmStatus,
  onWorkerClick,
  isLoading = false,
  className,
}) => {
  // Loading state
  if (isLoading) {
    return <LoadingState className={className} />;
  }

  // Empty state
  if (!swarmStatus) {
    return <EmptyState className={className} />;
  }

  // Active swarm state
  return (
    <Card className={cn('w-full', className)}>
      <CardHeader className="pb-2">
        <SwarmHeader
          mode={swarmStatus.mode}
          status={swarmStatus.status}
          totalWorkers={swarmStatus.totalWorkers}
          startedAt={swarmStatus.startedAt}
        />
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Overall progress */}
        <OverallProgress
          progress={swarmStatus.overallProgress}
          status={swarmStatus.status}
        />

        {/* Worker list */}
        <div className="border-t pt-4">
          <WorkerCardList
            workers={swarmStatus.workers}
            onWorkerClick={onWorkerClick}
          />
        </div>
      </CardContent>
    </Card>
  );
};

export default AgentSwarmPanel;
