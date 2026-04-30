/**
 * TaskDetailPage - Task Detail View
 *
 * Sprint 139: Phase 40 - Task Dashboard
 *
 * Displays task metadata, progress bar, step list,
 * and execution result with cancel/retry actions.
 */

import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ListTodo,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Circle,
  Loader2,
  SkipForward,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Separator } from '@/components/ui/Separator';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/utils';
import { useTask, useTaskSteps, useCancelTask, useRetryTask } from '@/hooks/useTasks';
import type { TaskStatus, TaskStepStatus } from '@/api/endpoints/tasks';

// =============================================================================
// Config
// =============================================================================

const statusConfig: Record<
  TaskStatus,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  pending: { label: '等待中', variant: 'outline' },
  running: { label: '執行中', variant: 'default' },
  completed: { label: '已完成', variant: 'secondary' },
  failed: { label: '失敗', variant: 'destructive' },
  cancelled: { label: '已取消', variant: 'outline' },
};

const stepStatusIcons: Record<TaskStepStatus, typeof CheckCircle2> = {
  pending: Circle,
  running: Loader2,
  completed: CheckCircle2,
  failed: XCircle,
  skipped: SkipForward,
};

const stepStatusColors: Record<TaskStepStatus, string> = {
  pending: 'text-gray-400',
  running: 'text-blue-500 animate-spin',
  completed: 'text-green-500',
  failed: 'text-red-500',
  skipped: 'text-gray-400',
};

function formatDuration(ms?: number): string {
  if (!ms) return '-';
  if (ms < 1000) return `${ms}ms`;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${seconds % 60}s`;
}

// =============================================================================
// Component
// =============================================================================

export function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: task, isLoading, error } = useTask(id || '');
  const { data: stepsData } = useTaskSteps(id || '');
  const cancelMutation = useCancelTask();
  const retryMutation = useRetryTask();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="p-6">
        <div className="flex items-center gap-2 p-4 bg-red-50 text-red-700 rounded-lg">
          <AlertCircle className="h-5 w-5" />
          <span>載入任務失敗：{error?.message || '找不到任務'}</span>
        </div>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => navigate('/tasks')}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          返回列表
        </Button>
      </div>
    );
  }

  const config = statusConfig[task.status] || statusConfig.pending;
  const steps = stepsData?.steps || task.steps || [];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/tasks')}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回列表
          </Button>
          <div>
            <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <ListTodo className="h-5 w-5" />
              {task.name || '任務詳情'}
            </h1>
            <p className="text-sm text-gray-500 font-mono mt-0.5">
              {task.task_id}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {task.status === 'running' && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => cancelMutation.mutate(task.task_id)}
              disabled={cancelMutation.isPending}
              className="text-orange-600"
            >
              <XCircle className="h-4 w-4 mr-2" />
              取消任務
            </Button>
          )}
          {task.status === 'failed' && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => retryMutation.mutate(task.task_id)}
              disabled={retryMutation.isPending}
            >
              <RotateCcw className="h-4 w-4 mr-2" />
              重試
            </Button>
          )}
        </div>
      </div>

      {/* Metadata Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-500">狀態</CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant={config.variant}>{config.label}</Badge>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-500">優先級</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-sm font-medium">{task.priority}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-500">建立時間</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-sm">{formatRelativeTime(task.created_at)}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-500">耗時</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-sm">{formatDuration(task.duration_ms)}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-500">Agent</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-sm">
              {task.agent_name || task.agent_id?.slice(0, 8) || '-'}
            </span>
          </CardContent>
        </Card>
      </div>

      {/* Progress */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">執行進度</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <Progress
              value={task.progress}
              className={cn(
                'h-3 flex-1',
                task.status === 'running' && 'animate-pulse'
              )}
            />
            <span className="text-lg font-semibold text-gray-700 w-14 text-right">
              {task.progress}%
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Steps */}
      {steps.length > 0 && (
        <>
          <Separator />
          <div>
            <h2 className="text-lg font-semibold mb-4">執行步驟</h2>
            <div className="space-y-2">
              {steps.map((step) => {
                const Icon = stepStatusIcons[step.status] || Circle;
                const colorClass = stepStatusColors[step.status] || 'text-gray-400';
                return (
                  <div
                    key={step.step_id}
                    className="flex items-center gap-3 p-3 rounded-lg border bg-white"
                  >
                    <Icon className={cn('h-5 w-5 shrink-0', colorClass)} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-800">
                          {step.name}
                        </span>
                        <span className="text-xs text-gray-400">
                          {formatDuration(step.duration_ms)}
                        </span>
                      </div>
                      {step.output_summary && (
                        <p className="text-xs text-gray-500 mt-0.5 truncate">
                          {step.output_summary}
                        </p>
                      )}
                      {step.error && (
                        <p className="text-xs text-red-500 mt-0.5">
                          {step.error}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* Result */}
      {(task.status === 'completed' || task.status === 'failed') && (
        <>
          <Separator />
          <Card
            className={cn(
              task.status === 'failed'
                ? 'border-red-200 bg-red-50'
                : 'border-green-200 bg-green-50'
            )}
          >
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                {task.status === 'completed' ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-red-500" />
                )}
                {task.status === 'completed' ? '執行結果' : '錯誤資訊'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {task.status === 'completed' && task.result ? (
                <pre className="text-xs text-gray-700 whitespace-pre-wrap bg-white p-3 rounded border">
                  {JSON.stringify(task.result, null, 2)}
                </pre>
              ) : task.error ? (
                <p className="text-sm text-red-700">{task.error}</p>
              ) : (
                <p className="text-sm text-gray-500">無結果資料</p>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
