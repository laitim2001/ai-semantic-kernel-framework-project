/**
 * ApprovalBanner - Inline Approval Prompt Component
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-3: HITL Approval Components
 *
 * Non-modal inline banner for approval requests.
 * Compact display with quick action buttons.
 */

import { FC, useMemo } from 'react';
import type { PendingApproval } from '@/types/ag-ui';
import { Button } from '@/components/ui/Button';
import { RiskBadge } from './RiskBadge';

export interface ApprovalBannerProps {
  /** Approval request */
  approval: PendingApproval;
  /** Callback when approved */
  onApprove: (approvalId: string) => void;
  /** Callback when rejected */
  onReject: (approvalId: string) => void;
  /** Callback for more details */
  onShowDetails?: (approval: PendingApproval) => void;
  /** Compact mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * ApprovalBanner Component
 *
 * Inline banner showing approval request with quick actions.
 */
export const ApprovalBanner: FC<ApprovalBannerProps> = ({
  approval,
  onApprove,
  onReject,
  onShowDetails,
  compact = false,
  className = '',
}) => {
  const { approvalId, toolName, riskLevel, riskScore, expiresAt, reasoning } = approval;

  // Time remaining calculation
  const timeRemaining = useMemo(() => {
    if (!expiresAt) return null;
    try {
      const expires = new Date(expiresAt).getTime();
      const now = Date.now();
      const diff = expires - now;

      if (diff <= 0) return 'Expired';

      const minutes = Math.floor(diff / 60000);
      const seconds = Math.floor((diff % 60000) / 1000);

      if (minutes > 0) return `${minutes}m ${seconds}s`;
      return `${seconds}s`;
    } catch {
      return null;
    }
  }, [expiresAt]);

  // Background color based on risk
  const bgColorClass = useMemo(() => {
    switch (riskLevel) {
      case 'critical': return 'bg-red-50 border-red-200';
      case 'high': return 'bg-orange-50 border-orange-200';
      case 'medium': return 'bg-yellow-50 border-yellow-200';
      default: return 'bg-blue-50 border-blue-200';
    }
  }, [riskLevel]);

  return (
    <div
      className={`flex items-center gap-3 p-3 rounded-lg border ${bgColorClass} ${className}`}
      data-testid={`approval-banner-${approvalId}`}
      role="alert"
      aria-label={`Approval required for ${toolName}`}
    >
      {/* Icon */}
      <div className="text-2xl" aria-hidden="true">
        🛡️
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-gray-900">Approval Required:</span>
          <span className="font-mono text-purple-600">{toolName}</span>
          <RiskBadge level={riskLevel} score={riskScore} size="sm" />
        </div>

        {!compact && reasoning && (
          <p className="text-sm text-gray-600 mt-1 line-clamp-2">{reasoning}</p>
        )}
      </div>

      {/* Time Remaining */}
      {timeRemaining && (
        <div className="text-sm text-gray-500 whitespace-nowrap">
          ⏱️ {timeRemaining}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2">
        {onShowDetails && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => onShowDetails(approval)}
            data-testid={`details-${approvalId}`}
          >
            Details
          </Button>
        )}
        <Button
          variant="default"
          size="sm"
          onClick={() => onApprove(approvalId)}
          data-testid={`approve-${approvalId}`}
        >
          Approve
        </Button>
        <Button
          variant="destructive"
          size="sm"
          onClick={() => onReject(approvalId)}
          data-testid={`reject-${approvalId}`}
        >
          Reject
        </Button>
      </div>
    </div>
  );
};

export default ApprovalBanner;
