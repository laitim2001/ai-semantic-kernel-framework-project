/**
 * SessionDetailPage - Session Detail View
 *
 * Sprint 138: Phase 40 - Session Management
 *
 * Displays session metadata and message history timeline.
 * Supports resume for interrupted sessions.
 */

import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Clock,
  User,
  Bot,
  Settings,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Separator } from '@/components/ui/Separator';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/utils';
import {
  useSession,
  useSessionMessages,
  useResumeSession,
} from '@/hooks/useSessions';
import type { SessionStatus } from '@/api/endpoints/sessions';

// =============================================================================
// Status Config
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

const roleConfig: Record<string, { icon: typeof User; label: string; color: string }> = {
  user: { icon: User, label: '使用者', color: 'bg-blue-50 border-blue-200' },
  assistant: { icon: Bot, label: 'AI 助手', color: 'bg-green-50 border-green-200' },
  system: { icon: Settings, label: '系統', color: 'bg-gray-50 border-gray-200' },
};

// =============================================================================
// Component
// =============================================================================

export function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const {
    data: session,
    isLoading: sessionLoading,
    error: sessionError,
  } = useSession(id || '');

  const {
    data: messagesData,
    isLoading: messagesLoading,
  } = useSessionMessages(id || '');

  const resumeMutation = useResumeSession();

  const handleResume = async () => {
    if (!id) return;
    try {
      await resumeMutation.mutateAsync(id);
      navigate(`/chat?session=${id}`);
    } catch {
      // Error handled by mutation
    }
  };

  if (sessionLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (sessionError || !session) {
    return (
      <div className="p-6">
        <div className="flex items-center gap-2 p-4 bg-red-50 text-red-700 rounded-lg">
          <AlertCircle className="h-5 w-5" />
          <span>載入 Session 失敗：{sessionError?.message || '找不到 Session'}</span>
        </div>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => navigate('/sessions')}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          返回列表
        </Button>
      </div>
    );
  }

  const config = statusConfig[session.status] || statusConfig.active;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/sessions')}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回列表
          </Button>
          <div>
            <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Session 詳情
            </h1>
            <p className="text-sm text-gray-500 font-mono mt-0.5">
              {session.session_id}
            </p>
          </div>
        </div>
        {session.status === 'interrupted' && (
          <Button
            onClick={handleResume}
            disabled={resumeMutation.isPending}
          >
            <RefreshCw
              className={cn(
                'h-4 w-4 mr-2',
                resumeMutation.isPending && 'animate-spin'
              )}
            />
            恢復 Session
          </Button>
        )}
      </div>

      {/* Metadata Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
            <CardTitle className="text-sm text-gray-500">建立時間</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-sm">
              {formatRelativeTime(session.created_at)}
            </span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-500">最後更新</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-sm">
              {formatRelativeTime(session.updated_at)}
            </span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-500">訊息數量</CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-lg font-semibold">
              {session.message_count}
            </span>
          </CardContent>
        </Card>
      </div>

      {/* Additional metadata */}
      {(session.agent_type || session.execution_mode || session.intent_category) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">執行資訊</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4 text-sm">
              {session.agent_type && (
                <div>
                  <span className="text-gray-500">Agent 類型：</span>
                  <span className="ml-1 font-medium">{session.agent_type}</span>
                </div>
              )}
              {session.execution_mode && (
                <div>
                  <span className="text-gray-500">執行模式：</span>
                  <span className="ml-1 font-medium">{session.execution_mode}</span>
                </div>
              )}
              {session.intent_category && (
                <div>
                  <span className="text-gray-500">意圖類別：</span>
                  <span className="ml-1 font-medium">{session.intent_category}</span>
                </div>
              )}
              {session.risk_level && (
                <div>
                  <span className="text-gray-500">風險等級：</span>
                  <span className="ml-1 font-medium">{session.risk_level}</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <Separator />

      {/* Message History */}
      <div>
        <h2 className="text-lg font-semibold mb-4">訊息歷史</h2>
        {messagesLoading ? (
          <div className="flex items-center justify-center h-32">
            <RefreshCw className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        ) : !messagesData?.messages?.length ? (
          <div className="text-center py-12 text-gray-500">
            <Bot className="h-8 w-8 mx-auto mb-2 text-gray-300" />
            <p>此 Session 暫無訊息記錄</p>
          </div>
        ) : (
          <div className="space-y-3">
            {messagesData.messages.map((msg) => {
              const roleInfo = roleConfig[msg.role] || roleConfig.system;
              const Icon = roleInfo.icon;
              return (
                <div
                  key={msg.id}
                  className={cn(
                    'p-4 rounded-lg border',
                    roleInfo.color
                  )}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Icon className="h-4 w-4 text-gray-500" />
                    <span className="text-sm font-medium text-gray-700">
                      {roleInfo.label}
                    </span>
                    <span className="text-xs text-gray-400 ml-auto">
                      {formatRelativeTime(msg.timestamp)}
                    </span>
                  </div>
                  <p className="text-sm text-gray-800 whitespace-pre-wrap">
                    {msg.content}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
