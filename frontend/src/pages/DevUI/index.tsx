// =============================================================================
// IPA Platform - DevUI Overview Page
// =============================================================================
// Sprint 87: S87-1 - DevUI Core Pages
//
// DevUI overview/landing page showing summary statistics.
//
// Dependencies:
//   - React Query
//   - DevTools hooks
// =============================================================================

import { FC } from 'react';
import { Link } from 'react-router-dom';
import {
  ListTree,
  Activity,
  CheckCircle,
  XCircle,
  Clock,
  ArrowRight,
} from 'lucide-react';
import { useTraces } from '@/hooks/useDevTools';

/**
 * Stat card component
 */
interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  iconColor: string;
  bgColor: string;
}

const StatCard: FC<StatCardProps> = ({ title, value, icon: Icon, iconColor, bgColor }) => (
  <div className="bg-white rounded-lg border border-gray-200 p-6">
    <div className="flex items-center gap-4">
      <div className={`w-12 h-12 rounded-lg ${bgColor} flex items-center justify-center`}>
        <Icon className={`w-6 h-6 ${iconColor}`} />
      </div>
      <div>
        <p className="text-sm text-gray-500">{title}</p>
        <p className="text-2xl font-semibold text-gray-900">{value}</p>
      </div>
    </div>
  </div>
);

/**
 * DevUI Overview Page
 * Shows summary statistics and quick links
 */
export const DevUIOverview: FC = () => {
  // Fetch traces for statistics
  const { data: tracesData, isLoading } = useTraces({ limit: 100 });

  // Calculate statistics (with safe access for items array)
  const items = tracesData?.items ?? [];
  const stats = {
    total: tracesData?.total ?? 0,
    running: items.filter((t) => t.status === 'running').length,
    completed: items.filter((t) => t.status === 'completed').length,
    failed: items.filter((t) => t.status === 'failed').length,
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Developer Tools</h1>
        <p className="mt-1 text-gray-500">
          Monitor and debug workflow executions, traces, and events.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Total Traces"
          value={isLoading ? '-' : stats.total}
          icon={ListTree}
          iconColor="text-purple-600"
          bgColor="bg-purple-50"
        />
        <StatCard
          title="Running"
          value={isLoading ? '-' : stats.running}
          icon={Clock}
          iconColor="text-blue-600"
          bgColor="bg-blue-50"
        />
        <StatCard
          title="Completed"
          value={isLoading ? '-' : stats.completed}
          icon={CheckCircle}
          iconColor="text-green-600"
          bgColor="bg-green-50"
        />
        <StatCard
          title="Failed"
          value={isLoading ? '-' : stats.failed}
          icon={XCircle}
          iconColor="text-red-600"
          bgColor="bg-red-50"
        />
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link
          to="/devui/traces"
          className="bg-white rounded-lg border border-gray-200 p-6 hover:border-purple-300 hover:shadow-sm transition-all group"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-purple-50 flex items-center justify-center">
                <ListTree className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">View Traces</h3>
                <p className="text-sm text-gray-500">
                  Browse and inspect execution traces
                </p>
              </div>
            </div>
            <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-purple-600 transition-colors" />
          </div>
        </Link>

        <Link
          to="/devui/monitor"
          className="bg-white rounded-lg border border-gray-200 p-6 hover:border-purple-300 hover:shadow-sm transition-all group"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
                <Activity className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">Live Monitor</h3>
                <p className="text-sm text-gray-500">
                  Watch executions in real-time
                </p>
              </div>
            </div>
            <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-blue-600 transition-colors" />
          </div>
        </Link>
      </div>

      {/* Recent Activity */}
      <div className="mt-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h2>
        <div className="bg-white rounded-lg border border-gray-200">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">Loading...</div>
          ) : items.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No traces found. Execute a workflow to see traces here.
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {items.slice(0, 5).map((trace) => (
                <Link
                  key={trace.id}
                  to={`/devui/traces/${trace.execution_id}`}
                  className="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        trace.status === 'completed'
                          ? 'bg-green-500'
                          : trace.status === 'running'
                          ? 'bg-blue-500'
                          : 'bg-red-500'
                      }`}
                    />
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {trace.workflow_id}
                      </p>
                      <p className="text-xs text-gray-500">
                        {new Date(trace.started_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs px-2 py-1 rounded-full ${
                        trace.status === 'completed'
                          ? 'bg-green-100 text-green-700'
                          : trace.status === 'running'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {trace.status}
                    </span>
                    <span className="text-xs text-gray-500">
                      {trace.event_count} events
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DevUIOverview;
