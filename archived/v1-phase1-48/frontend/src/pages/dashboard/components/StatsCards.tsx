// =============================================================================
// IPA Platform - Stats Cards Component
// =============================================================================
// Sprint 5: Frontend UI - Dashboard Components
//
// Key metrics display cards for the dashboard.
// =============================================================================

import { Card, CardContent } from '@/components/ui/Card';
import {
  PlayCircle,
  CheckCircle,
  Clock,
  DollarSign,
} from 'lucide-react';
import { formatNumber, formatCurrency, formatPercentage } from '@/lib/utils';
import type { DashboardStats } from '@/types';

interface StatsCardsProps {
  stats?: DashboardStats;
}

export function StatsCards({ stats }: StatsCardsProps) {
  const cards = [
    {
      title: '總執行數',
      value: formatNumber(stats?.total_executions || 0),
      icon: PlayCircle,
      color: 'text-blue-500',
      bgColor: 'bg-blue-50',
    },
    {
      title: '成功率',
      value: formatPercentage(stats?.success_rate || 0),
      icon: CheckCircle,
      color: 'text-green-500',
      bgColor: 'bg-green-50',
    },
    {
      title: '待審批',
      value: formatNumber(stats?.pending_approvals || 0),
      icon: Clock,
      color: 'text-orange-500',
      bgColor: 'bg-orange-50',
    },
    {
      title: '今日 LLM 成本',
      value: formatCurrency(stats?.llm_cost_today || 0),
      icon: DollarSign,
      color: 'text-purple-500',
      bgColor: 'bg-purple-50',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <Card key={card.title}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{card.title}</p>
                <p className="text-2xl font-bold mt-1">{card.value}</p>
              </div>
              <div className={`p-3 rounded-full ${card.bgColor}`}>
                <card.icon className={`h-6 w-6 ${card.color}`} />
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
