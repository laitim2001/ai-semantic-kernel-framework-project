/**
 * ApprovalMessageCard - Inline Approval as AI Message
 *
 * Sprint 99: HITL UX Improvement
 * Phase 28: Hybrid Orchestrator Integration
 *
 * Displays tool call approval as an AI message in the chat flow.
 * This provides a more natural conversation experience compared to modal dialogs.
 *
 * Features:
 * - Looks like an AI response with avatar
 * - Shows tool name, arguments, and risk level
 * - Approve/Reject buttons inline
 * - Countdown timer for expiry
 * - Risk-based styling (green/yellow/orange/red)
 * - Shows resolved status (approved/rejected/expired) with history
 */

import { FC, useState, useEffect, useCallback } from 'react';
import {
  AlertTriangle,
  AlertOctagon,
  Shield,
  Clock,
  Check,
  X,
  Terminal,
  Bot,
  Loader2,
  CheckCircle2,
  XCircle,
  Timer,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/utils';
import type { PendingApproval, RiskLevel, ApprovalStatus } from '@/types/ag-ui';

// =============================================================================
// Types
// =============================================================================

export interface ApprovalMessageCardProps {
  /** The pending approval to display */
  approval: PendingApproval;
  /** Callback when user approves */
  onApprove: () => void;
  /** Callback when user rejects (with optional reason) */
  onReject: (reason?: string) => void;
  /** Callback when approval expires - used to clean up and allow new approvals */
  onExpired?: () => void;
  /** Whether an action is being processed */
  isProcessing?: boolean;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Calculate remaining time until expiry
 */
const calculateTimeRemaining = (expiresAt: string): number => {
  return Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000));
};

/**
 * Format seconds as mm:ss
 */
const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

/**
 * Get risk level configuration
 */
const getRiskConfig = (level: RiskLevel) => {
  const configs = {
    low: {
      icon: Shield,
      label: 'Low Risk',
      bgClass: 'bg-green-50 dark:bg-green-900/20',
      borderClass: 'border-green-200 dark:border-green-800',
      textClass: 'text-green-700 dark:text-green-300',
      badgeClass: 'bg-green-100 text-green-700 dark:bg-green-800 dark:text-green-300',
    },
    medium: {
      icon: AlertTriangle,
      label: 'Medium Risk',
      bgClass: 'bg-yellow-50 dark:bg-yellow-900/20',
      borderClass: 'border-yellow-200 dark:border-yellow-800',
      textClass: 'text-yellow-700 dark:text-yellow-300',
      badgeClass: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-800 dark:text-yellow-300',
    },
    high: {
      icon: AlertOctagon,
      label: 'High Risk',
      bgClass: 'bg-orange-50 dark:bg-orange-900/20',
      borderClass: 'border-orange-200 dark:border-orange-800',
      textClass: 'text-orange-700 dark:text-orange-300',
      badgeClass: 'bg-orange-100 text-orange-700 dark:bg-orange-800 dark:text-orange-300',
    },
    critical: {
      icon: AlertOctagon,
      label: 'Critical Risk',
      bgClass: 'bg-red-50 dark:bg-red-900/20',
      borderClass: 'border-red-200 dark:border-red-800',
      textClass: 'text-red-700 dark:text-red-300',
      badgeClass: 'bg-red-100 text-red-700 dark:bg-red-800 dark:text-red-300',
    },
  };
  return configs[level] || configs.medium;
};

/**
 * Get status display configuration
 */
const getStatusConfig = (status: ApprovalStatus) => {
  const configs = {
    pending: {
      icon: Clock,
      label: 'Pending',
      bgClass: 'bg-blue-50 dark:bg-blue-900/20',
      borderClass: 'border-blue-200 dark:border-blue-800',
      textClass: 'text-blue-700 dark:text-blue-300',
    },
    approved: {
      icon: CheckCircle2,
      label: 'Approved',
      bgClass: 'bg-green-50 dark:bg-green-900/20',
      borderClass: 'border-green-300 dark:border-green-700',
      textClass: 'text-green-700 dark:text-green-300',
    },
    rejected: {
      icon: XCircle,
      label: 'Rejected',
      bgClass: 'bg-red-50 dark:bg-red-900/20',
      borderClass: 'border-red-300 dark:border-red-700',
      textClass: 'text-red-700 dark:text-red-300',
    },
    expired: {
      icon: Timer,
      label: 'Expired',
      bgClass: 'bg-gray-50 dark:bg-gray-900/20',
      borderClass: 'border-gray-300 dark:border-gray-700',
      textClass: 'text-gray-500 dark:text-gray-400',
    },
  };
  return configs[status] || configs.pending;
};

