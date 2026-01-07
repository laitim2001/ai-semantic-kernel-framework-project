/**
 * ModeSwitchConfirmDialog - Mode Switch Confirmation Dialog
 *
 * Sprint 64: Approval Flow & Risk Indicators
 * S64-1: useApprovalFlow Hook (Mode Switch Confirmation)
 * Phase 16: Unified Agentic Chat Interface
 *
 * Dialog component for confirming automatic mode switches.
 * Shows when a mode switch has lower confidence or is complex.
 */

import { FC } from 'react';
import {
  MessageSquare,
  GitBranch,
  ArrowRight,
  AlertCircle,
  Check,
  X,
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
import { Progress } from '@/components/ui/Progress';
import { cn } from '@/lib/utils';
import type { ExecutionMode } from '@/types/unified-chat';

// =============================================================================
// Types
// =============================================================================

export interface ModeSwitchConfirmDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Source mode */
  from: ExecutionMode;
  /** Target mode */
  to: ExecutionMode;
  /** Reason for the switch */
  reason: string;
  /** Confidence level (0-1) */
  confidence: number;
  /** Callback when user confirms */
  onConfirm: () => void;
  /** Callback when user cancels */
  onCancel: () => void;
  /** Whether action is processing */
  isProcessing?: boolean;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get mode display configuration
 */
const getModeConfig = (mode: ExecutionMode) => {
  if (mode === 'chat') {
    return {
      icon: MessageSquare,
      label: 'Chat Mode',
      description: 'Conversational interaction',
      className: 'text-blue-500 bg-blue-50 border-blue-200',
    };
  }
  return {
    icon: GitBranch,
    label: 'Workflow Mode',
    description: 'Multi-step structured execution',
    className: 'text-purple-500 bg-purple-50 border-purple-200',
  };
};

/**
 * Get confidence level display
 */
const getConfidenceDisplay = (confidence: number) => {
  const percent = Math.round(confidence * 100);
  if (percent >= 90) {
    return { label: 'Very High', className: 'text-green-600' };
  }
  if (percent >= 70) {
    return { label: 'High', className: 'text-green-500' };
  }
  if (percent >= 50) {
    return { label: 'Medium', className: 'text-yellow-600' };
  }
  return { label: 'Low', className: 'text-red-500' };
};

// =============================================================================
// Component
// =============================================================================

/**
 * ModeSwitchConfirmDialog Component
 *
 * Shows a confirmation dialog when the system wants to switch
 * execution modes but needs user confirmation.
 *
 * @example
 * ```tsx
 * <ModeSwitchConfirmDialog
 *   open={!!modeSwitchPending}
 *   from="chat"
 *   to="workflow"
 *   reason="Complex multi-step task detected"
 *   confidence={0.75}
 *   onConfirm={confirmModeSwitch}
 *   onCancel={cancelModeSwitch}
 * />
 * ```
 */
export const ModeSwitchConfirmDialog: FC<ModeSwitchConfirmDialogProps> = ({
  open,
  from,
  to,
  reason,
  confidence,
  onConfirm,
  onCancel,
  isProcessing = false,
}) => {
  const fromConfig = getModeConfig(from);
  const toConfig = getModeConfig(to);
  const confidenceDisplay = getConfidenceDisplay(confidence);
  const confidencePercent = Math.round(confidence * 100);

  const FromIcon = fromConfig.icon;
  const ToIcon = toConfig.icon;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onCancel()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-yellow-500" />
            Mode Switch Request
          </DialogTitle>
          <DialogDescription>
            The system detected a change that may require switching execution modes.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Mode Transition Visual */}
          <div className="flex items-center justify-center gap-4">
            {/* From Mode */}
            <div
              className={cn(
                'flex flex-col items-center gap-2 p-4 rounded-lg border',
                fromConfig.className
              )}
            >
              <FromIcon className="h-8 w-8" />
              <span className="text-sm font-medium">{fromConfig.label}</span>
            </div>

            {/* Arrow */}
            <ArrowRight className="h-6 w-6 text-muted-foreground" />

            {/* To Mode */}
            <div
              className={cn(
                'flex flex-col items-center gap-2 p-4 rounded-lg border',
                toConfig.className
              )}
            >
              <ToIcon className="h-8 w-8" />
              <span className="text-sm font-medium">{toConfig.label}</span>
            </div>
          </div>

          {/* Reason */}
          <div className="bg-muted/50 rounded-lg p-3">
            <p className="text-sm font-medium text-muted-foreground mb-1">
              Reason for switch:
            </p>
            <p className="text-sm">{reason}</p>
          </div>

          {/* Confidence */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Detection Confidence:</span>
              <Badge variant="outline" className={confidenceDisplay.className}>
                {confidenceDisplay.label} ({confidencePercent}%)
              </Badge>
            </div>
            <Progress
              value={confidencePercent}
              className="h-2"
            />
          </div>

          {/* Warning for lower confidence */}
          {confidence < 0.7 && (
            <div className="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <AlertCircle className="h-4 w-4 text-yellow-600 mt-0.5 shrink-0" />
              <p className="text-sm text-yellow-800">
                The confidence level is below 70%. You may want to review this
                switch carefully before confirming.
              </p>
            </div>
          )}
        </div>

        <DialogFooter className="flex gap-2 sm:gap-2">
          <Button
            variant="outline"
            onClick={onCancel}
            disabled={isProcessing}
            className="flex-1 sm:flex-none"
          >
            <X className="h-4 w-4 mr-2" />
            Stay in {fromConfig.label}
          </Button>
          <Button
            onClick={onConfirm}
            disabled={isProcessing}
            className="flex-1 sm:flex-none"
          >
            <Check className="h-4 w-4 mr-2" />
            Switch to {toConfig.label}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ModeSwitchConfirmDialog;
