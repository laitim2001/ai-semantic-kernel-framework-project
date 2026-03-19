/**
 * TaskProgressCard - Inline Task Progress Component
 *
 * Sprint 139: Phase 40 - Task Dashboard
 *
 * Displays task progress inline within chat messages.
 * Features: progress bar, step list, auto-refresh, link to detail page.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle2,
  XCircle,
  Circle,
  Loader2,
  SkipForward,
  ChevronDown,
  ChevronUp,
  ExternalLink,
} from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import { cn } from '@/lib/utils';
import { useTask } from '@/hooks/useTasks';
import type { TaskStatus, TaskStepStatus, TaskStep } from '@/api/endpoints/tasks';

// =============================================================================
// Types
// =============================================================================

export interface TaskProgressCardProps {
  /** Task ID to track */
  taskId: string;
  /** Optional task name override */
  taskName?: string;
}

// =============================================================================
// Config
// =============================================================================

const statusConfig: Record<
  TaskStatus,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline'; color: string }
> = {
  pending: { label: '等待中', variant: 'outline', color: 'border-gray-200' },
  running: { label: '執行中', variant: 'default', color: 'border-blue-200' },
  completed: { label: '已完成', variant: 'secondary', color: 'border-green-200' },
  failed: { label: '失敗', variant: 'destructive', color: 'border-red-200' },
  cancelled: { label: '已取消', variant: 'outline', color: 'border-yellow-200' },
};

const stepIcons: Record<TaskStepStatus, typeof CheckCircle2> = {
  pending: Circle,
  running: Loader2,
  completed: CheckCircle2,
  failed: XCircle,
  skipped: SkipForward,
};

const stepColors: Record<TaskStepStatus, string> = {
  pending: 'text-gray-400',
  running: 'text-blue-500 animate-spin',
  completed: 'text-green-500',
  failed: 'text-red-500',
  skipped: 'text-gray-400',
};

// =============================================================================
// Component
// =============================================================================

export function TaskProgressCard({ taskId, taskName }: TaskProgressCardProps) {
  const navigate = useNavigate();
  const [showSteps, setShowSteps] = useState(false);

  const { data: task } = useTask(taskId);

  if (!task) {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 bg-gray-50 text-xs text-gray-500">
        <Loader2 className="h-3 w-3 animate-spin" />
        載入任務 {taskId.slice(0, 8)}...
      </div>
    );
  }

  const config = statusConfig[task.status] || statusConfig.pending;
  const steps: TaskStep[] = task.steps || [];
  const displayName = taskName || task.name || taskId.slice(0, 12);

  return (
    <div
      className={cn(
        'rounded-lg border bg-white text-sm w-full max-w-md',
        config.color
      )}
    >
      {/* Header: Task ID + Name + Status */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100">
        <div className="flex items-center gap-2 min-w-0">
          <button
            onClick={() => navigate(`/tasks/${taskId}`)}
            className="font-mono text-xs text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1"
            title="查看詳情"
          >
            {taskId.slice(0, 8)}
            <ExternalLink className="h-3 w-3" />
          </button>
          <span className="text-gray-700 font-medium truncate">
            {displayName}
          </span>
        </div>
        <Badge variant={config.variant} className="text-[10px] px-1.5 py-0 h-4">
          {config.label}
        </Badge>
      </div>

      {/* Progress Bar */}
      <div className="px-3 py-2">
        <div className="flex items-center gap-2">
          <Progress
            value={task.progress}
            className={cn(
              'h-2 flex-1',
              task.status === 'running' && 'animate-pulse'
            )}
          />
          <span className="text-xs font-medium text-gray-600 w-8 text-right">
            {task.progress}%
          </span>
        </div>
      </div>

      {/* Steps (collapsible) */}
      {steps.length > 0 && (
        <>
          <button
            onClick={() => setShowSteps(!showSteps)}
            className="w-full flex items-center justify-between px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-50 border-t border-gray-100 transition-colors"
          >
            <span>{steps.length} 個步驟</span>
            {showSteps ? (
              <ChevronUp className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
          </button>

          {showSteps && (
            <div className="px-3 pb-2 space-y-1">
              {steps.map((step) => {
                const Icon = stepIcons[step.status] || Circle;
                const colorClass = stepColors[step.status] || 'text-gray-400';
                return (
                  <div
                    key={step.step_id}
                    className="flex items-center gap-2 text-xs"
                  >
                    <Icon className={cn('h-3.5 w-3.5 shrink-0', colorClass)} />
                    <span className="text-gray-700 truncate flex-1">
                      {step.name}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default TaskProgressCard;
