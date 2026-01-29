/**
 * WorkerDetailDrawer Component
 *
 * Main drawer component for viewing Worker details.
 * Integrates all sub-components for a comprehensive view.
 *
 * Sprint 103: WorkerDetailDrawer
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
import { WorkerDetailHeader } from './WorkerDetailHeader';
import { CurrentTask } from './CurrentTask';
import { ToolCallsPanel } from './ToolCallsPanel';
import { MessageHistory } from './MessageHistory';
import { CheckpointPanel } from './CheckpointPanel';
import { useWorkerDetail } from './hooks/useWorkerDetail';
import type { UIWorkerSummary } from './types';

// =============================================================================
// Types
// =============================================================================

interface WorkerDetailDrawerProps {
  /** Whether the drawer is open */
  open: boolean;
  /** Close handler */
  onClose: () => void;
  /** Swarm ID */
  swarmId: string;
  /** Selected worker summary (used to initiate fetch) */
  worker: UIWorkerSummary | null;
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
    <h3 className="font-medium text-lg mb-2">Failed to load worker details</h3>
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
 * WorkerDetailDrawer - Drawer for viewing Worker details
 *
 * @param open - Whether the drawer is open
 * @param onClose - Close handler
 * @param swarmId - Swarm ID
 * @param worker - Selected worker summary
 * @param className - Additional CSS classes
 */
export const WorkerDetailDrawer: FC<WorkerDetailDrawerProps> = ({
  open,
  onClose,
  swarmId,
  worker,
  className,
}) => {
  // Fetch worker details
  const {
    worker: workerDetail,
    isLoading,
    error,
    refetch,
  } = useWorkerDetail({
    swarmId,
    workerId: worker?.workerId || '',
    enabled: open && !!worker,
    // Poll every 2 seconds if worker is running
    pollInterval: worker?.status === 'running' ? 2000 : undefined,
  });

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
          <SheetTitle>Worker Details</SheetTitle>
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
              {/* Worker Header */}
              <WorkerDetailHeader
                worker={workerDetail}
                onBack={onClose}
              />

              <Separator />

              {/* Current Task */}
              <CurrentTask
                taskDescription={workerDetail.taskDescription}
              />

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

              {/* Error (if worker failed) */}
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

              {/* Result (if worker completed) */}
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

export default WorkerDetailDrawer;
