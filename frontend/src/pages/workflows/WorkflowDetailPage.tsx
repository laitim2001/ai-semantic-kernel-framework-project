// =============================================================================
// IPA Platform - Workflow Detail Page
// =============================================================================
// Sprint 5: Frontend UI - S5-3 Workflow Management
//
// Detailed view of a single workflow with execution history.
// =============================================================================

import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Play, Settings, History, AlertCircle, CheckCircle, XCircle, Power, PowerOff } from 'lucide-react';
import { api } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { PageLoading, LoadingSpinner } from '@/components/shared/LoadingSpinner';
import { formatDate, formatNumber } from '@/lib/utils';
import type { Workflow, Execution } from '@/types';

interface ExecutionResult {
  execution_id: string;
  workflow_id: string;
  status: string;
  result: Record<string, unknown> | null;
  error?: string;
}

export function WorkflowDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [showExecuteDialog, setShowExecuteDialog] = useState(false);
  const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null);

  const { data: workflow, isLoading } = useQuery({
    queryKey: ['workflow', id],
    queryFn: () => api.get<Workflow>(`/workflows/${id}`),
    enabled: !!id,
  });

  interface ExecutionListResponse {
    items: Execution[];
    total: number;
    page: number;
    page_size: number;
  }

  const { data: executionsData, refetch: refetchExecutions } = useQuery({
    queryKey: ['workflow-executions', id],
    queryFn: () => api.get<ExecutionListResponse>(`/executions/?workflow_id=${id}&page_size=10`),
    enabled: !!id,
  });

  const executions = executionsData?.items;

  const executeMutation = useMutation({
    mutationFn: () => api.post<ExecutionResult>(`/workflows/${id}/execute`, { input: {}, variables: {} }),
    onSuccess: (data) => {
      setExecutionResult(data);
      refetchExecutions();
      queryClient.invalidateQueries({ queryKey: ['workflow', id] });
    },
    onError: (error: Error) => {
      setExecutionResult({
        execution_id: '',
        workflow_id: id || '',
        status: 'failed',
        result: null,
        error: error.message,
      });
    },
  });

  const handleExecute = () => {
    setShowExecuteDialog(true);
    setExecutionResult(null);
    executeMutation.mutate();
  };

  const activateMutation = useMutation({
    mutationFn: () => api.post<Workflow>(`/workflows/${id}/activate`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow', id] });
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: () => api.post<Workflow>(`/workflows/${id}/deactivate`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow', id] });
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
  });

  const handleToggleStatus = () => {
    if (workflow?.status === 'active') {
      deactivateMutation.mutate();
    } else {
      activateMutation.mutate();
    }
  };

  if (isLoading) {
    return <PageLoading />;
  }

  // Use mock data if API not available
  const wf = workflow || generateMockWorkflow(id || 'wf-1');
  const execs = executions || [];

  return (
    <div className="space-y-6">
      {/* Back button and header */}
      <div className="flex items-center gap-4">
        <Link to="/workflows">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">{wf.name}</h1>
            <StatusBadge status={wf.status} />
          </div>
          <p className="text-gray-500">{wf.description}</p>
        </div>
        <div className="flex gap-2">
          <Link to={`/workflows/${id}/edit`}>
            <Button variant="outline">
              <Settings className="w-4 h-4 mr-2" />
              編輯
            </Button>
          </Link>
          <Button
            variant={wf.status === 'active' ? 'destructive' : 'default'}
            onClick={handleToggleStatus}
            disabled={activateMutation.isPending || deactivateMutation.isPending}
          >
            {activateMutation.isPending || deactivateMutation.isPending ? (
              <LoadingSpinner size="sm" className="mr-2" />
            ) : wf.status === 'active' ? (
              <PowerOff className="w-4 h-4 mr-2" />
            ) : (
              <Power className="w-4 h-4 mr-2" />
            )}
            {wf.status === 'active' ? '停用' : '啟用'}
          </Button>
          <Button
            onClick={handleExecute}
            disabled={executeMutation.isPending || wf.status !== 'active'}
          >
            {executeMutation.isPending ? (
              <LoadingSpinner size="sm" className="mr-2" />
            ) : (
              <Play className="w-4 h-4 mr-2" />
            )}
            執行
          </Button>
        </div>
      </div>

      {/* Execution Status Dialog */}
      {showExecuteDialog && (
        <Card className={`border-2 ${
          executionResult?.status === 'completed' ? 'border-green-200 bg-green-50' :
          executionResult?.status === 'failed' ? 'border-red-200 bg-red-50' :
          'border-blue-200 bg-blue-50'
        }`}>
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              {executeMutation.isPending ? (
                <>
                  <LoadingSpinner size="md" />
                  <div>
                    <p className="font-medium">正在執行工作流...</p>
                    <p className="text-sm text-gray-500">請稍候，這可能需要一些時間</p>
                  </div>
                </>
              ) : executionResult?.status === 'completed' ? (
                <>
                  <CheckCircle className="w-6 h-6 text-green-500 shrink-0" />
                  <div className="flex-1">
                    <p className="font-medium text-green-700">工作流執行成功</p>
                    <p className="text-sm text-gray-600 mt-1">
                      執行 ID: {executionResult.execution_id.slice(0, 8)}...
                    </p>
                    {executionResult.result && (
                      <div className="mt-2 p-2 bg-white rounded text-sm font-mono overflow-auto max-h-40">
                        {JSON.stringify(executionResult.result, null, 2)}
                      </div>
                    )}
                  </div>
                </>
              ) : executionResult?.status === 'failed' ? (
                <>
                  <XCircle className="w-6 h-6 text-red-500 shrink-0" />
                  <div className="flex-1">
                    <p className="font-medium text-red-700">工作流執行失敗</p>
                    <p className="text-sm text-red-600 mt-1">
                      {executionResult.error || '發生未知錯誤'}
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <AlertCircle className="w-6 h-6 text-blue-500 shrink-0" />
                  <div>
                    <p className="font-medium text-blue-700">執行狀態: {executionResult?.status}</p>
                    <p className="text-sm text-gray-600 mt-1">
                      執行 ID: {executionResult?.execution_id?.slice(0, 8)}...
                    </p>
                  </div>
                </>
              )}
            </div>
            <div className="mt-4 flex justify-end">
              <Button variant="outline" size="sm" onClick={() => setShowExecuteDialog(false)}>
                關閉
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Workflow not active warning */}
      {wf.status !== 'active' && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-yellow-600" />
              <span className="text-sm text-yellow-700">
                工作流狀態為 <Badge variant="secondary">{wf.status}</Badge>，需要先將狀態設為「啟用」才能執行。
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Info cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500">觸發方式</p>
            <p className="text-lg font-semibold mt-1">{wf.trigger_type}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500">總執行次數</p>
            <p className="text-lg font-semibold mt-1">
              {formatNumber(wf.execution_count ?? 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500">版本</p>
            <p className="text-lg font-semibold mt-1">v{wf.version}</p>
          </CardContent>
        </Card>
      </div>

      {/* Workflow definition */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">工作流定義</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500">
              節點數: {(wf.graph_definition?.nodes || wf.definition?.nodes || []).length} | 連接數: {(wf.graph_definition?.edges || wf.definition?.edges || []).length}
            </p>
            <div className="mt-4 flex gap-2 flex-wrap">
              {(wf.graph_definition?.nodes || wf.definition?.nodes || []).map((node) => (
                <Badge key={node.id} variant="outline">
                  {node.name || node.id}
                </Badge>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Execution history */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <History className="w-5 h-5" />
            執行歷史
          </CardTitle>
        </CardHeader>
        <CardContent>
          {execs.length === 0 ? (
            <p className="text-gray-500 text-center py-8">暫無執行記錄</p>
          ) : (
            <div className="space-y-3">
              {execs.map((exec) => (
                <div
                  key={exec.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div>
                    <p className="font-mono text-sm">{exec.id.slice(0, 8)}</p>
                    <p className="text-xs text-gray-500">
                      {formatDate(exec.started_at)}
                    </p>
                  </div>
                  <StatusBadge status={exec.status} />
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// Generate mock data
function generateMockWorkflow(id: string): Workflow {
  return {
    id,
    name: 'IT 支援工作流',
    description: '自動處理 IT 支援請求，包括密碼重置、軟體安裝等',
    version: '1.2.0',
    status: 'active',
    trigger_type: 'event',
    definition: {
      nodes: [
        { id: 'start', type: 'start', name: '開始', config: {} },
        { id: 'agent-1', type: 'agent', name: 'IT 支援 Agent', config: {} },
        { id: 'approval', type: 'approval', name: '主管審批', config: {} },
        { id: 'end', type: 'end', name: '結束', config: {} },
      ],
      edges: [
        { id: 'e1', source: 'start', target: 'agent-1' },
        { id: 'e2', source: 'agent-1', target: 'approval' },
        { id: 'e3', source: 'approval', target: 'end' },
      ],
    },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    last_execution_at: new Date(Date.now() - 3600000).toISOString(),
    execution_count: 156,
  };
}
