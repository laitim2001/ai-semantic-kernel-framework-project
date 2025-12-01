// =============================================================================
// IPA Platform - Audit Page
// =============================================================================
// Sprint 5: Frontend UI - Audit Log
//
// Audit log viewer for system activities.
// =============================================================================

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Filter } from 'lucide-react';
import { api } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { PageLoading } from '@/components/shared/LoadingSpinner';
import { EmptyState } from '@/components/shared/EmptyState';
import { formatDate } from '@/lib/utils';
import type { AuditLog } from '@/types';

export function AuditPage() {
  const [searchQuery, setSearchQuery] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['audit-logs', searchQuery],
    queryFn: () => api.get<AuditLog[]>(`/audit?search=${searchQuery}`),
  });

  // Use mock data if API not available
  const logs = data || generateMockAuditLogs();

  if (isLoading) {
    return <PageLoading />;
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">審計日誌</h1>
        <p className="text-gray-500">查看系統活動記錄和操作歷史</p>
      </div>

      {/* Search and filters */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="搜索日誌..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>
        <Button variant="outline">
          <Filter className="w-4 h-4 mr-2" />
          篩選
        </Button>
      </div>

      {/* Logs list */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">活動記錄</CardTitle>
        </CardHeader>
        <CardContent>
          {logs.length === 0 ? (
            <EmptyState title="暫無日誌" description="目前沒有任何活動記錄" />
          ) : (
            <div className="space-y-4">
              {logs.map((log) => (
                <div
                  key={log.id}
                  className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant={getActionVariant(log.action)}>
                        {log.action}
                      </Badge>
                      <span className="text-sm text-gray-500">
                        {log.resource_type}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700">
                      {log.user_name || 'System'} 對 {log.resource_type}{' '}
                      <code className="bg-gray-200 px-1 rounded">
                        {log.resource_id.slice(0, 8)}
                      </code>{' '}
                      執行了 {log.action} 操作
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      {formatDate(log.timestamp)}
                      {log.ip_address && ` · ${log.ip_address}`}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function getActionVariant(
  action: string
): 'success' | 'warning' | 'destructive' | 'info' {
  if (action.includes('create') || action.includes('approve')) return 'success';
  if (action.includes('delete') || action.includes('reject')) return 'destructive';
  if (action.includes('update') || action.includes('edit')) return 'warning';
  return 'info';
}

// Generate mock data
function generateMockAuditLogs(): AuditLog[] {
  return [
    {
      id: 'log-1',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      action: 'workflow.execute',
      resource_type: 'workflow',
      resource_id: 'wf-1234567890',
      user_name: 'Admin',
      details: { trigger: 'manual' },
      ip_address: '192.168.1.100',
    },
    {
      id: 'log-2',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      action: 'checkpoint.approve',
      resource_type: 'checkpoint',
      resource_id: 'cp-0987654321',
      user_name: 'Manager',
      details: { feedback: 'Approved' },
      ip_address: '192.168.1.101',
    },
    {
      id: 'log-3',
      timestamp: new Date(Date.now() - 10800000).toISOString(),
      action: 'agent.create',
      resource_type: 'agent',
      resource_id: 'agent-abcdef',
      user_name: 'Developer',
      details: { template: 'it-support' },
      ip_address: '192.168.1.102',
    },
    {
      id: 'log-4',
      timestamp: new Date(Date.now() - 14400000).toISOString(),
      action: 'workflow.update',
      resource_type: 'workflow',
      resource_id: 'wf-xyz123456',
      user_name: 'Admin',
      details: { version: '1.2.0' },
      ip_address: '192.168.1.100',
    },
  ];
}
