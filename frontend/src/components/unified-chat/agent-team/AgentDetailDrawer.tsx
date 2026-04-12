/**
 * AgentDetailDrawer Component
 *
 * Main drawer component for viewing Agent details.
 * Integrates all sub-components for a comprehensive view.
 *
 * Sprint 103: AgentDetailDrawer
 */

import { FC } from 'react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/Sheet';
import { Separator } from '@/components/ui/Separator';
import { AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { AgentDetailHeader } from './AgentDetailHeader';
import { CurrentTask } from './CurrentTask';
import { ToolCallsPanel } from './ToolCallsPanel';
import { MessageHistory } from './MessageHistory';
import { CheckpointPanel } from './CheckpointPanel';
import { ExtendedThinkingPanel } from './ExtendedThinkingPanel';
import { useAgentDetail } from './hooks/useAgentDetail';
import type { UIAgentSummary, AgentDetail } from './types';

// =============================================================================
// Types
// =============================================================================

interface AgentDetailDrawerProps {
  /** Whether the drawer is open */
  open: boolean;
  /** Close handler */
  onClose: () => void;
  /** Team ID */
  teamId: string;
  /** Selected agent summary (used to initiate fetch) */
  agent: UIAgentSummary | null;
  /** External agent detail (optional - for mock/test scenarios) */
  workerDetail?: AgentDetail | null;
  /** Optional class name */
  className?: string;
}

// =============================================================================
// Skeleton Component
// =============================================================================

const Skeleton: FC<{ className?: string }> = ({ className }) => (
  <div className={cn('animate-pulse rounded-md bg-muted', className)} />
);

const LoadingSkeleton: FC = () => (
  <div className="space-y-4 p-4">
    {/* Header skeleton */}
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton className="h-8 w-8" />
        <Skeleton className="h-6 w-48" />
      </div>
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-2 w-32" />
      </div>
      <div className="flex gap-2">
        <Skeleton className="h-5 w-20" />
        <Skeleton className="h-5 w-16" />
      </div>
    </div>

    <Skeleton className="h-[1px] w-full" />

    {/* Task skeleton */}
    <div className="space-y-2">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-16 w-full" />
    </div>

    <Skeleton className="h-[1px] w-full" />

    {/* Tool calls skeleton */}
    <div className="space-y-2">
      <Skeleton className="h-4 w-32" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-24 w-full" />
    </div>

    <Skeleton className="h-[1px] w-full" />

    {/* Messages skeleton */}
    <div className="space-y-2">
      <Skeleton className="h-4 w-36" />
      <Skeleton className="h-20 w-full" />
    </div>
  </div>
);

// =============================================================================
// Error Component
// =============================================================================

interface ErrorDisplayProps {
  error: Error;
  onRetry?: () => void;
}

const ErrorDisplay: FC<ErrorDisplayProps> = ({ error, onRetry }) => (
  <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
    <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
    <h3 className="font-medium text-lg mb-2">Failed to load agent details</h3>
    <p className="text-sm text-muted-foreground mb-4 max-w-sm">
      {error.message}
    </p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="text-sm text-primary hover:underline"
      >
        Try again
      </button>
    )}
  </div>
);

// =============================================================================
// Component
// =============================================================================

/**
 * AgentDetailDrawer - Drawer for viewing Agent details
 *
 * @param open - Whether the drawer is open
 * @param onClose - Close handler
 * @param teamId - Team ID
 * @param agent - Selected agent summary
 * @param agentDetail - External agent detail (optional - for mock/test scenarios)
 * @param className - Additional CSS classes
 */
export const AgentDetailDrawer: FC<AgentDetailDrawerProps> = ({
  open,
  onClose,
  teamId,
  agent,
  workerDetail: externalAgentDetail,
  className,
}) => {
  // Fetch agent details (skip if external detail is provided)
  const {
    agent: fetchedAgentDetail,
    isLoading,
    error,
    refetch,
  } = useAgentDetail({
    teamId,
    agentId: agent?.agentId || '',
    enabled: open && !!agent && !externalAgentDetail,
    // Poll every 2 seconds if agent is running
    pollInterval: agent?.status === 'running' ? 2000 : undefined,
  });

  // Use external detail if provided, otherwise use fetched detail
  const workerDetail = externalAgentDetail || fetchedAgentDetail;

  return (
    <Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <SheetContent
        side="right"
        className={cn(
          'w-full sm:w-[540px] sm:max-w-[90vw] p-0 overflow-hidden',
          className
        )}
      >
        {/* Accessible title (hidden visually) */}
        <SheetHeader className="sr-only">
          <SheetTitle>Agent Details</SheetTitle>
        </SheetHeader>

        {/* Scrollable content area */}
        <div className="h-full overflow-y-auto scrollbar-thin">
          {/* Loading state */}
          {isLoading && !workerDetail && <LoadingSkeleton />}

          {/* Error state */}
          {error && !workerDetail && (
            <ErrorDisplay error={error} onRetry={refetch} />
          )}

          {/* Content */}
          {workerDetail && (
            <div className="p-4 space-y-4">
              {/* Agent Header */}
              <AgentDetailHeader
                agent={workerDetail}
                onBack={onClose}
              />

              <Separator />

              {/* Current Task */}
              <CurrentTask
                taskDescription={workerDetail.taskDescription}
              />

              {/* Extended Thinking (Sprint 104) */}
              {workerDetail.thinkingHistory && workerDetail.thinkingHistory.length > 0 && (
                <>
                  <Separator />
                  <ExtendedThinkingPanel
                    thinkingHistory={workerDetail.thinkingHistory}
                    defaultExpanded={true}
                    autoScroll={true}
                    maxHeight={250}
                  />
                </>
              )}

              <Separator />

              {/* Tool Calls */}
              <ToolCallsPanel
                toolCalls={workerDetail.toolCalls}
              />

              <Separator />

              {/* Message History */}
              <MessageHistory
                messages={workerDetail.messages}
                defaultExpanded={false}
              />

              {/* Checkpoint (if exists) */}
              {workerDetail.checkpointId && (
                <>
                  <Separator />
                  <CheckpointPanel
                    checkpointId={workerDetail.checkpointId}
                    backend={workerDetail.checkpointBackend}
                  />
                </>
              )}

              {/* Error (if agent failed) */}
              {workerDetail.error && (
                <>
                  <Separator />
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm font-medium text-red-500">
                      <AlertCircle className="h-4 w-4" />
                      <span>Error</span>
                    </div>
                    <pre className="text-xs bg-red-50 dark:bg-red-950/50 p-3 rounded-md text-red-600 dark:text-red-400 overflow-x-auto">
                      {workerDetail.error}
                    </pre>
                  </div>
                </>
              )}

              {/* Result (if agent completed) */}
              {workerDetail.result && Object.keys(workerDetail.result).length > 0 && (
                <>
                  <Separator />
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm font-medium text-green-600 dark:text-green-400">
                      <span>Result</span>
                    </div>
                    <pre className="text-xs bg-muted p-3 rounded-md overflow-x-auto max-h-40">
                      {JSON.stringify(workerDetail.result, null, 2)}
                    </pre>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
};

export default AgentDetailDrawer;
