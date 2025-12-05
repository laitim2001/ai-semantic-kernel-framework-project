// =============================================================================
// IPA Platform - Agents Page
// =============================================================================
// Sprint 5: Frontend UI - S5-4 Agent Management
//
// List and management of AI agents.
// =============================================================================

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Plus, Search, Bot } from 'lucide-react';
import { api } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { PageLoading } from '@/components/shared/LoadingSpinner';
import { EmptyState } from '@/components/shared/EmptyState';
import { formatNumber } from '@/lib/utils';
import type { Agent } from '@/types';

export function AgentsPage() {
  const [searchQuery, setSearchQuery] = useState('');

  interface AgentListResponse {
    items: Agent[];
    total: number;
    page: number;
    page_size: number;
  }

  const { data, isLoading } = useQuery({
    queryKey: ['agents', searchQuery],
    queryFn: () => api.get<AgentListResponse>(`/agents?search=${searchQuery}`),
  });

  // Use mock data if API not available, handle both array and object response
  const agents = Array.isArray(data) ? data : (data?.items || generateMockAgents());

  const filteredAgents = agents.filter((agent) =>
    agent.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (isLoading) {
    return <PageLoading />;
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Agent 管理</h1>
          <p className="text-gray-500">管理和配置您的 AI Agents</p>
        </div>
        <div className="flex gap-2">
          <Link to="/templates">
            <Button variant="outline">
              從模板創建
            </Button>
          </Link>
          <Link to="/agents/new">
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              建立 Agent
            </Button>
          </Link>
        </div>
      </div>

      {/* Search bar */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="搜索 Agent..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
        />
      </div>

      {/* Agents grid */}
      {filteredAgents.length === 0 ? (
        <EmptyState
          title="暫無 Agent"
          description="從模板市場創建您的第一個 Agent"
          action={{ label: '瀏覽模板', onClick: () => {} }}
          icon={<Bot className="w-6 h-6 text-gray-400" />}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredAgents.map((agent) => (
            <Link key={agent.id} to={`/agents/${agent.id}`}>
              <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
                <CardContent className="pt-6">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center shrink-0">
                      <Bot className="w-6 h-6 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-gray-900 truncate">
                          {agent.name}
                        </h3>
                        <StatusBadge status={agent.status} />
                      </div>
                      <p className="text-sm text-gray-500 line-clamp-2">
                        {agent.description}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center gap-2 flex-wrap">
                    <Badge variant="outline">{agent.category}</Badge>
                    {agent.tools.slice(0, 2).map((tool) => (
                      <Badge key={tool} variant="secondary">
                        {tool}
                      </Badge>
                    ))}
                    {agent.tools.length > 2 && (
                      <Badge variant="secondary">+{agent.tools.length - 2}</Badge>
                    )}
                  </div>

                  <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
                    <span>{formatNumber(agent.execution_count ?? 0)} 次執行</span>
                    <span>·</span>
                    <span>平均 {agent.avg_response_time_ms ?? 0}ms</span>
                  </div>
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
function generateMockAgents(): Agent[] {
  return [
    {
      id: 'agent-1',
      name: 'IT 支援 Agent',
      description: '處理 IT 支援請求，包括密碼重置、軟體問題排查等',
      category: 'IT Operations',
      instructions: 'You are an IT support agent...',
      tools: ['ServiceNow', 'AD', 'Email'],
      model_config: { model: 'gpt-4o', temperature: 0.7, max_tokens: 2000 },
      status: 'active',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      execution_count: 256,
      avg_response_time_ms: 1200,
    },
    {
      id: 'agent-2',
      name: '客服回覆 Agent',
      description: '自動回覆客戶常見問題，提供 24/7 支援',
      category: 'Customer Service',
      instructions: 'You are a customer service agent...',
      tools: ['CRM', 'Knowledge Base', 'Email'],
      model_config: { model: 'gpt-4o', temperature: 0.5, max_tokens: 1500 },
      status: 'active',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      execution_count: 1024,
      avg_response_time_ms: 800,
    },
    {
      id: 'agent-3',
      name: '報表分析 Agent',
      description: '分析業務數據並生成報表摘要',
      category: 'Analytics',
      instructions: 'You are a data analyst agent...',
      tools: ['Database', 'Excel', 'Chart'],
      model_config: { model: 'gpt-4o', temperature: 0.3, max_tokens: 3000 },
      status: 'inactive',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      execution_count: 45,
      avg_response_time_ms: 2500,
    },
  ];
}
