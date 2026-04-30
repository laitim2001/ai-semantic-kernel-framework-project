// =============================================================================
// IPA Platform - DevUI Statistics Dashboard Component
// =============================================================================
// Sprint 89: S89-1 - Statistics Dashboard
//
// Comprehensive statistics dashboard for trace execution analysis.
//
// Dependencies:
//   - Lucide React
//   - Tailwind CSS
//   - StatCard, EventPieChart
// =============================================================================

import { FC, useMemo } from 'react';
import {
  Bot,
  Wrench,
  Activity,
  AlertTriangle,
  XCircle,
  CheckCircle,
  Clock,
  Zap,
} from 'lucide-react';
import type { TraceEvent } from '@/types/devtools';
import { StatCard, MiniStatCard } from './StatCard';
import { EventPieChart, getEventTypeColor } from './EventPieChart';
import { DurationBar } from './DurationBar';
import { cn } from '@/lib/utils';

interface StatisticsProps {
  /** Trace events to analyze */
  events: TraceEvent[];
  /** Total trace duration in milliseconds */
  totalDurationMs?: number;
  /** Show detailed breakdown */
  showDetails?: boolean;
  /** Layout mode */
  layout?: 'horizontal' | 'vertical';
  /** Additional CSS classes */
  className?: string;
}

/**
 * Calculate statistics from events
 */
function calculateStatistics(events: TraceEvent[]) {
  const stats = {
    total: events.length,
    byType: {} as Record<string, number>,
    bySeverity: {} as Record<string, number>,
    llmCalls: 0,
    llmTotalMs: 0,
    toolCalls: 0,
    toolTotalMs: 0,
    toolSuccess: 0,
    toolFailed: 0,
    errors: 0,
    warnings: 0,
    checkpoints: 0,
    checkpointApproved: 0,
    checkpointRejected: 0,
    checkpointTimeout: 0,
  };

  events.forEach((event) => {
    const type = event.event_type.toUpperCase();

    // Count by type
    stats.byType[event.event_type] = (stats.byType[event.event_type] || 0) + 1;

    // Count by severity
    stats.bySeverity[event.severity] = (stats.bySeverity[event.severity] || 0) + 1;

    // LLM stats
    if (type.includes('LLM_REQUEST') || type.includes('LLM_RESPONSE')) {
      stats.llmCalls++;
      if (event.duration_ms) {
        stats.llmTotalMs += event.duration_ms;
      }
    }

    // Tool stats
    if (type.includes('TOOL_CALL') || type.includes('TOOL_RESULT')) {
      stats.toolCalls++;
      if (event.duration_ms) {
        stats.toolTotalMs += event.duration_ms;
      }
      // Check for success/failure in tool results
      if (type.includes('TOOL_RESULT')) {
        const hasError = event.data?.error || event.severity === 'error';
        if (hasError) {
          stats.toolFailed++;
        } else {
          stats.toolSuccess++;
        }
      }
    }

    // Error/Warning stats
    if (type.includes('ERROR') || event.severity === 'error') {
      stats.errors++;
    }
    if (type.includes('WARNING') || event.severity === 'warning') {
      stats.warnings++;
    }

    // Checkpoint stats
    if (type.includes('CHECKPOINT')) {
      stats.checkpoints++;
      if (type.includes('APPROVED')) stats.checkpointApproved++;
      if (type.includes('REJECTED')) stats.checkpointRejected++;
      if (type.includes('TIMEOUT')) stats.checkpointTimeout++;
    }
  });

  return stats;
}

/**
 * Statistics Dashboard Component
 * Displays comprehensive execution statistics
 */
