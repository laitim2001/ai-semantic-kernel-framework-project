/**
 * InlineApproval - Inline Tool Call Approval Component
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * S62-3: ChatArea Component
 * Phase 16: Unified Agentic Chat Interface
 *
 * Displays inline approval buttons for low/medium risk tool calls.
 * High/critical risk tool calls should use ApprovalDialog instead.
 */

import { FC, useState, useCallback } from 'react';
import { Check, X, AlertTriangle, Shield } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import type { InlineApprovalProps } from '@/types/unified-chat';
import { cn } from '@/lib/utils';

/**
 * Get risk level display config
 */
const getRiskConfig = (level: string) => {
  switch (level) {
    case 'low':
      return {
        icon: Shield,
        label: 'Low Risk',
        variant: 'default' as const,
        className: 'text-green-600 bg-green-50 border-green-200',
      };
    case 'medium':
      return {
        icon: AlertTriangle,
        label: 'Medium Risk',
        variant: 'secondary' as const,
        className: 'text-yellow-600 bg-yellow-50 border-yellow-200',
      };
    default:
      return {
        icon: Shield,
        label: level,
        variant: 'secondary' as const,
        className: 'text-gray-600 bg-gray-50 border-gray-200',
      };
  }
};

/**
 * InlineApproval Component
 *
 * Compact inline approval UI for tool calls within the message flow.
 * Shows tool name, risk level badge, and approve/reject buttons.
 */
export const InlineApproval: FC<InlineApprovalProps> = ({
  approval,
  onApprove,
  onReject,
  compact = false,
}) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [showRejectInput, setShowRejectInput] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  const riskConfig = getRiskConfig(approval.riskLevel);
  const RiskIcon = riskConfig.icon;

  // Handle approve
  const handleApprove = useCallback(async () => {
    setIsProcessing(true);
    try {
      await onApprove();
    } finally {
      setIsProcessing(false);
    }
  }, [onApprove]);

  // Handle reject
  const handleReject = useCallback(async () => {
    setIsProcessing(true);
    try {
      await onReject(rejectReason || undefined);
    } finally {
      setIsProcessing(false);
      setShowRejectInput(false);
      setRejectReason('');
    }
  }, [onReject, rejectReason]);

  // Toggle reject input
  const toggleRejectInput = useCallback(() => {
    setShowRejectInput((prev) => !prev);
    if (!showRejectInput) {
      setRejectReason('');
    }
  }, [showRejectInput]);

  if (compact) {
    // Compact mode: just buttons
    return (
      <div
        className="inline-flex items-center gap-2"
        data-testid="inline-approval-compact"
      >
        <Badge variant={riskConfig.variant} className="text-xs">
          {approval.toolName}
        </Badge>
        <Button
          variant="default"
          size="sm"
          className="h-6 px-2 text-xs"
          onClick={handleApprove}
          disabled={isProcessing}
        >
          <Check className="h-3 w-3" />
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="h-6 px-2 text-xs"
          onClick={() => onReject()}
          disabled={isProcessing}
        >
          <X className="h-3 w-3" />
        </Button>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'rounded-lg border p-3',
        riskConfig.className
      )}
      data-testid="inline-approval"
      data-approval-id={approval.approvalId}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <RiskIcon className="h-4 w-4" />
          <span className="text-sm font-medium">{approval.toolName}</span>
          <Badge variant={riskConfig.variant} className="text-xs">
            {riskConfig.label}
          </Badge>
        </div>

        {/* Action Buttons */}
        {!showRejectInput && (
          <div className="flex items-center gap-2">
            <Button
              variant="default"
              size="sm"
              className="h-7 gap-1"
              onClick={handleApprove}
              disabled={isProcessing}
            >
              <Check className="h-3.5 w-3.5" />
              Approve
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 gap-1"
              onClick={toggleRejectInput}
              disabled={isProcessing}
            >
              <X className="h-3.5 w-3.5" />
              Reject
            </Button>
          </div>
        )}
      </div>

      {/* Reasoning */}
      {approval.reasoning && (
        <p className="mt-2 text-xs text-gray-600">{approval.reasoning}</p>
      )}

      {/* Arguments Preview */}
      {Object.keys(approval.arguments).length > 0 && (
        <div className="mt-2">
          <div className="text-xs text-gray-500 mb-1">Arguments:</div>
          <pre className="text-xs bg-white/50 rounded p-2 overflow-x-auto">
            {JSON.stringify(approval.arguments, null, 2)}
          </pre>
        </div>
      )}

      {/* Reject Input */}
      {showRejectInput && (
        <div className="mt-3 space-y-2">
          <input
            type="text"
            placeholder="Reason for rejection (optional)"
            className="w-full px-3 py-2 text-sm border rounded-md bg-white"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleReject();
              } else if (e.key === 'Escape') {
                toggleRejectInput();
              }
            }}
            autoFocus
          />
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleRejectInput}
              disabled={isProcessing}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleReject}
              disabled={isProcessing}
            >
              Confirm Reject
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default InlineApproval;