// =============================================================================
// Sub-Components
// =============================================================================

interface TimeoutCountdownProps {
  expiresAt: string;
  onExpired?: () => void;
}

const TimeoutCountdown: FC<TimeoutCountdownProps> = ({ expiresAt, onExpired }) => {
  const [remaining, setRemaining] = useState(() => calculateTimeRemaining(expiresAt));

  useEffect(() => {
    const interval = setInterval(() => {
      const newRemaining = calculateTimeRemaining(expiresAt);
      setRemaining(newRemaining);
      if (newRemaining === 0) {
        onExpired?.();
        clearInterval(interval);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [expiresAt, onExpired]);

  if (remaining <= 0) {
    return (
      <Badge variant="destructive" className="animate-pulse text-xs">
        <Clock className="h-3 w-3 mr-1" />
        Expired
      </Badge>
    );
  }

  const isUrgent = remaining < 30;

  return (
    <Badge
      variant={isUrgent ? 'destructive' : 'outline'}
      className={cn('text-xs', isUrgent && 'animate-pulse')}
    >
      <Clock className="h-3 w-3 mr-1" />
      {formatTime(remaining)}
    </Badge>
  );
};

// =============================================================================
// Resolved Status Component
// =============================================================================

interface ResolvedStatusProps {
  status: ApprovalStatus;
  resolvedAt?: string;
  rejectReason?: string;
}

const ResolvedStatus: FC<ResolvedStatusProps> = ({ status, resolvedAt, rejectReason }) => {
  const config = getStatusConfig(status);
  const StatusIcon = config.icon;

  return (
    <div className={cn(
      'flex items-center gap-2 px-3 py-2 rounded-lg',
      config.bgClass,
      'border',
      config.borderClass
    )}>
      <StatusIcon className={cn('h-5 w-5', config.textClass)} />
      <div className="flex-1">
        <span className={cn('font-medium', config.textClass)}>
          {config.label}
        </span>
        {resolvedAt && (
          <span className="text-xs text-gray-500 ml-2">
            at {new Date(resolvedAt).toLocaleTimeString()}
          </span>
        )}
        {rejectReason && (
          <p className="text-xs text-gray-600 mt-1">
            Reason: {rejectReason}
          </p>
        )}
      </div>
    </div>
  );
};

// =============================================================================
// Main Component
// =============================================================================

/**
 * ApprovalMessageCard Component
 *
 * Renders a tool call approval request as an AI message in the chat flow.
 * Shows different UI based on status: pending (with buttons) or resolved (with history).
 */
export const ApprovalMessageCard: FC<ApprovalMessageCardProps> = ({
  approval,
  onApprove,
  onReject,
  onExpired,
  isProcessing = false,
}) => {
  const [localExpired, setLocalExpired] = useState(false);
  const [showRejectInput, setShowRejectInput] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [localProcessing, setLocalProcessing] = useState(false);

  // Determine effective status
  const effectiveStatus: ApprovalStatus = approval.status || (localExpired ? 'expired' : 'pending');
  const isResolved = effectiveStatus !== 'pending';
  const isPending = effectiveStatus === 'pending';

  const riskConfig = getRiskConfig(approval.riskLevel);
  const RiskIcon = riskConfig.icon;

  // Handle approve
  const handleApprove = useCallback(async () => {
    if (isResolved || isProcessing || localProcessing) return;
    setLocalProcessing(true);
    try {
      await onApprove();
    } finally {
      setLocalProcessing(false);
    }
  }, [isResolved, isProcessing, localProcessing, onApprove]);

  // Handle reject
  const handleReject = useCallback(async () => {
    if (isProcessing || localProcessing) return;
    setLocalProcessing(true);
    try {
      await onReject(rejectReason || undefined);
    } finally {
      setLocalProcessing(false);
      setShowRejectInput(false);
      setRejectReason('');
    }
  }, [isProcessing, localProcessing, onReject, rejectReason]);

  // Handle expiry
  const handleExpired = useCallback(() => {
    setLocalExpired(true);
    // Notify parent to remove this approval after a delay (allows user to see it expired)
    setTimeout(() => {
      onExpired?.();
    }, 3000); // Remove after 3 seconds
  }, [onExpired]);

  const processing = isProcessing || localProcessing;

  // Use resolved styling for non-pending states
  const cardBgClass = isResolved
    ? getStatusConfig(effectiveStatus).bgClass
    : riskConfig.bgClass;
  const cardBorderClass = isResolved
    ? getStatusConfig(effectiveStatus).borderClass
    : riskConfig.borderClass;

  return (
    <div className="flex gap-3 py-2 px-4" data-testid="approval-message-card">
      {/* AI Avatar */}
      <div className="flex-shrink-0">
        <div className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center',
          isResolved ? getStatusConfig(effectiveStatus).bgClass : riskConfig.bgClass,
          isResolved ? getStatusConfig(effectiveStatus).borderClass : riskConfig.borderClass,
          'border'
        )}>
          {isResolved ? (
            (() => {
              const StatusIcon = getStatusConfig(effectiveStatus).icon;
              return <StatusIcon className={cn('h-4 w-4', getStatusConfig(effectiveStatus).textClass)} />;
            })()
          ) : (
            <Bot className={cn('h-4 w-4', riskConfig.textClass)} />
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {isResolved ? `Tool Call ${effectiveStatus.charAt(0).toUpperCase() + effectiveStatus.slice(1)}` : 'Approval Required'}
          </span>
          {isPending && !localExpired && (
            <TimeoutCountdown expiresAt={approval.expiresAt} onExpired={handleExpired} />
          )}
          {isResolved && (
            <Badge className={getStatusConfig(effectiveStatus).textClass + ' ' + getStatusConfig(effectiveStatus).bgClass}>
              {getStatusConfig(effectiveStatus).label}
            </Badge>
          )}
        </div>

        {/* Approval Card */}
        <div className={cn(
          'rounded-lg border p-4 max-w-xl',
          cardBgClass,
          cardBorderClass,
          isResolved && 'opacity-90'
        )}>
          {/* Tool Info Row */}
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
              <Terminal className="h-4 w-4 text-gray-600 dark:text-gray-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-gray-900 dark:text-gray-100 truncate">
                {approval.toolName}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Tool Call
              </p>
            </div>
            <Badge className={riskConfig.badgeClass}>
              <RiskIcon className="h-3 w-3 mr-1" />
              {riskConfig.label}
            </Badge>
          </div>

          {/* Reasoning */}
          {approval.reasoning && (
            <p className="text-sm text-gray-600 dark:text-gray-300 mb-3">
              {approval.reasoning}
            </p>
          )}

          {/* Arguments Preview - collapsed for resolved */}
          {Object.keys(approval.arguments).length > 0 && (
            <details className="mb-3" open={isPending}>
              <summary className="text-xs text-gray-500 dark:text-gray-400 mb-1 font-medium cursor-pointer">
                Arguments {isResolved && '(click to expand)'}
              </summary>
              <pre className="text-xs bg-white/70 dark:bg-gray-800/70 rounded-lg p-3 overflow-x-auto max-h-32 border border-gray-200 dark:border-gray-700">
                {JSON.stringify(approval.arguments, null, 2)}
              </pre>
            </details>
          )}

          {/* Resolved Status Display */}
          {isResolved && (
            <ResolvedStatus
              status={effectiveStatus}
              resolvedAt={approval.resolvedAt}
              rejectReason={approval.rejectReason}
            />
          )}

          {/* Reject Reason Input (only for pending) */}
          {isPending && showRejectInput && !localExpired && (
            <div className="mb-4 space-y-2">
              <input
                type="text"
                placeholder="Reason for rejection (optional)"
                className="w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 focus:ring-2 focus:ring-primary/50 focus:border-primary"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleReject();
                  } else if (e.key === 'Escape') {
                    setShowRejectInput(false);
                    setRejectReason('');
                  }
                }}
                autoFocus
                disabled={processing}
              />
              <div className="flex justify-end gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setShowRejectInput(false);
                    setRejectReason('');
                  }}
                  disabled={processing}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleReject}
                  disabled={processing}
                >
                  {processing ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-1" />
                  ) : (
                    <X className="h-4 w-4 mr-1" />
                  )}
                  Confirm Reject
                </Button>
              </div>
            </div>
          )}

          {/* Action Buttons (only for pending) */}
          {isPending && !showRejectInput && !localExpired && (
            <div className="flex items-center gap-2">
              <Button
                onClick={handleApprove}
                disabled={processing}
                className="flex-1 gap-2"
                size="sm"
              >
                {processing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Check className="h-4 w-4" />
                )}
                Approve
              </Button>
              <Button
                variant="outline"
                onClick={() => setShowRejectInput(true)}
                disabled={processing}
                className="flex-1 gap-2"
                size="sm"
              >
                <X className="h-4 w-4" />
                Reject
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ApprovalMessageCard;
