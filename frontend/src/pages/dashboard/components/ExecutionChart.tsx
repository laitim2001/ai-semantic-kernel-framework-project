// =============================================================================
// IPA Platform - Execution Chart Component
// =============================================================================
// Sprint 5: Frontend UI - Dashboard Components
//
// Line chart showing execution statistics over time.
//
// Dependencies:
//   - Recharts
// =============================================================================

import { useQuery } from '@tanstack/react-query';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { api } from '@/api/client';
import { LoadingSpinner } from '@/components/shared/LoadingSpinner';
import type { ExecutionChartData } from '@/types';

export function ExecutionChart() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-execution-chart'],
    queryFn: () => api.get<ExecutionChartData[]>('/dashboard/executions/chart'),
  });

  if (isLoading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  // Use mock data if API not available
  const chartData = data || generateMockData();

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => value.slice(5)}
          />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="success"
            name="成功"
            stroke="#22c55e"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="failed"
            name="失敗"
            stroke="#ef4444"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// Generate mock data for demo
function generateMockData(): ExecutionChartData[] {
  const data: ExecutionChartData[] = [];
  const today = new Date();

  for (let i = 6; i >= 0; i--) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);
    data.push({
      date: date.toISOString().slice(0, 10),
      total: Math.floor(Math.random() * 50) + 20,
      success: Math.floor(Math.random() * 40) + 15,
      failed: Math.floor(Math.random() * 10),
    });
  }

  return data;
}
