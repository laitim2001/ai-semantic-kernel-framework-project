/**
 * TaskDashboardPage - Task Management Dashboard
 *
 * Sprint 139: Phase 40 - Task Dashboard
 *
 * Displays all dispatched tasks with status/priority filtering,
 * pagination, and auto-refresh for running tasks.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ListTodo,
  RefreshCw,
  Eye,
  XCircle,
  RotateCcw,
  Filter,
  AlertCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/Table';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/utils';
import { useTasks, useCancelTask, useRetryTask } from '@/hooks/useTasks';
import type { TaskStatus, TaskPriority } from '@/api/endpoints/tasks';

// =============================================================================
// Status/Priority Config
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

const priorityConfig: Record<
  TaskPriority,
  { label: string; color: string }
> = {
  LOW: { label: '低', color: 'text-gray-500' },
  MEDIUM: { label: '中', color: 'text-blue-600' },
  HIGH: { label: '高', color: 'text-orange-600' },
  CRITICAL: { label: '嚴重', color: 'text-red-600' },
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

export function TaskDashboardPage() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<TaskStatus | 'all'>('all');
  const [priorityFilter, setPriorityFilter] = useState<TaskPriority | 'all'>('all');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const { data, isLoading, error, refetch } = useTasks({
    ...(statusFilter !== 'all' ? { status: statusFilter } : {}),
    limit: pageSize,
    offset: (page - 1) * pageSize,
  });

  const cancelMutation = useCancelTask();
  const retryMutation = useRetryTask();

  const handleCancel = async (taskId: string) => {
    if (!confirm('確定要取消此任務嗎？')) return;
    cancelMutation.mutate(taskId);
  };

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <ListTodo className="h-6 w-6" />
            任務中心
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            追蹤和管理所有 dispatch 出去的後台任務
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          重新整理
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Filter className="h-4 w-4 text-gray-500" />
        <Select
          value={statusFilter}
          onValueChange={(val) => {
            setStatusFilter(val as TaskStatus | 'all');
            setPage(1);
          }}
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="任務狀態" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部狀態</SelectItem>
            <SelectItem value="pending">等待中</SelectItem>
            <SelectItem value="running">執行中</SelectItem>
            <SelectItem value="completed">已完成</SelectItem>
            <SelectItem value="failed">失敗</SelectItem>
            <SelectItem value="cancelled">已取消</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={priorityFilter}
          onValueChange={(val) => {
            setPriorityFilter(val as TaskPriority | 'all');
            setPage(1);
          }}
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="優先級" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部優先級</SelectItem>
            <SelectItem value="LOW">低</SelectItem>
            <SelectItem value="MEDIUM">中</SelectItem>
            <SelectItem value="HIGH">高</SelectItem>
            <SelectItem value="CRITICAL">嚴重</SelectItem>
          </SelectContent>
        </Select>
        {data && (
          <span className="text-sm text-gray-500">
            共 {data.total ?? 0} 個任務
          </span>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-50 text-red-700 rounded-lg">
          <AlertCircle className="h-5 w-5" />
          <span>載入任務失敗：{error.message}</span>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      )}

      {/* Table */}
      {!isLoading && data && (
        <>
          <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[180px]">Task ID</TableHead>
                  <TableHead>名稱</TableHead>
                  <TableHead>狀態</TableHead>
                  <TableHead className="w-[120px]">進度</TableHead>
                  <TableHead>優先級</TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead>建立時間</TableHead>
                  <TableHead>耗時</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {!data.tasks?.length ? (
                  <TableRow>
                    <TableCell
                      colSpan={9}
                      className="text-center py-12 text-gray-500"
                    >
                      <ListTodo className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                      <p>暫無任務</p>
                    </TableCell>
                  </TableRow>
                ) : (
                  (data.tasks || []).map((task) => {
                    const sConfig = statusConfig[task.status] || statusConfig.pending;
                    const pConfig = priorityConfig[task.priority] || priorityConfig.MEDIUM;
                    return (
                      <TableRow key={task.task_id}>
                        <TableCell className="font-mono text-xs">
                          {task.task_id.slice(0, 12)}...
                        </TableCell>
                        <TableCell className="font-medium text-sm">
                          {task.name || '-'}
                        </TableCell>
                        <TableCell>
                          <Badge variant={sConfig.variant}>
                            {sConfig.label}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Progress
                              value={task.progress}
                              className="h-2 w-16"
                            />
                            <span className="text-xs text-gray-500">
                              {task.progress}%
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className={cn('text-xs font-medium', pConfig.color)}>
                            {pConfig.label}
                          </span>
                        </TableCell>
                        <TableCell className="text-sm text-gray-600">
                          {task.agent_name || task.agent_id?.slice(0, 8) || '-'}
                        </TableCell>
                        <TableCell className="text-sm text-gray-600">
                          {formatRelativeTime(task.created_at)}
                        </TableCell>
                        <TableCell className="text-sm text-gray-600">
                          {formatDuration(task.duration_ms)}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => navigate(`/tasks/${task.task_id}`)}
                              title="查看詳情"
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                            {task.status === 'running' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleCancel(task.task_id)}
                                disabled={cancelMutation.isPending}
                                title="取消任務"
                                className="text-orange-500 hover:text-orange-700"
                              >
                                <XCircle className="h-4 w-4" />
                              </Button>
                            )}
                            {task.status === 'failed' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => retryMutation.mutate(task.task_id)}
                                disabled={retryMutation.isPending}
                                title="重試任務"
                                className="text-blue-500 hover:text-blue-700"
                              >
                                <RotateCcw className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                上一頁
              </Button>
              <span className="text-sm text-gray-600">
                {page} / {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                下一頁
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
