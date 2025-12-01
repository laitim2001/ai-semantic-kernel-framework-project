// =============================================================================
// IPA Platform - Approvals Page
// =============================================================================
// Sprint 5: Frontend UI - S5-5 Approval Workbench
//
// Approval workbench for handling pending checkpoints.
// =============================================================================

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Clock, CheckCircle, XCircle } from 'lucide-react';
import { api } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { PageLoading } from '@/components/shared/LoadingSpinner';
import { EmptyState } from '@/components/shared/EmptyState';
import { formatRelativeTime } from '@/lib/utils';
import type { Checkpoint } from '@/types';

export function ApprovalsPage() {
  const queryClient = useQueryClient();
  const [selectedCheckpoint, setSelectedCheckpoint] = useState<Checkpoint | null>(
    null
  );
  const [feedback, setFeedback] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['pending-checkpoints'],
    queryFn: () => api.get<Checkpoint[]>('/checkpoints/pending'),
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) =>
      api.post(`/checkpoints/${id}/approve`, { feedback }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-checkpoints'] });
      setSelectedCheckpoint(null);
      setFeedback('');
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) =>
      api.post(`/checkpoints/${id}/reject`, { reason: feedback }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-checkpoints'] });
      setSelectedCheckpoint(null);
      setFeedback('');
    },
  });

  if (isLoading) {
    return <PageLoading />;
  }

  // Use mock data if API not available
  const checkpoints = data || generateMockCheckpoints();

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">審批工作台</h1>
        <p className="text-gray-500">處理待審批的工作流檢查點</p>
      </div>

      {/* Stats */}
      <div className="flex gap-4">
        <Badge variant="warning" className="text-sm py-1 px-3">
          <Clock className="w-4 h-4 mr-1" />
          {checkpoints.filter((c) => c.status === 'pending').length} 待處理
        </Badge>
      </div>

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Checkpoints list */}
        <div className="space-y-4">
          {checkpoints.length === 0 ? (
            <EmptyState
              title="無待審批項目"
              description="目前沒有需要審批的項目"
              icon={<CheckCircle className="w-6 h-6 text-green-500" />}
            />
          ) : (
            checkpoints.map((checkpoint) => (
              <Card
                key={checkpoint.id}
                className={`cursor-pointer transition-all ${
                  selectedCheckpoint?.id === checkpoint.id
                    ? 'ring-2 ring-primary'
                    : 'hover:shadow-md'
                }`}
                onClick={() => setSelectedCheckpoint(checkpoint)}
              >
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold text-gray-900">
                        {checkpoint.workflow_name}
                      </h3>
                      <p className="text-sm text-gray-500 mt-1">
                        Step {checkpoint.step}: {checkpoint.step_name}
                      </p>
                    </div>
                    <Badge
                      variant={
                        checkpoint.status === 'pending' ? 'warning' : 'success'
                      }
                    >
                      {checkpoint.status === 'pending' ? '待處理' : '已處理'}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-400 mt-2">
                    {formatRelativeTime(checkpoint.created_at)}
                  </p>
                </CardContent>
              </Card>
            ))
          )}
        </div>

        {/* Detail panel */}
        <div className="lg:sticky lg:top-6">
          {selectedCheckpoint ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">審批詳情</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm font-medium text-gray-700">工作流</p>
                  <p className="text-sm text-gray-500">
                    {selectedCheckpoint.workflow_name}
                  </p>
                </div>

                <div>
                  <p className="text-sm font-medium text-gray-700">步驟</p>
                  <p className="text-sm text-gray-500">
                    Step {selectedCheckpoint.step}: {selectedCheckpoint.step_name}
                  </p>
                </div>

                <div>
                  <p className="text-sm font-medium text-gray-700 mb-2">內容</p>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <pre className="text-sm text-gray-600 whitespace-pre-wrap">
                      {selectedCheckpoint.content}
                    </pre>
                  </div>
                </div>

                <div>
                  <p className="text-sm font-medium text-gray-700 mb-2">
                    反饋 (可選)
                  </p>
                  <textarea
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    placeholder="輸入反饋或備註..."
                    className="w-full px-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-none"
                    rows={3}
                  />
                </div>

                <div className="flex gap-2 pt-2">
                  <Button
                    variant="outline"
                    className="flex-1"
                    onClick={() =>
                      rejectMutation.mutate(selectedCheckpoint.id)
                    }
                    disabled={rejectMutation.isPending}
                  >
                    <XCircle className="w-4 h-4 mr-2" />
                    拒絕
                  </Button>
                  <Button
                    className="flex-1"
                    onClick={() =>
                      approveMutation.mutate(selectedCheckpoint.id)
                    }
                    disabled={approveMutation.isPending}
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    批准
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="pt-6">
                <p className="text-center text-gray-500 py-12">
                  選擇一個項目查看詳情
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

// Generate mock data
function generateMockCheckpoints(): Checkpoint[] {
  return [
    {
      id: 'cp-1',
      execution_id: 'exec-1',
      workflow_id: 'wf-1',
      workflow_name: 'IT 支援審批',
      step: 2,
      step_name: '主管審批',
      status: 'pending',
      content:
        '用戶 John 申請安裝軟體 Visual Studio Code。\n\nAgent 分析結果：\n- 軟體類型：開發工具\n- 風險等級：低\n- 建議：批准安裝',
      context: { user: 'John', software: 'VS Code' },
      created_at: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      id: 'cp-2',
      execution_id: 'exec-2',
      workflow_id: 'wf-2',
      workflow_name: '費用報銷審批',
      step: 1,
      step_name: '財務審核',
      status: 'pending',
      content:
        '報銷申請：\n- 金額：$150\n- 類別：辦公用品\n- 描述：購買文具和打印紙',
      context: { amount: 150, category: '辦公用品' },
      created_at: new Date(Date.now() - 7200000).toISOString(),
    },
  ];
}