export const Statistics: FC<StatisticsProps> = ({
  events,
  totalDurationMs,
  showDetails = true,
  layout = 'horizontal',
  className,
}) => {
  // Calculate statistics
  const stats = useMemo(() => calculateStatistics(events), [events]);

  // Prepare pie chart data
  const pieChartData = useMemo(() => {
    return Object.entries(stats.byType)
      .map(([type, count]) => ({
        label: type,
        value: count,
        color: getEventTypeColor(type),
      }))
      .sort((a, b) => b.value - a.value);
  }, [stats.byType]);

  // Calculate averages
  const llmAvgMs = stats.llmCalls > 0 ? Math.round(stats.llmTotalMs / (stats.llmCalls / 2)) : 0;
  const toolSuccessRate = stats.toolSuccess + stats.toolFailed > 0
    ? Math.round((stats.toolSuccess / (stats.toolSuccess + stats.toolFailed)) * 100)
    : 100;

  // Format duration
  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const isHorizontal = layout === 'horizontal';

  return (
    <div className={cn('space-y-6', className)}>
      {/* Main Stats Grid */}
      <div className={cn(
        'grid gap-4',
        isHorizontal
          ? 'grid-cols-2 lg:grid-cols-4'
          : 'grid-cols-1 sm:grid-cols-2'
      )}>
        {/* LLM Stats */}
        <StatCard
          title="LLM 調用"
          value={Math.floor(stats.llmCalls / 2)}
          description={`平均 ${formatDuration(llmAvgMs)}`}
          icon={Bot}
          variant="purple"
        >
          {stats.llmTotalMs > 0 && (
            <DurationBar
              durationMs={stats.llmTotalMs}
              maxDurationMs={totalDurationMs || stats.llmTotalMs}
              variant="default"
            />
          )}
        </StatCard>

        {/* Tool Stats */}
        <StatCard
          title="工具調用"
          value={Math.floor(stats.toolCalls / 2)}
          description={`成功率 ${toolSuccessRate}%`}
          icon={Wrench}
          variant="green"
          trend={toolSuccessRate >= 90 ? 'up' : toolSuccessRate >= 70 ? 'neutral' : 'down'}
          trendValue={`${toolSuccessRate}%`}
        >
          {stats.toolTotalMs > 0 && (
            <DurationBar
              durationMs={stats.toolTotalMs}
              maxDurationMs={totalDurationMs || stats.toolTotalMs}
              variant="success"
            />
          )}
        </StatCard>

        {/* Event Stats */}
        <StatCard
          title="總事件數"
          value={stats.total}
          description={`${Object.keys(stats.byType).length} 種類型`}
          icon={Activity}
          variant="blue"
        />

        {/* Error/Warning Stats */}
        <StatCard
          title="錯誤 / 警告"
          value={`${stats.errors} / ${stats.warnings}`}
          icon={stats.errors > 0 ? XCircle : AlertTriangle}
          variant={stats.errors > 0 ? 'red' : stats.warnings > 0 ? 'yellow' : 'default'}
        >
          <div className="flex gap-2">
            <MiniStatCard
              label="錯誤"
              value={stats.errors}
              variant={stats.errors > 0 ? 'error' : 'default'}
            />
            <MiniStatCard
              label="警告"
              value={stats.warnings}
              variant={stats.warnings > 0 ? 'warning' : 'default'}
            />
          </div>
        </StatCard>
      </div>

      {/* Detailed Stats (Optional) */}
      {showDetails && (
        <div className={cn(
          'grid gap-6',
          isHorizontal ? 'lg:grid-cols-2' : 'grid-cols-1'
        )}>
          {/* Event Distribution Pie Chart */}
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-700 mb-4">事件類型分佈</h3>
            <EventPieChart
              data={pieChartData}
              size={180}
              innerRadius={0.5}
              centerValue={stats.total}
              centerLabel="總事件"
            />
          </div>

          {/* Additional Stats */}
          <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
            <h3 className="text-sm font-medium text-gray-700">詳細統計</h3>

            {/* Performance Stats */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-600">總執行時間</span>
                </div>
                <span className="text-sm font-medium text-gray-900">
                  {totalDurationMs ? formatDuration(totalDurationMs) : '-'}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bot className="w-4 h-4 text-purple-500" />
                  <span className="text-sm text-gray-600">LLM 總耗時</span>
                </div>
                <span className="text-sm font-medium text-gray-900">
                  {formatDuration(stats.llmTotalMs)}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Wrench className="w-4 h-4 text-green-500" />
                  <span className="text-sm text-gray-600">工具總耗時</span>
                </div>
                <span className="text-sm font-medium text-gray-900">
                  {formatDuration(stats.toolTotalMs)}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-indigo-500" />
                  <span className="text-sm text-gray-600">平均事件間隔</span>
                </div>
                <span className="text-sm font-medium text-gray-900">
                  {stats.total > 1 && totalDurationMs
                    ? formatDuration(Math.round(totalDurationMs / stats.total))
                    : '-'}
                </span>
              </div>
            </div>

            {/* Checkpoint Stats (if any) */}
            {stats.checkpoints > 0 && (
              <>
                <div className="border-t border-gray-100 pt-3">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle className="w-4 h-4 text-yellow-500" />
                    <span className="text-sm font-medium text-gray-700">檢查點統計</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <MiniStatCard label="創建" value={stats.checkpoints} />
                    <MiniStatCard label="批准" value={stats.checkpointApproved} variant="success" />
                    <MiniStatCard label="拒絕" value={stats.checkpointRejected} variant="error" />
                    <MiniStatCard label="超時" value={stats.checkpointTimeout} variant="warning" />
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * Compact Statistics Summary
 */
export const StatisticsSummary: FC<{
  events: TraceEvent[];
  className?: string;
}> = ({ events, className }) => {
  const stats = useMemo(() => calculateStatistics(events), [events]);

  return (
    <div className={cn('flex flex-wrap gap-3', className)}>
      <MiniStatCard label="事件" value={stats.total} />
      <MiniStatCard
        label="LLM"
        value={Math.floor(stats.llmCalls / 2)}
        icon={Bot}
      />
      <MiniStatCard
        label="工具"
        value={Math.floor(stats.toolCalls / 2)}
        icon={Wrench}
      />
      {stats.errors > 0 && (
        <MiniStatCard
          label="錯誤"
          value={stats.errors}
          variant="error"
          icon={XCircle}
        />
      )}
      {stats.warnings > 0 && (
        <MiniStatCard
          label="警告"
          value={stats.warnings}
          variant="warning"
          icon={AlertTriangle}
        />
      )}
    </div>
  );
};

export default Statistics;
