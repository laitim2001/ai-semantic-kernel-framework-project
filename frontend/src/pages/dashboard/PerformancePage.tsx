// =============================================================================
// IPA Platform - Performance Monitoring Page
// =============================================================================
// Sprint 12 - S12-4: UI Integration
//
// Phase 2 performance monitoring dashboard with real-time metrics,
// concurrent execution stats, and optimization recommendations.
//
// Features:
//   - System performance metrics
//   - Phase 2 feature stats
//   - Concurrent execution monitoring
//   - Performance recommendations
//
// Dependencies:
//   - TanStack Query
//   - Recharts
// =============================================================================

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { PageLoading } from '@/components/shared/LoadingSpinner';
import { Badge } from '@/components/ui/Badge';
import {
  Activity,
  Cpu,
  HardDrive,
  Zap,
  Users,
  GitBranch,
  MessageSquare,
  Brain,
  Layers,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
} from 'recharts';

// Performance metrics types
interface SystemMetrics {
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  network_bytes_sent: number;
  network_bytes_recv: number;
}

interface Phase2Stats {
  concurrent_executions: number;
  handoff_success_rate: number;
  groupchat_sessions: number;
  planning_accuracy: number;
  nested_workflow_depth: number;
  avg_latency_ms: number;
  throughput_improvement: number;
}

interface PerformanceRecommendation {
  id: string;
  type: 'optimization' | 'warning' | 'info';
  title: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
}

interface PerformanceData {
  system_metrics: SystemMetrics;
  phase2_stats: Phase2Stats;
  recommendations: PerformanceRecommendation[];
  history: Array<{
    timestamp: string;
    cpu: number;
    memory: number;
    latency: number;
  }>;
}

// Mock data for development - will be replaced with real API calls
const mockPerformanceData: PerformanceData = {
  system_metrics: {
    cpu_percent: 45.2,
    memory_percent: 62.8,
    disk_percent: 38.5,
    network_bytes_sent: 1234567890,
    network_bytes_recv: 9876543210,
  },
  phase2_stats: {
    concurrent_executions: 12,
    handoff_success_rate: 97.5,
    groupchat_sessions: 8,
    planning_accuracy: 89.3,
    nested_workflow_depth: 4,
    avg_latency_ms: 145,
    throughput_improvement: 3.2,
  },
  recommendations: [
    {
      id: '1',
      type: 'optimization',
      title: 'Enable connection pooling',
      description: 'Connection pooling can reduce latency by 25%',
      impact: 'high',
    },
    {
      id: '2',
      type: 'warning',
      title: 'High memory usage detected',
      description: 'Memory usage is above 60%, consider scaling',
      impact: 'medium',
    },
    {
      id: '3',
      type: 'info',
      title: 'Caching optimization available',
      description: 'LLM response caching is enabled and working effectively',
      impact: 'low',
    },
  ],
  history: Array.from({ length: 24 }, (_, i) => ({
    timestamp: `${String(i).padStart(2, '0')}:00`,
    cpu: Math.random() * 60 + 20,
    memory: Math.random() * 30 + 50,
    latency: Math.random() * 100 + 100,
  })),
};

