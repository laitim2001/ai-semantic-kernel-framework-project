// =============================================================================
// IPA Platform - Recent Executions Component
// =============================================================================
// Sprint 5: Frontend UI - Dashboard Components
//
// Table showing recent workflow executions.
// =============================================================================

import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '@/api/client';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { LoadingSpinner } from '@/components/shared/LoadingSpinner';
import { EmptyState } from '@/components/shared/EmptyState';
import { formatRelativeTime, formatDuration } from '@/lib/utils';
import type { Execution } from '@/types';

export function RecentExecutions() {
  const { data, isLoading } = useQuery({
    queryKey: ['recent-executions'],
    queryFn: () => api.get<Execution[]>('/executions?limit=10'),
  });

  if (isLoading) {
    return (
      <div className="h-48 flex items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  // Use mock data if API not available
  const executions = data || generateMockExecutions();

  if (executions.length === 0) {
    return <EmptyState title="暫無執行記錄" description="尚未有任何工作流執行" />;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-left text-sm text-gray-500 border-b">
            <th className="pb-3 font-medium">執行 ID</th>
            <th className="pb-3 font-medium">工作流</th>
            <th className="pb-3 font-medium">狀態</th>
            <th className="pb-3 font-medium">開始時間</th>
            <th className="pb-3 font-medium">持續時間</th>
          </tr>
        </thead>
        <tbody>
          {executions.map((execution) => (
            <tr key={execution.id} className="border-b last:border-0">
              <td className="py-3">
                <Link
                  to={`/workflows/${execution.workflow_id}`}
                  className="text-primary hover:underline font-mono text-sm"
                >
                  {execution.id.slice(0, 8)}
                </Link>
              </td>
              <td className="py-3 text-sm">{execution.workflow_name}</td>
              <td className="py-3">
                <StatusBadge status={execution.status} />
              </td>
              <td className="py-3 text-sm text-gray-500">
                {formatRelativeTime(execution.started_at)}
              </td>
              <td className="py-3 text-sm text-gray-500">
                {execution.duration_ms
                  ? formatDuration(execution.duration_ms)
                  : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Generate mock data for demo
function generateMockExecutions(): Execution[] {
  const statuses: Execution['status'][] = ['completed', 'running', 'failed', 'pending'];
  const workflows = ['IT支援工作流', '客服自動回覆', '報表生成', '數據同步'];

  return Array.from({ length: 5 }, (_, i) => ({
    id: `exec-${Math.random().toString(36).slice(2, 10)}`,
    workflow_id: `wf-${i + 1}`,
    workflow_name: workflows[i % workflows.length],
    status: statuses[i % statuses.length],
    started_at: new Date(Date.now() - i * 3600000).toISOString(),
    duration_ms: Math.floor(Math.random() * 60000) + 1000,
    current_step: i + 1,
    total_steps: 5,
    llm_calls: Math.floor(Math.random() * 10),
    llm_tokens: Math.floor(Math.random() * 5000),
    llm_cost: Math.random() * 0.1,
  }));
}
