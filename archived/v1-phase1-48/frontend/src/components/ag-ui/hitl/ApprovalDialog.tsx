/**
 * ApprovalDialog - Modal Approval Dialog Component
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-3: HITL Approval Components
 *
 * Full-screen modal dialog for tool call approval.
 * Shows complete details including arguments, risk assessment, and timeout.
 */

import { FC, useState, useEffect, useMemo, useCallback } from 'react';
import type { PendingApproval } from '@/types/ag-ui';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import { RiskBadge } from './RiskBadge';

export interface ApprovalDialogProps {
  /** Approval request */
  approval: PendingApproval;
  /** Whether dialog is open */
  isOpen: boolean;
  /** Callback when approved */
  onApprove: (approvalId: string, comment?: string) => void;
  /** Callback when rejected */
  onReject: (approvalId: string, comment?: string) => void;
  /** Callback when dialog is closed */
  onClose: () => void;
  /** Show comment field */
  showComment?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * ApprovalDialog Component
 *
 * Modal dialog for reviewing and acting on tool call approval requests.
 */
export const ApprovalDialog: FC<ApprovalDialogProps> = ({
  approval,
  isOpen,
  onApprove,
  onReject,
  onClose,
  showComment = true,
  className = '',
}) => {
  const [comment, setComment] = useState('');
  const [timeRemaining, setTimeRemaining] = useState<number | null>(null);

  const {
    approvalId,
    toolName,
    arguments: args,
    riskLevel,
    riskScore,
    reasoning,
    expiresAt,
    createdAt,
  } = approval;

  // Format arguments as JSON
  const formattedArgs = useMemo(() => {
    try {
      return JSON.stringify(args, null, 2);
    } catch {
      return String(args);
    }
  }, [args]);

  // Countdown timer
  useEffect(() => {
    if (!expiresAt || !isOpen) {
      setTimeRemaining(null);
      return;
    }

    const updateTimer = () => {
      const expires = new Date(expiresAt).getTime();
      const now = Date.now();
      const diff = Math.max(0, Math.floor((expires - now) / 1000));
      setTimeRemaining(diff);

      if (diff <= 0) {
        onClose();
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);

    return () => clearInterval(interval);
  }, [expiresAt, isOpen, onClose]);

  // Format time remaining
  const formattedTime = useMemo(() => {
    if (timeRemaining === null) return null;
    const minutes = Math.floor(timeRemaining / 60);
    const seconds = timeRemaining % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }, [timeRemaining]);

  // Handle approve
  const handleApprove = useCallback(() => {
    onApprove(approvalId, comment.trim() || undefined);
    setComment('');
  }, [approvalId, comment, onApprove]);

  // Handle reject
  const handleReject = useCallback(() => {
    onReject(approvalId, comment.trim() || undefined);
    setComment('');
  }, [approvalId, comment, onReject]);

  // Handle backdrop click
  const handleBackdropClick = useCallback((e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  }, [onClose]);

  if (!isOpen) return null;

  // Urgency styling based on time remaining
  const timerClass = timeRemaining !== null && timeRemaining < 30
    ? 'text-red-600 animate-pulse'
    : 'text-gray-600';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={handleBackdropClick}
      data-testid={`approval-dialog-${approvalId}`}
      role="dialog"
      aria-modal="true"
      aria-labelledby="approval-dialog-title"
    >
      <div className={`bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden ${className}`}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b bg-gray-50">
          <div>
            <h2 id="approval-dialog-title" className="text-lg font-semibold text-gray-900">
              Tool Approval Required
            </h2>
            <p className="text-sm text-gray-500">
              Review and approve this tool call before execution
            </p>
          </div>
          {formattedTime && (
            <div className={`text-lg font-mono font-bold ${timerClass}`}>
              ⏱️ {formattedTime}
            </div>
          )}
        </div>

        {/* Content */}
        <div className="p-6 space-y-4 overflow-y-auto max-h-[60vh]">
          {/* Tool Info */}
          <div>
            <div className="text-sm font-medium text-gray-500 mb-1">Tool Name</div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-lg text-purple-600">{toolName}</span>
              <RiskBadge level={riskLevel} score={riskScore} showScore />
            </div>
          </div>

          {/* Arguments */}
          <div>
            <div className="text-sm font-medium text-gray-500 mb-1">Arguments</div>
            <pre className="p-3 bg-gray-50 rounded-lg text-sm font-mono overflow-x-auto max-h-40">
              {formattedArgs}
            </pre>
          </div>

          {/* Risk Assessment */}
          <div>
            <div className="text-sm font-medium text-gray-500 mb-1">Risk Assessment</div>
            <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-200">
              <p className="text-sm text-yellow-800">{reasoning || 'No risk assessment provided.'}</p>
            </div>
          </div>

          {/* Timestamps */}
          <div className="flex gap-4 text-sm text-gray-500">
            {createdAt && (
              <div>
                <span className="font-medium">Requested:</span>{' '}
                {new Date(createdAt).toLocaleTimeString('zh-TW')}
              </div>
            )}
            {expiresAt && (
              <div>
                <span className="font-medium">Expires:</span>{' '}
                {new Date(expiresAt).toLocaleTimeString('zh-TW')}
              </div>
            )}
          </div>

          {/* Comment Field */}
          {showComment && (
            <div>
              <div className="text-sm font-medium text-gray-500 mb-1">Comment (Optional)</div>
              <Textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Add a comment for audit log..."
                className="resize-none"
                rows={2}
                data-testid="approval-comment"
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t bg-gray-50">
          <Button
            variant="outline"
            onClick={onClose}
            data-testid="cancel-approval"
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleReject}
            data-testid={`reject-${approvalId}`}
          >
            Reject
          </Button>
          <Button
            variant="default"
            onClick={handleApprove}
            data-testid={`approve-${approvalId}`}
          >
            Approve
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ApprovalDialog;