export function PerformancePage() {
  const [timeRange, setTimeRange] = useState<'1h' | '24h' | '7d'>('24h');

  const { data, isLoading, error } = useQuery({
    queryKey: ['performance-metrics', timeRange],
    queryFn: async () => {
      try {
        return await api.get<PerformanceData>(`/performance/metrics?range=${timeRange}`);
      } catch {
        // Return mock data for development
        return mockPerformanceData;
      }
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  if (isLoading) {
    return <PageLoading />;
  }

  if (error && !data) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">載入失敗，請重試</p>
      </div>
    );
  }

  const perfData = data || mockPerformanceData;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">效能監控</h1>
          <p className="text-gray-500">Phase 2 系統效能指標和優化建議</p>
        </div>
        <div className="flex gap-2">
          {(['1h', '24h', '7d'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                timeRange === range
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {range === '1h' ? '1 小時' : range === '24h' ? '24 小時' : '7 天'}
            </button>
          ))}
        </div>
      </div>

      {/* System metrics cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="CPU 使用率"
          value={`${perfData.system_metrics.cpu_percent.toFixed(1)}%`}
          icon={Cpu}
          color="blue"
          trend={perfData.system_metrics.cpu_percent > 80 ? 'warning' : 'normal'}
        />
        <MetricCard
          title="記憶體使用率"
          value={`${perfData.system_metrics.memory_percent.toFixed(1)}%`}
          icon={HardDrive}
          color="green"
          trend={perfData.system_metrics.memory_percent > 80 ? 'warning' : 'normal'}
        />
        <MetricCard
          title="平均延遲"
          value={`${perfData.phase2_stats.avg_latency_ms}ms`}
          icon={Activity}
          color="purple"
          trend={perfData.phase2_stats.avg_latency_ms > 200 ? 'warning' : 'good'}
        />
        <MetricCard
          title="吞吐量提升"
          value={`${perfData.phase2_stats.throughput_improvement.toFixed(1)}x`}
          icon={TrendingUp}
          color="orange"
          trend="good"
        />
      </div>

      {/* Phase 2 feature stats */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Phase 2 功能統計</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <FeatureStatCard
              title="並行執行"
              value={perfData.phase2_stats.concurrent_executions}
              icon={GitBranch}
              subtitle="當前執行中"
            />
            <FeatureStatCard
              title="Agent 交接"
              value={`${perfData.phase2_stats.handoff_success_rate}%`}
              icon={Users}
              subtitle="成功率"
            />
            <FeatureStatCard
              title="群組聊天"
              value={perfData.phase2_stats.groupchat_sessions}
              icon={MessageSquare}
              subtitle="活躍會話"
            />
            <FeatureStatCard
              title="動態規劃"
              value={`${perfData.phase2_stats.planning_accuracy}%`}
              icon={Brain}
              subtitle="準確率"
            />
            <FeatureStatCard
              title="嵌套工作流"
              value={`L${perfData.phase2_stats.nested_workflow_depth}`}
              icon={Layers}
              subtitle="最大深度"
            />
          </div>
        </CardContent>
      </Card>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CPU & Memory chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">系統資源使用</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={perfData.history}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" />
                <YAxis />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="cpu"
                  stackId="1"
                  stroke="#3B82F6"
                  fill="#93C5FD"
                  name="CPU %"
                />
                <Area
                  type="monotone"
                  dataKey="memory"
                  stackId="2"
                  stroke="#10B981"
                  fill="#6EE7B7"
                  name="記憶體 %"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Latency chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">延遲趨勢</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={perfData.history}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" />
                <YAxis />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="latency"
                  stroke="#8B5CF6"
                  strokeWidth={2}
                  dot={false}
                  name="延遲 (ms)"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">優化建議</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {perfData.recommendations.map((rec) => (
              <RecommendationCard key={rec.id} recommendation={rec} />
            ))}
            {perfData.recommendations.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <CheckCircle className="h-12 w-12 mx-auto text-green-500 mb-2" />
                <p>系統運行良好，暫無優化建議</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Metric card component
interface MetricCardProps {
  title: string;
  value: string;
  icon: React.ElementType;
  color: 'blue' | 'green' | 'purple' | 'orange';
  trend?: 'good' | 'warning' | 'normal';
}

function MetricCard({ title, value, icon: Icon, color, trend = 'normal' }: MetricCardProps) {
  const colorClasses = {
    blue: 'text-blue-500 bg-blue-50',
    green: 'text-green-500 bg-green-50',
    purple: 'text-purple-500 bg-purple-50',
    orange: 'text-orange-500 bg-orange-50',
  };

  const trendIndicator = {
    good: <TrendingUp className="h-4 w-4 text-green-500" />,
    warning: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
    normal: null,
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500">{title}</p>
            <div className="flex items-center gap-2 mt-1">
              <p className="text-2xl font-bold">{value}</p>
              {trendIndicator[trend]}
            </div>
          </div>
          <div className={`p-3 rounded-full ${colorClasses[color]}`}>
            <Icon className="h-6 w-6" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Feature stat card component
interface FeatureStatCardProps {
  title: string;
  value: string | number;
  icon: React.ElementType;
  subtitle: string;
}

function FeatureStatCard({ title, value, icon: Icon, subtitle }: FeatureStatCardProps) {
  return (
    <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg">
      <div className="p-2 bg-white rounded-lg shadow-sm">
        <Icon className="h-5 w-5 text-gray-600" />
      </div>
      <div>
        <p className="text-sm text-gray-500">{title}</p>
        <p className="text-xl font-semibold">{value}</p>
        <p className="text-xs text-gray-400">{subtitle}</p>
      </div>
    </div>
  );
}

// Recommendation card component
interface RecommendationCardProps {
  recommendation: PerformanceRecommendation;
}

function RecommendationCard({ recommendation }: RecommendationCardProps) {
  const typeConfig = {
    optimization: {
      icon: Zap,
      bgColor: 'bg-blue-50',
      textColor: 'text-blue-700',
      borderColor: 'border-blue-200',
    },
    warning: {
      icon: AlertTriangle,
      bgColor: 'bg-yellow-50',
      textColor: 'text-yellow-700',
      borderColor: 'border-yellow-200',
    },
    info: {
      icon: CheckCircle,
      bgColor: 'bg-green-50',
      textColor: 'text-green-700',
      borderColor: 'border-green-200',
    },
  };

  const impactBadge = {
    high: <Badge variant="destructive">高優先</Badge>,
    medium: <Badge variant="secondary">中優先</Badge>,
    low: <Badge variant="outline">低優先</Badge>,
  };

  const config = typeConfig[recommendation.type];
  const Icon = config.icon;

  return (
    <div className={`flex items-start gap-4 p-4 rounded-lg border ${config.bgColor} ${config.borderColor}`}>
      <div className={`p-2 rounded-full ${config.bgColor}`}>
        <Icon className={`h-5 w-5 ${config.textColor}`} />
      </div>
      <div className="flex-1">
        <div className="flex items-center justify-between">
          <h4 className="font-medium text-gray-900">{recommendation.title}</h4>
          {impactBadge[recommendation.impact]}
        </div>
        <p className="text-sm text-gray-600 mt-1">{recommendation.description}</p>
      </div>
    </div>
  );
}
