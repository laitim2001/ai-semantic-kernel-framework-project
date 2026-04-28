// =============================================================================
// IPA Platform - Dashboard Page
// =============================================================================
// Sprint 5: Frontend UI - S5-2 Dashboard
//
// Main dashboard page with system overview and key metrics.
//
// Dependencies:
//   - TanStack Query
//   - Recharts
// =============================================================================

import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { PageLoading } from '@/components/shared/LoadingSpinner';
import { StatsCards } from './components/StatsCards';
import { ExecutionChart } from './components/ExecutionChart';
import { RecentExecutions } from './components/RecentExecutions';
import { PendingApprovals } from './components/PendingApprovals';
import type { DashboardStats } from '@/types';

export function DashboardPage() {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.get<DashboardStats>('/dashboard/stats'),
  });

  if (isLoading) {
    return <PageLoading />;
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">載入失敗，請重試</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page title */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">系統概覽和關鍵指標</p>
      </div>

      {/* Stats cards */}
      <StatsCards stats={stats} />

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Execution chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">執行統計</CardTitle>
          </CardHeader>
          <CardContent>
            <ExecutionChart />
          </CardContent>
        </Card>

        {/* Pending approvals */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">待審批項目</CardTitle>
          </CardHeader>
          <CardContent>
            <PendingApprovals />
          </CardContent>
        </Card>
      </div>

      {/* Recent executions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">最近執行</CardTitle>
        </CardHeader>
        <CardContent>
          <RecentExecutions />
        </CardContent>
      </Card>
    </div>
  );
}
