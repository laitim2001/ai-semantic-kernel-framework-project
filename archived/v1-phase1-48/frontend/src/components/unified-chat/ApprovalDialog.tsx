/**
 * ApprovalDialog - High Risk Tool Call Approval Dialog
 *
 * Sprint 64: Approval Flow & Risk Indicators
 * S64-2: ApprovalDialog Component
 * Phase 16: Unified Agentic Chat Interface
 *
 * Modal dialog for high-risk and critical approval requests.
 * Shows detailed risk information, tool arguments, and countdown timer.
 */

import { FC, useState, useEffect, useCallback } from 'react';
import {
  AlertTriangle,
  Clock,
  X,
  Check,
  Terminal,
  AlertOctagon,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Textarea } from '@/components/ui/Textarea';
import { cn } from '@/lib/utils';
import { RiskIndicator } from './RiskIndicator';
import type { PendingApproval, RiskLevel } from '@/types/ag-ui';

// =============================================================================
// Types
// =============================================================================

export interface ApprovalDialogProps {
  /** The pending approval to display */
  approval: PendingApproval;
  /** Callback when user approves */
  onApprove: () => void;
  /** Callback when user rejects (with optional reason) */
  onReject: (reason?: string) => void;
  /** Callback when dialog is dismissed */
  onDismiss: () => void;
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
 * Get risk level styling
 */
const getRiskStyling = (level: RiskLevel) => {
  const styles = {
    low: {
      border: 'border-green-300',
      bg: 'bg-green-50',
      headerBg: 'bg-green-100',
      icon: AlertTriangle,
    },
    medium: {
      border: 'border-yellow-300',
      bg: 'bg-yellow-50',
      headerBg: 'bg-yellow-100',
      icon: AlertTriangle,
    },
    high: {
      border: 'border-orange-300',
      bg: 'bg-orange-50',
      headerBg: 'bg-orange-100',
      icon: AlertOctagon,
    },
    critical: {
      border: 'border-red-300',
      bg: 'bg-red-50',
      headerBg: 'bg-red-100',
      icon: AlertOctagon,
    },
  };
  return styles[level];
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
      <Badge variant="destructive" className="animate-pulse">
        <Clock className="h-3 w-3 mr-1" />
        Expired
      </Badge>
    );
  }

  const isUrgent = remaining < 30;

  return (
    <Badge
      variant={isUrgent ? 'destructive' : 'outline'}
      className={cn(isUrgent && 'animate-pulse')}
    >
      <Clock className="h-3 w-3 mr-1" />
      {formatTime(remaining)}
    </Badge>
  );
};

// =============================================================================
// Main Component
// =============================================================================

/**
 * ApprovalDialog Component
 *
 * Shows a modal dialog for high-risk and critical tool call approvals.
 * Includes risk visualization, tool arguments, countdown timer, and
 * optional rejection reason input.
 *
 * @example
 * ```tsx
 * <ApprovalDialog
 *   approval={pendingApproval}
 *   onApprove={() => approve(pendingApproval.toolCallId)}
 *   onReject={(reason) => reject(pendingApproval.toolCallId, reason)}
 *   onDismiss={dismissDialog}
 *   isProcessing={isProcessing}
 * />
 * ```
 */
