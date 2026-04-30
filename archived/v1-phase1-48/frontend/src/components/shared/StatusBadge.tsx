// =============================================================================
// IPA Platform - Status Badge Component
// =============================================================================
// Sprint 5: Frontend UI - Shared Components
//
// Status indicator badge for workflows, executions, etc.
// =============================================================================

import { Badge } from '@/components/ui/Badge';
import type { Status } from '@/types';

interface StatusBadgeProps {
  status: Status | string;
  className?: string;
}

const statusConfig: Record<string, { label: string; variant: 'success' | 'warning' | 'destructive' | 'info' | 'secondary' }> = {
  pending: { label: '待處理', variant: 'warning' },
  running: { label: '執行中', variant: 'info' },
  completed: { label: '已完成', variant: 'success' },
  failed: { label: '失敗', variant: 'destructive' },
  paused: { label: '已暫停', variant: 'secondary' },
  active: { label: '啟用', variant: 'success' },
  inactive: { label: '停用', variant: 'secondary' },
  draft: { label: '草稿', variant: 'secondary' },
  approved: { label: '已批准', variant: 'success' },
  rejected: { label: '已拒絕', variant: 'destructive' },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status] || { label: status, variant: 'secondary' as const };

  return (
    <Badge variant={config.variant} className={className}>
      {config.label}
    </Badge>
  );
}
