/**
 * ApprovalList - Pending Approvals List Component
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-3: HITL Approval Components
 *
 * Displays a list of pending approval requests.
 * Supports sorting, filtering, and batch operations.
 */

import { FC, useState, useMemo, useCallback } from 'react';
import type { PendingApproval, RiskLevel } from '@/types/ag-ui';
import { Button } from '@/components/ui/Button';
import { ApprovalBanner } from './ApprovalBanner';

export interface ApprovalListProps {
  /** List of pending approvals */
  approvals: PendingApproval[];
  /** Callback when approved */
  onApprove: (approvalId: string) => void;
  /** Callback when rejected */
  onReject: (approvalId: string) => void;
  /** Callback for showing details */
  onShowDetails?: (approval: PendingApproval) => void;
  /** Enable batch operations */
  enableBatchOps?: boolean;
  /** Sort by criteria */
  sortBy?: 'time' | 'risk';
  /** Sort order */
  sortOrder?: 'asc' | 'desc';
  /** Filter by risk level */
  filterRisk?: RiskLevel[];
  /** Empty state message */
  emptyMessage?: string;
  /** Additional CSS classes */
  className?: string;
}

/** Risk level priority for sorting */
const riskPriority: Record<RiskLevel, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
};

/**
 * ApprovalList Component
 *
 * Displays and manages multiple pending approval requests.
 */
export const ApprovalList: FC<ApprovalListProps> = ({
  approvals,
  onApprove,
  onReject,
  onShowDetails,
  enableBatchOps = false,
  sortBy = 'time',
  sortOrder = 'desc',
  filterRisk,
  emptyMessage = 'No pending approvals',
  className = '',
}) => {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Filter and sort approvals
  const processedApprovals = useMemo(() => {
    let filtered = [...approvals];

    // Apply risk filter
    if (filterRisk && filterRisk.length > 0) {
      filtered = filtered.filter((a) => filterRisk.includes(a.riskLevel));
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let comparison = 0;

      if (sortBy === 'time') {
        comparison = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
      } else if (sortBy === 'risk') {
        comparison = riskPriority[a.riskLevel] - riskPriority[b.riskLevel];
      }

      return sortOrder === 'desc' ? -comparison : comparison;
    });

    return filtered;
  }, [approvals, filterRisk, sortBy, sortOrder]);

  // Toggle selection
  const toggleSelection = useCallback((approvalId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(approvalId)) {
        next.delete(approvalId);
      } else {
        next.add(approvalId);
      }
      return next;
    });
  }, []);

  // Select all
  const selectAll = useCallback(() => {
    setSelectedIds(new Set(processedApprovals.map((a) => a.approvalId)));
  }, [processedApprovals]);

  // Clear selection
  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  // Batch approve
  const handleBatchApprove = useCallback(() => {
    selectedIds.forEach((id) => onApprove(id));
    setSelectedIds(new Set());
  }, [selectedIds, onApprove]);

  // Batch reject
  const handleBatchReject = useCallback(() => {
    selectedIds.forEach((id) => onReject(id));
    setSelectedIds(new Set());
  }, [selectedIds, onReject]);

  // Empty state
  if (processedApprovals.length === 0) {
    return (
      <div
        className={`flex flex-col items-center justify-center p-8 text-gray-400 ${className}`}
        data-testid="approval-list-empty"
      >
        <div className="text-4xl mb-2">✅</div>
        <div>{emptyMessage}</div>
      </div>
    );
  }

  return (
    <div className={className} data-testid="approval-list">
      {/* Header with batch controls */}
      {enableBatchOps && (
        <div className="flex items-center justify-between mb-4 p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">
              {processedApprovals.length} pending approval{processedApprovals.length > 1 ? 's' : ''}
            </span>
            {selectedIds.size > 0 && (
              <span className="text-sm text-blue-600 font-medium">
                ({selectedIds.size} selected)
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {selectedIds.size === 0 ? (
              <Button
                variant="outline"
                size="sm"
                onClick={selectAll}
                data-testid="select-all"
              >
                Select All
              </Button>
            ) : (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={clearSelection}
                  data-testid="clear-selection"
                >
                  Clear
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleBatchApprove}
                  data-testid="batch-approve"
                >
                  Approve ({selectedIds.size})
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleBatchReject}
                  data-testid="batch-reject"
                >
                  Reject ({selectedIds.size})
                </Button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Approval items */}
      <div className="space-y-3">
        {processedApprovals.map((approval) => (
          <div key={approval.approvalId} className="flex items-start gap-2">
            {enableBatchOps && (
              <input
                type="checkbox"
                checked={selectedIds.has(approval.approvalId)}
                onChange={() => toggleSelection(approval.approvalId)}
                className="mt-4 w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                data-testid={`checkbox-${approval.approvalId}`}
                aria-label={`Select ${approval.toolName} approval`}
              />
            )}
            <div className="flex-1">
              <ApprovalBanner
                approval={approval}
                onApprove={onApprove}
                onReject={onReject}
                onShowDetails={onShowDetails}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ApprovalList;
