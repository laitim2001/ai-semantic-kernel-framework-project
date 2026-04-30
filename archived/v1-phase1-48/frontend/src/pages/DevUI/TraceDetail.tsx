// =============================================================================
// IPA Platform - DevUI Trace Detail Page
// =============================================================================
// Sprint 87: S87-3 - DevUI Core Pages
// Sprint 88: Updated with Timeline, EventTree, and EventPanel components
// Sprint 89: Added Statistics, LiveIndicator, and EventFilter
//
// Page displaying detailed trace information with events.
//
// Dependencies:
//   - React Router
//   - React Query
//   - DevTools hooks
//   - Timeline, EventTree, EventPanel, Statistics, LiveIndicator, EventFilter
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
  LayoutList,
  GitBranch,
  Activity,
  BarChart3,
  Filter,
} from 'lucide-react';
import { useTrace, useTraceEvents, useDeleteTrace } from '@/hooks/useDevTools';
import { useEventFilter } from '@/hooks/useEventFilter';
import { EventList } from '@/components/DevUI/EventList';
import { Timeline } from '@/components/DevUI/Timeline';
import { EventTree } from '@/components/DevUI/EventTree';
import { EventPanel } from '@/components/DevUI/EventPanel';
import { Statistics, StatisticsSummary } from '@/components/DevUI/Statistics';
import { LiveIndicator } from '@/components/DevUI/LiveIndicator';
import { EventFilter } from '@/components/DevUI/EventFilter';
import type { TraceStatus, TraceEvent } from '@/types/devtools';
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

/** View mode for events display */
type ViewMode = 'timeline' | 'tree' | 'list' | 'stats';

/**
 * Trace Detail Page Component
 */
export const TraceDetail: FC = () => {
  const { id: executionId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('timeline');
  const [selectedEvent, setSelectedEvent] = useState<TraceEvent | null>(null);
  const [showFilters, setShowFilters] = useState(false);

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

  // Event filtering
  const {
    filters,
    filteredEvents,
    filterCounts,
    filterOptions,
    hasActiveFilters,
    toggleEventType,
    toggleSeverity,
    toggleExecutorId,
    setSearchQuery,
    setShowErrorsOnly,
    clearFilters,
  } = useEventFilter(eventsData?.items ?? [], { syncToUrl: true });

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

      {/* Live Indicator for running traces */}
      {trace.status === 'running' && (
        <div className="mb-6">
          <LiveIndicator
            status="connected"
            isPaused={false}
            lastUpdate={new Date()}
            onPause={() => {}}
            onResume={() => {}}
            onDisconnect={() => {}}
          />
        </div>
      )}

      {/* Quick Stats Summary */}
      <div className="mb-6">
        <StatisticsSummary events={eventsData?.items ?? []} />
      </div>

      {/* Events Section */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Filters Panel (collapsible) */}
        {showFilters && viewMode !== 'stats' && (
          <div className="lg:col-span-1">
            <EventFilter
              eventTypes={filterOptions.eventTypes}
              selectedEventTypes={filters.eventTypes}
              severities={filterOptions.severities}
              selectedSeverities={filters.severities}
              executorIds={filterOptions.executorIds}
              selectedExecutorIds={filters.executorIds}
              searchQuery={filters.searchQuery}
              showErrorsOnly={filters.showErrorsOnly}
              hasActiveFilters={hasActiveFilters}
              filterCounts={filterCounts}
              onToggleEventType={toggleEventType}
              onToggleSeverity={toggleSeverity}
              onToggleExecutorId={toggleExecutorId}
              onSearchChange={setSearchQuery}
              onShowErrorsOnlyChange={setShowErrorsOnly}
              onClearFilters={clearFilters}
            />
          </div>
        )}

        {/* Events View */}
        <div className={cn(
          'bg-white rounded-lg border border-gray-200 overflow-hidden',
          showFilters && viewMode !== 'stats' ? 'lg:col-span-2' : selectedEvent ? 'lg:col-span-3' : 'lg:col-span-4',
          selectedEvent && showFilters && viewMode !== 'stats' && 'lg:col-span-2'
        )}>
          {/* View mode toggle */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-gray-900">Events</h2>
              {hasActiveFilters && viewMode !== 'stats' && (
                <span className="px-2 py-0.5 text-xs font-medium bg-purple-100 text-purple-700 rounded">
                  {filterCounts.filtered} / {filterCounts.total}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {/* Filter toggle button */}
              {viewMode !== 'stats' && (
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg transition-colors',
                    showFilters || hasActiveFilters
                      ? 'bg-purple-50 border-purple-200 text-purple-700'
                      : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                  )}
                >
                  <Filter className="w-4 h-4" />
                  {showFilters ? '隱藏篩選' : '篩選'}
                </button>
              )}
              {/* View mode toggle */}
              <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('stats')}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors',
                    viewMode === 'stats'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  )}
                >
                  <BarChart3 className="w-4 h-4" />
                  Stats
                </button>
                <button
                  onClick={() => setViewMode('timeline')}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors',
                    viewMode === 'timeline'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  )}
                >
                  <Activity className="w-4 h-4" />
                  Timeline
                </button>
                <button
                  onClick={() => setViewMode('tree')}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors',
                    viewMode === 'tree'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  )}
                >
                  <GitBranch className="w-4 h-4" />
                  Tree
                </button>
                <button
                  onClick={() => setViewMode('list')}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors',
                    viewMode === 'list'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  )}
                >
                  <LayoutList className="w-4 h-4" />
                  List
                </button>
              </div>
            </div>
          </div>

          {/* Events content based on view mode */}
          <div className="p-4">
            {eventsLoading ? (
              <div className="flex items-center justify-center p-12">
                <Loader2 className="w-6 h-6 text-purple-600 animate-spin" />
                <span className="ml-2 text-gray-500">Loading events...</span>
              </div>
            ) : viewMode === 'stats' ? (
              <Statistics
                events={eventsData?.items ?? []}
                totalDurationMs={trace.duration_ms}
                showDetails={true}
                layout="horizontal"
              />
            ) : viewMode === 'timeline' ? (
              <Timeline
                events={filteredEvents}
                selectedEventId={selectedEvent?.id}
                onEventSelect={setSelectedEvent}
                maxHeight="500px"
              />
            ) : viewMode === 'tree' ? (
              <EventTree
                events={filteredEvents}
                selectedEventId={selectedEvent?.id}
                onEventSelect={setSelectedEvent}
                maxHeight="500px"
              />
            ) : (
              <EventList
                events={filteredEvents}
                isLoading={false}
                onEventSelect={setSelectedEvent}
                selectedEventId={selectedEvent?.id}
              />
            )}
          </div>
        </div>

        {/* Event Detail Panel */}
        {selectedEvent && viewMode !== 'stats' && (
          <div className="lg:col-span-1">
            <EventPanel
              event={selectedEvent}
              onClose={() => setSelectedEvent(null)}
            />
          </div>
        )}
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
