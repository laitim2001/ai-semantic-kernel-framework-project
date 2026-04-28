// =============================================================================
// IPA Platform - Pending Approvals Component
// =============================================================================
// Sprint 5: Frontend UI - Dashboard Components
//
// List of pending approval items on dashboard.
// =============================================================================

import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Clock } from 'lucide-react';
import { api } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { LoadingSpinner } from '@/components/shared/LoadingSpinner';
import { EmptyState } from '@/components/shared/EmptyState';
import { formatRelativeTime } from '@/lib/utils';
import type { Checkpoint } from '@/types';

export function PendingApprovals() {
  interface PendingApprovalsResponse {
    items: Checkpoint[];
    count: number;
  }

  const { data, isLoading } = useQuery({
    queryKey: ['pending-approvals-preview'],
    queryFn: () => api.get<PendingApprovalsResponse>('/checkpoints/pending?limit=5'),
  });

  if (isLoading) {
    return (
      <div className="h-48 flex items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  // Use mock data if API not available, handle both array and object response
  const approvals = Array.isArray(data) ? data : (data?.items || generateMockApprovals());

  if (approvals.length === 0) {
    return (
      <EmptyState
        title="無待審批項目"
        description="目前沒有需要審批的項目"
        icon={<Clock className="w-6 h-6 text-gray-400" />}
      />
    );
  }

  return (
    <div className="space-y-4">
      {approvals.map((approval) => (
        <div
          key={approval.id}
          className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
        >
          <div>
            <p className="font-medium text-sm">{approval.workflow_name}</p>
            <p className="text-xs text-gray-500">
              Step {approval.step} · {formatRelativeTime(approval.created_at)}
            </p>
          </div>
          <Link to={`/approvals?id=${approval.id}`}>
            <Button variant="outline" size="sm">
              查看
            </Button>
          </Link>
        </div>
      ))}

      {approvals.length > 0 && (
        <Link to="/approvals" className="block">
          <Button variant="ghost" className="w-full">
            查看全部
          </Button>
        </Link>
      )}
    </div>
  );
}

// Generate mock data for demo
function generateMockApprovals(): Checkpoint[] {
  const workflows = ['IT支援審批', '費用報銷審批', '系統變更審批'];

  return Array.from({ length: 3 }, (_, i) => ({
    id: `cp-${Math.random().toString(36).slice(2, 10)}`,
    execution_id: `exec-${i}`,
    workflow_id: `wf-${i}`,
    workflow_name: workflows[i % workflows.length],
    step: i + 1,
    step_name: `Step ${i + 1}`,
    status: 'pending' as const,
    content: 'Sample approval content',
    context: {},
    created_at: new Date(Date.now() - i * 1800000).toISOString(),
  }));
}
