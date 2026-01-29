/**
 * WorkerCardList Component
 *
 * Displays a scrollable list of WorkerCards.
 * Handles empty state and selection.
 *
 * Sprint 102: AgentSwarmPanel + WorkerCard
 */

import { FC } from 'react';
import { WorkerCard } from './WorkerCard';
import type { WorkerCardListProps } from './types';

// =============================================================================
// Component
// =============================================================================

/**
 * WorkerCardList - Scrollable list of worker cards
 *
 * @param workers - Array of worker summaries to display
 * @param selectedWorkerId - Currently selected worker ID
 * @param onWorkerClick - Click handler for worker selection
 */
export const WorkerCardList: FC<WorkerCardListProps> = ({
  workers,
  selectedWorkerId,
  onWorkerClick,
}) => {
  // Empty state
  if (workers.length === 0) {
    return (
      <div className="text-center text-muted-foreground text-sm py-8">
        <p>No workers assigned yet</p>
        <p className="text-xs mt-1 opacity-75">
          Workers will appear when the swarm starts processing
        </p>
      </div>
    );
  }

  return (
    <div className="max-h-[400px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-rounded scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-700">
      <div className="space-y-2">
        {workers.map((worker, index) => (
          <WorkerCard
            key={worker.workerId}
            worker={worker}
            index={index}
            isSelected={worker.workerId === selectedWorkerId}
            onClick={() => onWorkerClick?.(worker)}
          />
        ))}
      </div>
    </div>
  );
};

export default WorkerCardList;