export const ApprovalDialog: FC<ApprovalDialogProps> = ({
  approval,
  onApprove,
  onReject,
  onDismiss,
  isProcessing = false,
}) => {
  const [showRejectInput, setShowRejectInput] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [isExpired, setIsExpired] = useState(false);

  const riskStyle = getRiskStyling(approval.riskLevel);

  // Extract risk factors from reasoning (simplified parsing)
  const riskFactors = approval.reasoning
    ? approval.reasoning
        .split(/[;,.]/)
        .map((s) => s.trim())
        .filter((s) => s.length > 0)
        .slice(0, 5)
    : [];

  // Handle approve
  const handleApprove = useCallback(() => {
    if (!isExpired && !isProcessing) {
      onApprove();
    }
  }, [isExpired, isProcessing, onApprove]);

  // Handle reject
  const handleReject = useCallback(() => {
    if (!isProcessing) {
      onReject(rejectReason || undefined);
      setShowRejectInput(false);
      setRejectReason('');
    }
  }, [isProcessing, onReject, rejectReason]);

  // Toggle reject input
  const toggleRejectInput = useCallback(() => {
    setShowRejectInput((prev) => !prev);
    if (!showRejectInput) {
      setRejectReason('');
    }
  }, [showRejectInput]);

  // Handle timeout expiry
  const handleExpired = useCallback(() => {
    setIsExpired(true);
  }, []);

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && showRejectInput && rejectReason) {
        handleReject();
      } else if (e.key === 'Escape') {
        if (showRejectInput) {
          toggleRejectInput();
        } else {
          onDismiss();
        }
      }
    },
    [handleReject, onDismiss, rejectReason, showRejectInput, toggleRejectInput]
  );

  return (
    <Dialog open={true} onOpenChange={(open: boolean) => !open && onDismiss()}>
      <DialogContent
        className={cn('sm:max-w-lg', riskStyle.border)}
        onKeyDown={handleKeyDown}
      >
        <DialogHeader className={cn('rounded-t-lg -mx-6 -mt-6 px-6 pt-6 pb-4', riskStyle.headerBg)}>
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Tool Approval Required
            </DialogTitle>
            <TimeoutCountdown
              expiresAt={approval.expiresAt}
              onExpired={handleExpired}
            />
          </div>
          <DialogDescription>
            This operation requires your explicit approval before execution.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Tool Info */}
          <div className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg">
            <div className="p-2 bg-background rounded-md">
              <Terminal className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{approval.toolName}</p>
              <p className="text-sm text-muted-foreground">Tool Call</p>
            </div>
            <RiskIndicator
              level={approval.riskLevel}
              score={approval.riskScore}
              factors={riskFactors}
              reasoning={approval.reasoning}
              size="md"
              showScore
            />
          </div>

          {/* Arguments */}
          {Object.keys(approval.arguments).length > 0 && (
            <div>
              <p className="text-sm font-medium mb-2">Arguments:</p>
              <pre className="text-xs bg-muted p-3 rounded-lg overflow-x-auto max-h-40">
                {JSON.stringify(approval.arguments, null, 2)}
              </pre>
            </div>
          )}

          {/* Risk Factors */}
          {riskFactors.length > 0 && (
            <div className={cn('p-3 rounded-lg border', riskStyle.border, riskStyle.bg)}>
              <p className="text-sm font-medium mb-2 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                Risk Assessment
              </p>
              <ul className="text-sm space-y-1">
                {riskFactors.map((factor, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-muted-foreground">•</span>
                    <span>{factor}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Expired Warning */}
          {isExpired && (
            <div className="p-3 bg-red-100 border border-red-300 rounded-lg">
              <p className="text-sm text-red-800 font-medium">
                This approval request has expired. Please dismiss this dialog.
              </p>
            </div>
          )}

          {/* Reject Reason Input */}
          {showRejectInput && !isExpired && (
            <div className="space-y-2">
              <p className="text-sm font-medium">Rejection Reason (optional):</p>
              <Textarea
                placeholder="Explain why you're rejecting this operation..."
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                className="resize-none"
                rows={3}
                autoFocus
              />
            </div>
          )}
        </div>

        <DialogFooter className="flex gap-2 sm:gap-2">
          {!showRejectInput ? (
            <>
              <Button
                variant="outline"
                onClick={toggleRejectInput}
                disabled={isProcessing || isExpired}
                className="flex-1 sm:flex-none"
              >
                <X className="h-4 w-4 mr-2" />
                Reject
              </Button>
              <Button
                onClick={handleApprove}
                disabled={isProcessing || isExpired}
                className="flex-1 sm:flex-none"
              >
                <Check className="h-4 w-4 mr-2" />
                Approve
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="ghost"
                onClick={toggleRejectInput}
                disabled={isProcessing}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleReject}
                disabled={isProcessing}
              >
                <X className="h-4 w-4 mr-2" />
                Confirm Reject
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ApprovalDialog;
