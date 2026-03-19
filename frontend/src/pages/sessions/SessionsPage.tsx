/**
 * SessionsPage - Session Management List Page
 *
 * Sprint 138: Phase 40 - Session Management
 *
 * Displays all sessions with status filtering, search, and actions.
 * Supports: view detail, resume interrupted, delete.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Clock,
  RefreshCw,
  Trash2,
  Eye,
  Filter,
  AlertCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
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
import {
  useSessions,
  useResumeSession,
  useDeleteSession,
} from '@/hooks/useSessions';
import type { SessionStatus } from '@/api/endpoints/sessions';

// =============================================================================
// Status Badge Mapping
// =============================================================================

const statusConfig: Record<
  SessionStatus,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  active: { label: '進行中', variant: 'default' },
  completed: { label: '已完成', variant: 'secondary' },
  interrupted: { label: '已中斷', variant: 'destructive' },
  expired: { label: '已過期', variant: 'outline' },
  error: { label: '錯誤', variant: 'destructive' },
};

// =============================================================================
// Component
// =============================================================================

export function SessionsPage() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<SessionStatus | 'all'>(
    'all'
  );

  const { data, isLoading, error, refetch } = useSessions(
    statusFilter !== 'all' ? { status: statusFilter } : undefined
  );

  const resumeMutation = useResumeSession();
  const deleteMutation = useDeleteSession();

  const handleResume = async (sessionId: string) => {
    try {
      await resumeMutation.mutateAsync(sessionId);
      navigate(`/chat?session=${sessionId}`);
    } catch {
      // Error handled by mutation
    }
  };

  const handleDelete = async (sessionId: string) => {
    if (!confirm('確定要刪除此 Session 嗎？此操作無法恢復。')) return;
    deleteMutation.mutate(sessionId);
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Clock className="h-6 w-6" />
            Sessions 管理
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            管理所有對話 Sessions，查看歷史記錄並恢復中斷的 Sessions
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
          onValueChange={(val) =>
            setStatusFilter(val as SessionStatus | 'all')
          }
        >
          <SelectTrigger className="w-48">
            <SelectValue placeholder="篩選狀態" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部狀態</SelectItem>
            <SelectItem value="active">進行中</SelectItem>
            <SelectItem value="completed">已完成</SelectItem>
            <SelectItem value="interrupted">已中斷</SelectItem>
            <SelectItem value="expired">已過期</SelectItem>
            <SelectItem value="error">錯誤</SelectItem>
          </SelectContent>
        </Select>
        {data && (
          <span className="text-sm text-gray-500">
            共 {data.total ?? 0} 個 Sessions
          </span>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-50 text-red-700 rounded-lg">
          <AlertCircle className="h-5 w-5" />
          <span>載入 Sessions 失敗：{error.message}</span>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      )}

      {/* Table */}
      {!isLoading && data && (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[240px]">Session ID</TableHead>
                <TableHead>狀態</TableHead>
                <TableHead>建立時間</TableHead>
                <TableHead>最後更新</TableHead>
                <TableHead className="text-center">訊息數</TableHead>
                <TableHead>最後訊息</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {!data.sessions?.length ? (
                <TableRow>
                  <TableCell
                    colSpan={7}
                    className="text-center py-12 text-gray-500"
                  >
                    <Clock className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                    <p>暫無 Sessions</p>
                  </TableCell>
                </TableRow>
              ) : (
                (data.sessions || []).map((session) => {
                  const config =
                    statusConfig[session.status] || statusConfig.active;
                  return (
                    <TableRow key={session.session_id}>
                      <TableCell className="font-mono text-xs">
                        {session.session_id.slice(0, 12)}...
                      </TableCell>
                      <TableCell>
                        <Badge variant={config.variant}>{config.label}</Badge>
                      </TableCell>
                      <TableCell className="text-sm text-gray-600">
                        {formatRelativeTime(session.created_at)}
                      </TableCell>
                      <TableCell className="text-sm text-gray-600">
                        {formatRelativeTime(session.updated_at)}
                      </TableCell>
                      <TableCell className="text-center">
                        {session.message_count}
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate text-sm text-gray-500">
                        {session.last_message || '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              navigate(`/sessions/${session.session_id}`)
                            }
                            title="查看詳情"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          {session.status === 'interrupted' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() =>
                                handleResume(session.session_id)
                              }
                              disabled={resumeMutation.isPending}
                              title="恢復 Session"
                            >
                              <RefreshCw
                                className={cn(
                                  'h-4 w-4',
                                  resumeMutation.isPending && 'animate-spin'
                                )}
                              />
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              handleDelete(session.session_id)
                            }
                            disabled={deleteMutation.isPending}
                            title="刪除 Session"
                            className="text-red-500 hover:text-red-700"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
