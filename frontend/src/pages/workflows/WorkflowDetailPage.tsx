// =============================================================================
// IPA Platform - Workflow Detail Page
// =============================================================================
// Sprint 5: Frontend UI - S5-3 Workflow Management
//
// Detailed view of a single workflow with execution history.
// =============================================================================

import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Play, Settings, History } from 'lucide-react';
import { api } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { PageLoading } from '@/components/shared/LoadingSpinner';
import { formatDate, formatNumber } from '@/lib/utils';
import type { Workflow, Execution } from '@/types';

export function WorkflowDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: workflow, isLoading } = useQuery({
    queryKey: ['workflow', id],
    queryFn: () => api.get<Workflow>(`/workflows/${id}`),
    enabled: !!id,
  });

  const { data: executions } = useQuery({
    queryKey: ['workflow-executions', id],
    queryFn: () => api.get<Execution[]>(`/workflows/${id}/executions?limit=10`),
    enabled: !!id,
  });

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
          <Button variant="outline">
            <Settings className="w-4 h-4 mr-2" />
            編輯
          </Button>
          <Button>
            <Play className="w-4 h-4 mr-2" />
            執行
          </Button>
        </div>
      </div>

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
              {formatNumber(wf.execution_count)}
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
              節點數: {wf.definition.nodes.length} | 連接數: {wf.definition.edges.length}
            </p>
            <div className="mt-4 flex gap-2 flex-wrap">
              {wf.definition.nodes.map((node) => (
                <Badge key={node.id} variant="outline">
                  {node.name}
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
