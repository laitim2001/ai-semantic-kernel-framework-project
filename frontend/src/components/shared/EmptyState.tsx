// =============================================================================
// IPA Platform - Empty State Component
// =============================================================================
// Sprint 5: Frontend UI - Shared Components
//
// Empty state display for lists and tables with no data.
// =============================================================================

import { FileQuestion } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface EmptyStateProps {
  title?: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  icon?: React.ReactNode;
}

export function EmptyState({
  title = '暫無數據',
  description = '目前沒有任何內容可顯示',
  action,
  icon,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-4">
        {icon || <FileQuestion className="w-6 h-6 text-gray-400" />}
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-1">{title}</h3>
      <p className="text-sm text-gray-500 mb-4 max-w-sm">{description}</p>
      {action && (
        <Button onClick={action.onClick}>{action.label}</Button>
      )}
    </div>
  );
}
