/**
 * WorkerDetailHeader Component
 *
 * Header section for the Worker Detail Drawer.
 * Displays worker name, status, progress, and type.
 *
 * Sprint 103: WorkerDetailDrawer
 */

import { FC } from 'react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  ArrowLeft,
  Search,
  Wrench,
  CheckCircle,
  Clock,
  PlayCircle,
  XCircle,
  Pause,
  Bot,
  Building2,
  Zap,
  Cpu,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { WorkerDetail, WorkerStatus, WorkerType } from './types';

// =============================================================================
// Types
// =============================================================================

interface WorkerDetailHeaderProps {
  worker: WorkerDetail;
  onBack?: () => void;
}

// =============================================================================
// Constants
// =============================================================================

const ROLE_ICONS: Record<string, LucideIcon> = {
  diagnostic: Search,
  research: Search,
  remediation: Wrench,
  verification: CheckCircle,
  analysis: Cpu,
  default: Bot,
};

interface StatusConfigItem {
  icon: LucideIcon;
  color: string;
  label: string;
}

const STATUS_CONFIG: Record<WorkerStatus, StatusConfigItem> = {
  pending: { icon: Clock, color: 'text-gray-500', label: 'Pending' },
  running: { icon: PlayCircle, color: 'text-blue-500', label: 'Running' },
  paused: { icon: Pause, color: 'text-yellow-500', label: 'Paused' },
  completed: { icon: CheckCircle, color: 'text-green-500', label: 'Completed' },
  failed: { icon: XCircle, color: 'text-red-500', label: 'Failed' },
};

interface TypeConfigItem {
  icon: LucideIcon;
  label: string;
}

const TYPE_CONFIG: Record<WorkerType, TypeConfigItem> = {
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
 * WorkerDetailHeader - Header for Worker Detail Drawer
 *
 * @param worker - Worker detail data
 * @param onBack - Back button click handler
 */
export const WorkerDetailHeader: FC<WorkerDetailHeaderProps> = ({
  worker,
  onBack,
}) => {
  const RoleIcon = ROLE_ICONS[worker.role.toLowerCase()] || ROLE_ICONS.default;
  const statusConfig = STATUS_CONFIG[worker.status];
  const StatusIcon = statusConfig.icon;
  const typeConfig = TYPE_CONFIG[worker.workerType] || TYPE_CONFIG.custom;
  const TypeIcon = typeConfig.icon;

  // Clamp progress
  const progress = Math.max(0, Math.min(100, worker.progress));

  return (
    <div className="space-y-3">
      {/* Top row - Back button and Worker name */}
      <div className="flex items-center gap-3">
        {onBack && (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={onBack}
          >
            <ArrowLeft className="h-4 w-4" />
            <span className="sr-only">Back</span>
          </Button>
        )}
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <RoleIcon className={cn('h-5 w-5 flex-shrink-0', statusConfig.color)} />
          <h2 className="font-semibold text-lg truncate">
            {worker.workerName}
          </h2>
        </div>
      </div>

      {/* Status and Progress row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <StatusIcon
            className={cn(
              'h-4 w-4',
              statusConfig.color,
              worker.status === 'running' && 'animate-pulse'
            )}
          />
          <span className="text-sm text-muted-foreground">
            {statusConfig.label}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Mini progress bar */}
          <div className="relative h-2 w-24 overflow-hidden rounded-full bg-secondary">
            <div
              className={cn(
                'h-full transition-all duration-300',
                progress >= 100
                  ? 'bg-green-500'
                  : worker.status === 'failed'
                    ? 'bg-red-500'
                    : 'bg-blue-500'
              )}
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="text-sm font-mono">{progress}%</span>
        </div>
      </div>

      {/* Type and Role badges */}
      <div className="flex items-center gap-2 flex-wrap">
        <Badge variant="secondary" className="text-xs">
          <TypeIcon className="h-3 w-3 mr-1" />
          {typeConfig.label}
        </Badge>
        <Badge variant="outline" className="text-xs capitalize">
          {worker.role}
        </Badge>
        {worker.toolCallsCount > 0 && (
          <Badge variant="outline" className="text-xs">
            {worker.toolCallsCount} {worker.toolCallsCount === 1 ? 'tool' : 'tools'}
          </Badge>
        )}
      </div>
    </div>
  );
};

export default WorkerDetailHeader;
