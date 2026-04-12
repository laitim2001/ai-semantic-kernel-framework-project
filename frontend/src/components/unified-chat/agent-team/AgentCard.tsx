/**
 * AgentCard Component
 *
 * Displays a single agent's status in a card format,
 * including name, type, progress, and current action.
 *
 * Sprint 102: AgentTeamPanel + AgentCard
 */

import { FC } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  Search,
  Wrench,
  CheckCircle,
  Clock,
  PlayCircle,
  XCircle,
  Pause,
  ChevronRight,
  Bot,
  Building2,
  Cpu,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AgentCardProps, AgentMemberStatus, AgentType } from './types';

// =============================================================================
// Constants
// =============================================================================

/**
 * Role icon mapping - maps agent roles to icons
 */
const ROLE_ICONS: Record<string, LucideIcon> = {
  diagnostic: Search,
  research: Search,
  remediation: Wrench,
  verification: CheckCircle,
  analysis: Cpu,
  default: Bot,
};

/**
 * Status configuration with icon, colors, and backgrounds
 */
interface StatusConfigItem {
  icon: LucideIcon;
  color: string;
  bgColor: string;
}

const STATUS_CONFIG: Record<AgentMemberStatus, StatusConfigItem> = {
  pending: {
    icon: Clock,
    color: 'text-gray-500',
    bgColor: 'bg-gray-50 dark:bg-gray-900/20',
  },
  running: {
    icon: PlayCircle,
    color: 'text-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
  },
  paused: {
    icon: Pause,
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-50 dark:bg-yellow-900/20',
  },
  completed: {
    icon: CheckCircle,
    color: 'text-green-500',
    bgColor: 'bg-green-50 dark:bg-green-900/20',
  },
  failed: {
    icon: XCircle,
    color: 'text-red-500',
    bgColor: 'bg-red-50 dark:bg-red-900/20',
  },
};

/**
 * Agent type configuration with icon and label
 */
interface TypeConfigItem {
  icon: LucideIcon;
  label: string;
}

const TYPE_CONFIG: Record<AgentType, TypeConfigItem> = {
  claude_sdk: { icon: Bot, label: 'Claude SDK' },
  maf: { icon: Building2, label: 'MAF' },
  hybrid: { icon: Zap, label: 'Hybrid' },
  research: { icon: Search, label: 'Research' },
  custom: { icon: Cpu, label: 'Custom' },
};

// =============================================================================
// Component
// =============================================================================

/**
 * AgentCard - Card showing a single agent's status
 *
 * @param agent - Agent summary data
 * @param index - Agent index for display numbering
 * @param isSelected - Whether this agent is currently selected
 * @param onClick - Click handler for the card
 */
export const AgentCard: FC<AgentCardProps> = ({
  agent,
  index,
  isSelected = false,
  onClick,
}) => {
  // Get configurations
  const RoleIcon = ROLE_ICONS[agent.role.toLowerCase()] || ROLE_ICONS.default;
  const statusConfig = STATUS_CONFIG[agent.status];
  const StatusIcon = statusConfig.icon;
  const typeConfig = TYPE_CONFIG[agent.agentType] || TYPE_CONFIG.custom;
  const TypeIcon = typeConfig.icon;

  // Format index as 2-digit number
  const displayIndex = String(index + 1).padStart(2, '0');

  // Clamp progress between 0 and 100
  const progress = Math.max(0, Math.min(100, agent.progress));

  return (
    <Card
      className={cn(
        'cursor-pointer transition-all duration-200',
        'hover:shadow-md hover:border-primary/50',
        isSelected && 'ring-2 ring-primary',
        statusConfig.bgColor
      )}
      onClick={onClick}
    >
      <CardContent className="p-3 space-y-2">
        {/* Title row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <RoleIcon className={cn('h-4 w-4 flex-shrink-0', statusConfig.color)} />
            <span className="font-medium text-sm truncate">
              {agent.agentName}
            </span>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <StatusIcon
              className={cn(
                'h-4 w-4',
                statusConfig.color,
                agent.status === 'running' && 'animate-pulse'
              )}
            />
            <span className="text-xs font-mono text-muted-foreground">
              {displayIndex}
            </span>
          </div>
        </div>

        {/* Type tags */}
        <div className="flex items-center gap-1 flex-wrap">
          <Badge variant="secondary" className="text-xs h-5 px-1.5">
            <TypeIcon className="h-3 w-3 mr-1" />
            {typeConfig.label}
          </Badge>
          <Badge variant="outline" className="text-xs h-5 px-1.5 capitalize">
            {agent.role}
          </Badge>
        </div>

        {/* Current action */}
        {agent.currentAction && (
          <div className="text-xs text-muted-foreground truncate pl-1">
            <span className="opacity-50">└─</span> {agent.currentAction}
          </div>
        )}

        {/* Progress row */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              {/* Mini progress bar */}
              <div className="relative h-1.5 w-24 overflow-hidden rounded-full bg-secondary">
                <div
                  className={cn(
                    'h-full transition-all duration-300',
                    progress >= 100
                      ? 'bg-green-500'
                      : agent.status === 'failed'
                        ? 'bg-red-500'
                        : 'bg-blue-500'
                  )}
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className="font-mono">{progress}%</span>
            </div>
            <span className="text-muted-foreground">
              ({agent.toolCallsCount} {agent.toolCallsCount === 1 ? 'tool' : 'tools'})
            </span>
          </div>
        </div>

        {/* View button */}
        <div className="flex justify-end pt-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-6 text-xs px-2"
            onClick={(e) => {
              e.stopPropagation();
              onClick?.();
            }}
          >
            View <ChevronRight className="h-3 w-3 ml-1" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default AgentCard;
