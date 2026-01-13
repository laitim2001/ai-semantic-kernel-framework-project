// =============================================================================
// IPA Platform - DevUI Trace List Page
// =============================================================================
// Sprint 87: S87-2 - DevUI Core Pages
//
// Page displaying list of execution traces with filtering and pagination.
//
// Dependencies:
//   - React Query
//   - DevTools hooks
// =============================================================================

import { FC, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  Search,
  Filter,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
} from 'lucide-react';
import { useTraces } from '@/hooks/useDevTools';
import type { TraceStatus } from '@/types/devtools';
import { cn } from '@/lib/utils';

/**
 * Status badge component
 */
const StatusBadge: FC<{ status: TraceStatus }> = ({ status }) => {
  const config = {
    running: { icon: Clock, bg: 'bg-blue-100', text: 'text-blue-700', label: 'Running' },
    completed: { icon: CheckCircle, bg: 'bg-green-100', text: 'text-green-700', label: 'Completed' },
    failed: { icon: XCircle, bg: 'bg-red-100', text: 'text-red-700', label: 'Failed' },
  }[status];

  const Icon = config.icon;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
        config.bg,
        config.text
      )}
    >
      <Icon className="w-3 h-3" />
      {config.label}
    </span>
  );
};

/**
 * Format duration in human-readable form
 */
function formatDuration(ms?: number): string {
  if (ms === undefined || ms === null) return '-';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

/**
 * Format date in human-readable form
 */
function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * Trace List Page Component
 */
export const TraceList: FC = () => {
  // Filter state
  const [statusFilter, setStatusFilter] = useState<TraceStatus | ''>('');
  const [workflowIdFilter, setWorkflowIdFilter] = useState('');
  const [page, setPage] = useState(0);
  const pageSize = 20;

  // Build query params
  const queryParams = useMemo(
    () => ({
      status: statusFilter || undefined,
      workflow_id: workflowIdFilter || undefined,
      limit: pageSize,
      offset: page * pageSize,
    }),
    [statusFilter, workflowIdFilter, page]
  );

  // Fetch traces
  const { data, isLoading, isError, refetch, isFetching } = useTraces(queryParams);

  // Safe access to items array
  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  // Pagination info
  const totalPages = total > 0 ? Math.ceil(total / pageSize) : 0;

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Execution Traces</h1>
          <p className="mt-1 text-sm text-gray-500">
            Browse and inspect workflow execution traces
          </p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw className={cn('w-4 h-4', isFetching && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
        <div className="flex items-center gap-4">
          <Filter className="w-4 h-4 text-gray-400" />
          <span className="text-sm font-medium text-gray-700">Filters:</span>

          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as TraceStatus | '');
              setPage(0);
            }}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="">All Status</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>

          {/* Workflow ID filter */}
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Filter by Workflow ID..."
              value={workflowIdFilter}
              onChange={(e) => {
                setWorkflowIdFilter(e.target.value);
                setPage(0);
              }}
              className="w-full pl-9 pr-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>

          {/* Clear filters */}
          {(statusFilter || workflowIdFilter) && (
            <button
              onClick={() => {
                setStatusFilter('');
                setWorkflowIdFilter('');
                setPage(0);
              }}
              className="text-sm text-purple-600 hover:text-purple-700"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center p-12">
            <Loader2 className="w-6 h-6 text-purple-600 animate-spin" />
            <span className="ml-2 text-gray-500">Loading traces...</span>
          </div>
        ) : isError ? (
          <div className="p-12 text-center">
            <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <p className="text-gray-500">Failed to load traces. Please try again.</p>
            <button
              onClick={() => refetch()}
              className="mt-4 text-purple-600 hover:text-purple-700"
            >
              Retry
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center text-gray-500">
            No traces found matching your criteria.
          </div>
        ) : (
          <>
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Execution ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Workflow ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Started At
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Events
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Duration
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {items.map((trace) => (
                  <tr
                    key={trace.id}
                    className="hover:bg-gray-50 transition-colors cursor-pointer"
                  >
                    <td className="px-4 py-3">
                      <Link
                        to={`/devui/traces/${trace.execution_id}`}
                        className="text-sm font-mono text-purple-600 hover:text-purple-700"
                      >
                        {trace.execution_id.slice(0, 12)}...
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-gray-900">{trace.workflow_id}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-gray-500">
                        {formatDate(trace.started_at)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={trace.status} />
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-gray-900">{trace.event_count}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-gray-500">
                        {formatDuration(trace.duration_ms)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
              <div className="text-sm text-gray-500">
                Showing {page * pageSize + 1} to{' '}
                {Math.min((page + 1) * pageSize, total)} of {total}{' '}
                results
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="p-2 text-gray-600 hover:bg-gray-200 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-sm text-gray-700">
                  Page {page + 1} of {totalPages || 1}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                  className="p-2 text-gray-600 hover:bg-gray-200 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default TraceList;
