// =============================================================================
// IPA Platform - DevUI Trace Detail Page
// =============================================================================
// Sprint 87: S87-3 - DevUI Core Pages
//
// Page displaying detailed trace information with events.
//
// Dependencies:
//   - React Router
//   - React Query
//   - DevTools hooks
// =============================================================================

import { FC, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Clock,
  CheckCircle,
  XCircle,
  Trash2,
  RefreshCw,
  Copy,
  Check,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import { useTrace, useTraceEvents, useDeleteTrace } from '@/hooks/useDevTools';
import { EventList } from '@/components/DevUI/EventList';
import type { TraceStatus } from '@/types/devtools';
import { cn } from '@/lib/utils';

/**
 * Status configuration
 */
const statusConfig: Record<
  TraceStatus,
  { icon: React.ComponentType<{ className?: string }>; bg: string; text: string }
> = {
  running: { icon: Clock, bg: 'bg-blue-100', text: 'text-blue-700' },
  completed: { icon: CheckCircle, bg: 'bg-green-100', text: 'text-green-700' },
  failed: { icon: XCircle, bg: 'bg-red-100', text: 'text-red-700' },
};

/**
 * Format date for display
 */
function formatDate(dateStr?: string): string {
  if (!dateStr) return '-';
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
 * Format duration for display
 */
function formatDuration(ms?: number): string {
  if (ms === undefined || ms === null) return '-';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
  return `${(ms / 60000).toFixed(2)}m`;
}

/**
 * Copy button component
 */
const CopyButton: FC<{ text: string }> = ({ text }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
      title="Copy to clipboard"
    >
      {copied ? (
        <Check className="w-4 h-4 text-green-500" />
      ) : (
        <Copy className="w-4 h-4" />
      )}
    </button>
  );
};

/**
 * Info item component
 */
const InfoItem: FC<{ label: string; value: string; copyable?: boolean }> = ({
  label,
  value,
  copyable,
}) => (
  <div>
    <div className="text-xs text-gray-500 mb-1">{label}</div>
    <div className="flex items-center gap-1">
      <span className="text-sm text-gray-900 font-mono">{value}</span>
      {copyable && <CopyButton text={value} />}
    </div>
  </div>
);

/**
 * Trace Detail Page Component
 */
export const TraceDetail: FC = () => {
  const { id: executionId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Fetch trace data
  const {
    data: trace,
    isLoading: traceLoading,
    isError: traceError,
    refetch: refetchTrace,
  } = useTrace(executionId ?? '');

  // Fetch events
  const {
    data: eventsData,
    isLoading: eventsLoading,
    refetch: refetchEvents,
  } = useTraceEvents(executionId ?? '');

  // Delete mutation
  const deleteMutation = useDeleteTrace();

  // Handle delete
  const handleDelete = async () => {
    if (!executionId) return;
    try {
      await deleteMutation.mutateAsync(executionId);
      navigate('/devui/traces');
    } catch (error) {
      console.error('Failed to delete trace:', error);
    }
  };

  // Handle refresh
  const handleRefresh = () => {
    refetchTrace();
    refetchEvents();
  };

  if (traceLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
      </div>
    );
  }

  if (traceError || !trace) {
    return (
      <div className="p-6">
        <button
          onClick={() => navigate('/devui/traces')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Traces
        </button>
        <div className="text-center py-12">
          <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-gray-500">Failed to load trace details.</p>
          <button
            onClick={() => refetchTrace()}
            className="mt-4 text-purple-600 hover:text-purple-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const StatusIcon = statusConfig[trace.status].icon;

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/devui/traces')}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Trace Details</h1>
            <p className="text-sm text-gray-500 font-mono">{executionId}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="flex items-center gap-2 px-3 py-2 text-sm text-red-600 bg-white border border-red-300 rounded-lg hover:bg-red-50"
          >
            <Trash2 className="w-4 h-4" />
            Delete
          </button>
        </div>
      </div>

      {/* Trace Info Card */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Trace Information</h2>
          <span
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium',
              statusConfig[trace.status].bg,
              statusConfig[trace.status].text
            )}
          >
            <StatusIcon className="w-4 h-4" />
            {trace.status.charAt(0).toUpperCase() + trace.status.slice(1)}
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <InfoItem
            label="Execution ID"
            value={trace.execution_id}
            copyable
          />
          <InfoItem
            label="Workflow ID"
            value={trace.workflow_id}
            copyable
          />
          <InfoItem label="Started At" value={formatDate(trace.started_at)} />
          <InfoItem label="Ended At" value={formatDate(trace.ended_at)} />
          <InfoItem label="Duration" value={formatDuration(trace.duration_ms)} />
          <InfoItem label="Event Count" value={String(trace.event_count)} />
          <InfoItem label="Span Count" value={String(trace.span_count)} />
        </div>

        {/* Events Summary */}
        {trace.events_summary && (
          <div className="mt-6 pt-6 border-t border-gray-200">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Events Summary</h3>
            <div className="grid grid-cols-2 gap-6">
              {/* By Type */}
              <div>
                <div className="text-xs text-gray-500 mb-2">By Type</div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(trace.events_summary.by_type).map(([type, count]) => (
                    <span
                      key={type}
                      className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs"
                    >
                      {type}: {count}
                    </span>
                  ))}
                </div>
              </div>
              {/* By Severity */}
              <div>
                <div className="text-xs text-gray-500 mb-2">By Severity</div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(trace.events_summary.by_severity).map(
                    ([severity, count]) => (
                      <span
                        key={severity}
                        className={cn(
                          'px-2 py-1 rounded text-xs',
                          severity === 'error' || severity === 'critical'
                            ? 'bg-red-100 text-red-700'
                            : severity === 'warning'
                            ? 'bg-yellow-100 text-yellow-700'
                            : 'bg-gray-100 text-gray-700'
                        )}
                      >
                        {severity}: {count}
                      </span>
                    )
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Events List */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Events</h2>
        </div>
        <EventList events={eventsData?.items ?? []} isLoading={eventsLoading} />
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Delete Trace</h3>
                <p className="text-sm text-gray-500">This action cannot be undone.</p>
              </div>
            </div>
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete this trace and all its events?
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TraceDetail;
