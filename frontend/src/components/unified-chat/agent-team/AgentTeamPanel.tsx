/**
 * AgentTeamPanel Component
 *
 * Main panel for displaying Agent Team status.
 * Integrates AgentTeamHeader, OverallProgress, and AgentCardList.
 *
 * Sprint 102: AgentTeamPanel + AgentCard
 */

import { FC } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { cn } from '@/lib/utils';
import { AgentTeamHeader } from './AgentTeamHeader';
import { OverallProgress } from './OverallProgress';
import { AgentCardList } from './AgentCardList';
import { ConversationLog } from './ConversationLog';
import { useAgentTeamStore, selectAgentEvents } from '@/stores/agentTeamStore';
import type { AgentTeamPanelProps } from './types';

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
        <p className="text-sm font-medium">No active Agent Team</p>
        <p className="text-xs opacity-75">
          A team will appear when multi-agent coordination starts
        </p>
      </div>
    </CardContent>
  </Card>
);

// =============================================================================
// Main Component
// =============================================================================

/**
 * AgentTeamPanel - Main panel showing team status
 *
 * @param agentTeamStatus - Current team status data (null if no active team)
 * @param onAgentClick - Handler when a agent card is clicked
 * @param isLoading - Whether data is loading
 * @param className - Additional CSS classes
 */
export const AgentTeamPanel: FC<AgentTeamPanelProps> = ({
  agentTeamStatus,
  onAgentClick,
  isLoading = false,
  className,
}) => {
  // Subscribe to conversation log events and route type from store
  const agentEvents = useAgentTeamStore(selectAgentEvents);
  const routeType = useAgentTeamStore((s) => s.routeType);

  // Loading state
  if (isLoading) {
    return <LoadingState className={className} />;
  }

  // Empty state
  if (!agentTeamStatus) {
    return <EmptyState className={className} />;
  }

  // Active team state
  return (
    <Card className={cn('w-full', className)}>
      <CardHeader className="pb-2">
        <AgentTeamHeader
          mode={agentTeamStatus.mode}
          status={agentTeamStatus.status}
          totalAgents={agentTeamStatus.totalAgents}
          startedAt={agentTeamStatus.startedAt}
          routeType={routeType}
        />
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Overall progress */}
        <OverallProgress
          progress={agentTeamStatus.overallProgress}
          status={agentTeamStatus.status}
        />

        {/* Agent list */}
        <div className="border-t pt-4">
          <AgentCardList
            agents={agentTeamStatus.agents}
            onAgentClick={onAgentClick}
          />
        </div>

        {/* Conversation Log (Phase 45: Sprint E) */}
        {agentEvents.length > 0 && (
          <div className="border-t pt-4">
            <ConversationLog
              events={agentEvents}
              maxHeight="280px"
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default AgentTeamPanel;
