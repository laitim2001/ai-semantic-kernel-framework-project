// =============================================================================
// IPA Platform - Agent Detail Page
// =============================================================================
// Sprint 5: Frontend UI - S5-4 Agent Management
//
// Detailed view of a single agent with test interface.
// =============================================================================

import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowLeft, Settings, Play, Send, Bot } from 'lucide-react';
import { api } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { PageLoading } from '@/components/shared/LoadingSpinner';
import { LoadingSpinner } from '@/components/shared/LoadingSpinner';
import { formatNumber } from '@/lib/utils';
import type { Agent } from '@/types';

export function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [testInput, setTestInput] = useState('');
  const [testResult, setTestResult] = useState<string | null>(null);

  const { data: agent, isLoading } = useQuery({
    queryKey: ['agent', id],
    queryFn: () => api.get<Agent>(`/agents/${id}`),
    enabled: !!id,
  });

  const testMutation = useMutation({
    mutationFn: (message: string) =>
      api.post<{ response: string }>(`/agents/${id}/test`, { message }),
    onSuccess: (data) => {
      setTestResult(data.response);
    },
  });

  if (isLoading) {
    return <PageLoading />;
  }

  // Use mock data if API not available
  const ag = agent || generateMockAgent(id || 'agent-1');

  const handleTest = () => {
    if (testInput.trim()) {
      testMutation.mutate(testInput);
    }
  };

  return (
    <div className="space-y-6">
      {/* Back button and header */}
      <div className="flex items-center gap-4">
        <Link to="/agents">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <div className="flex items-center gap-4 flex-1">
          <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
            <Bot className="w-6 h-6 text-primary" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900">{ag.name}</h1>
              <StatusBadge status={ag.status} />
            </div>
            <p className="text-gray-500">{ag.description}</p>
          </div>
        </div>
        <Link to={`/agents/${id}/edit`}>
          <Button variant="outline">
            <Settings className="w-4 h-4 mr-2" />
            編輯
          </Button>
        </Link>
      </div>

      {/* Info cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500">類別</p>
            <p className="text-lg font-semibold mt-1">{ag.category || '未分類'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500">執行次數</p>
            <p className="text-lg font-semibold mt-1">
              {formatNumber(ag.execution_count ?? 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500">平均響應時間</p>
            <p className="text-lg font-semibold mt-1">
              {ag.avg_response_time_ms ?? 0}ms
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500">模型</p>
            <p className="text-lg font-semibold mt-1">
              {ag.model_config_data?.model || ag.model_config?.model || 'gpt-4o'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tools */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">工具列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 flex-wrap">
            {ag.tools.map((tool) => (
              <Badge key={tool} variant="outline" className="text-sm py-1 px-3">
                {tool}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Test interface */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Play className="w-5 h-5" />
            測試 Agent
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={testInput}
                onChange={(e) => setTestInput(e.target.value)}
                placeholder="輸入測試訊息..."
                className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                onKeyDown={(e) => e.key === 'Enter' && handleTest()}
              />
              <Button onClick={handleTest} disabled={testMutation.isPending}>
                {testMutation.isPending ? (
                  <LoadingSpinner size="sm" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </Button>
            </div>

            {testResult && (
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm font-medium text-gray-700 mb-2">回覆:</p>
                <p className="text-sm text-gray-600 whitespace-pre-wrap">
                  {testResult}
                </p>
              </div>
            )}

            {!testResult && !testMutation.isPending && (
              <p className="text-sm text-gray-500 text-center py-4">
                輸入訊息來測試 Agent 的回應
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Generate mock data
function generateMockAgent(id: string): Agent {
  return {
    id,
    name: 'IT 支援 Agent',
    description: '處理 IT 支援請求，包括密碼重置、軟體問題排查等',
    category: 'IT Operations',
    instructions: 'You are an IT support agent...',
    tools: ['ServiceNow', 'Active Directory', 'Email', 'Knowledge Base'],
    model_config: { model: 'gpt-4o', temperature: 0.7, max_tokens: 2000 },
    status: 'active',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    execution_count: 256,
    avg_response_time_ms: 1200,
  };
}
