/**
 * AgentTeamStatusBadges Component
 *
 * Displays a compact row of badges showing all agents' status.
 * Useful for quick overview when the full panel is collapsed.
 *
 * Sprint 102: AgentTeamPanel + AgentCard
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
import type { AgentTeamStatusBadgesProps, AgentMemberStatus } from './types';

// =============================================================================
// Constants
// =============================================================================

interface StatusConfigItem {
  icon: LucideIcon;
  color: string;
}

const STATUS_CONFIG: Record<AgentMemberStatus, StatusConfigItem> = {
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
 * AgentTeamStatusBadges - Compact status badges for all agents
 *
 * @param agents - Array of agent summaries
 * @param onAgentClick - Handler when a badge is clicked
 */
export const AgentTeamStatusBadges: FC<AgentTeamStatusBadgesProps> = ({
  agents,
  onAgentClick,
}) => {
  if (agents.length === 0) {
    return null;
  }

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex flex-wrap gap-2 justify-center py-2">
        {agents.map((agent, index) => {
          const statusConfig = STATUS_CONFIG[agent.status];
          const StatusIcon = statusConfig.icon;
          const displayIndex = String(index + 1).padStart(2, '0');

          return (
            <Tooltip key={agent.agentId}>
              <TooltipTrigger asChild>
                <Badge
                  variant="outline"
                  className={cn(
                    'cursor-pointer hover:bg-accent transition-colors',
                    'flex items-center gap-1 px-2 py-1'
                  )}
                  onClick={() => onAgentClick?.(agent)}
                >
                  <User className="h-3 w-3" />
                  <span className="font-mono text-xs">{displayIndex}</span>
                  <StatusIcon className={cn('h-3 w-3', statusConfig.color)} />
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <div className="text-xs">
                  <div className="font-medium">{agent.agentName}</div>
                  <div className="text-muted-foreground capitalize">
                    {agent.status} - {agent.progress}%
                  </div>
                  {agent.currentAction && (
                    <div className="text-muted-foreground mt-1 max-w-[200px] truncate">
                      {agent.currentAction}
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

export default AgentTeamStatusBadges;
