// =============================================================================
// IPA Platform - Workflows Page
// =============================================================================
// Sprint 5: Frontend UI - S5-3 Workflow Management
//
// List and management of workflows.
// =============================================================================

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';
import { api } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { PageLoading } from '@/components/shared/LoadingSpinner';
import { EmptyState } from '@/components/shared/EmptyState';
import { formatRelativeTime, formatNumber } from '@/lib/utils';
import type { Workflow } from '@/types';

export function WorkflowsPage() {
  const [searchQuery, setSearchQuery] = useState('');

  interface WorkflowListResponse {
    items: Workflow[];
    total: number;
    page: number;
    page_size: number;
  }

  const { data, isLoading } = useQuery({
    queryKey: ['workflows', searchQuery],
    queryFn: () => api.get<WorkflowListResponse>(`/workflows/?search=${searchQuery}`),
  });

  // Use mock data if API not available, handle both array and object response
  const workflows = Array.isArray(data) ? data : (data?.items || generateMockWorkflows());

  const filteredWorkflows = workflows.filter((wf) =>
    wf.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (isLoading) {
    return <PageLoading />;
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">工作流管理</h1>
          <p className="text-gray-500">管理和監控您的自動化工作流</p>
        </div>
        <Link to="/workflows/new">
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            創建工作流
          </Button>
        </Link>
      </div>

      {/* Search bar */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="搜索工作流..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
        />
      </div>

      {/* Workflows grid */}
      {filteredWorkflows.length === 0 ? (
        <EmptyState
          title="暫無工作流"
          description="創建您的第一個自動化工作流"
          action={{ label: '創建工作流', onClick: () => {} }}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredWorkflows.map((workflow) => (
            <Link key={workflow.id} to={`/workflows/${workflow.id}`}>
              <Card className="hover:shadow-md transition-shadow cursor-pointer">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="font-semibold text-gray-900">
                        {workflow.name}
                      </h3>
                      <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                        {workflow.description}
                      </p>
                    </div>
                    <StatusBadge status={workflow.status} />
                  </div>

                  <div className="flex items-center gap-4 text-sm text-gray-500">
                    <span>{workflow.trigger_type}</span>
                    <span>·</span>
                    <span>{formatNumber(workflow.execution_count ?? 0)} 次執行</span>
                  </div>

                  {workflow.last_execution_at && (
                    <p className="text-xs text-gray-400 mt-2">
                      最後執行: {formatRelativeTime(workflow.last_execution_at)}
                    </p>
                  )}
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

// Generate mock data
function generateMockWorkflows(): Workflow[] {
  return [
    {
      id: 'wf-1',
      name: 'IT 支援工作流',
      description: '自動處理 IT 支援請求，包括密碼重置、軟體安裝等',
      version: '1.2.0',
      status: 'active',
      trigger_type: 'event',
      definition: { nodes: [], edges: [] },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      last_execution_at: new Date(Date.now() - 3600000).toISOString(),
      execution_count: 156,
    },
    {
      id: 'wf-2',
      name: '客服自動回覆',
      description: '使用 AI Agent 自動回覆常見客戶問題',
      version: '2.0.0',
      status: 'active',
      trigger_type: 'webhook',
      definition: { nodes: [], edges: [] },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      last_execution_at: new Date(Date.now() - 1800000).toISOString(),
      execution_count: 1024,
    },
    {
      id: 'wf-3',
      name: '報表生成工作流',
      description: '每日自動生成業務報表並發送郵件',
      version: '1.0.0',
      status: 'active',
      trigger_type: 'schedule',
      definition: { nodes: [], edges: [] },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      last_execution_at: new Date(Date.now() - 86400000).toISOString(),
      execution_count: 30,
    },
  ];
}
