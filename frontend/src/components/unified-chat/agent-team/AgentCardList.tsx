/**
 * AgentCardList Component
 *
 * Displays a scrollable list of AgentCards.
 * Handles empty state and selection.
 *
 * Sprint 102: AgentTeamPanel + AgentCard
 */

import { FC } from 'react';
import { AgentCard } from './AgentCard';
import type { AgentCardListProps } from './types';

// =============================================================================
// Component
// =============================================================================

/**
 * AgentCardList - Scrollable list of agent cards
 *
 * @param agents - Array of agent summaries to display
 * @param selectedAgentId - Currently selected agent ID
 * @param onAgentClick - Click handler for agent selection
 */
export const AgentCardList: FC<AgentCardListProps> = ({
  agents,
  selectedAgentId,
  onAgentClick,
}) => {
  // Empty state
  if (agents.length === 0) {
    return (
      <div className="text-center text-muted-foreground text-sm py-8">
        <p>No agents assigned yet</p>
        <p className="text-xs mt-1 opacity-75">
          Agents will appear when the team starts processing
        </p>
      </div>
    );
  }

  return (
    <div className="max-h-[400px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-rounded scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-700">
      <div className="space-y-2">
        {agents.map((agent, index) => (
          <AgentCard
            key={agent.agentId}
            agent={agent}
            index={index}
            isSelected={agent.agentId === selectedAgentId}
            onClick={() => onAgentClick?.(agent)}
          />
        ))}
      </div>
    </div>
  );
};

export default AgentCardList;
