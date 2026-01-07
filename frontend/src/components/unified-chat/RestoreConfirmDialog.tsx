/**
 * RestoreConfirmDialog - Checkpoint Restore Confirmation
 *
 * Sprint 65: Metrics, Checkpoints & Polish
 * S65-2: Checkpoint Integration
 * Phase 16: Unified Agentic Chat Interface
 *
 * Modal dialog for confirming checkpoint restoration.
 * Shows checkpoint details and warns about data loss.
 */

import { FC } from 'react';
import {
  AlertTriangle,
  RotateCcw,
  Clock,
  BookmarkCheck,
  X,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import type { Checkpoint } from '@/types/unified-chat';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

export interface RestoreConfirmDialogProps {
  /** Whether the dialog is open */
  isOpen: boolean;
  /** The checkpoint to restore */
  checkpoint: Checkpoint | null;
  /** Whether restore is in progress */
  isRestoring?: boolean;
  /** Callback when user confirms restore */
  onConfirm: () => void;
  /** Callback when user cancels */
  onCancel: () => void;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Format timestamp to readable date/time
 */
const formatTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp);
  return date.toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

/**
 * Format relative time
 */
const formatRelativeTime = (timestamp: string): string => {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`;
  if (diffHour < 24) return `${diffHour} hour${diffHour > 1 ? 's' : ''} ago`;
  return then.toLocaleDateString('zh-TW');
};

// =============================================================================
// Component
// =============================================================================

/**
 * RestoreConfirmDialog Component
 *
 * Shows a confirmation dialog before restoring a checkpoint.
 * Includes checkpoint details and a warning about data loss.
 */
export const RestoreConfirmDialog: FC<RestoreConfirmDialogProps> = ({
  isOpen,
  checkpoint,
  isRestoring = false,
  onConfirm,
  onCancel,
}) => {
  if (!checkpoint) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onCancel()}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RotateCcw className="h-5 w-5 text-blue-500" />
            Restore Checkpoint
          </DialogTitle>
          <DialogDescription>
            Are you sure you want to restore to this checkpoint?
          </DialogDescription>
        </DialogHeader>

        {/* Checkpoint Details */}
        <div className="space-y-4 py-4">
          {/* Checkpoint Info Card */}
          <div className="rounded-lg border bg-gray-50 p-4 space-y-3">
            <div className="flex items-center gap-2">
              <BookmarkCheck className="h-5 w-5 text-green-600" />
              <span className="font-medium">
                {checkpoint.label || 'Checkpoint'}
              </span>
            </div>

            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Clock className="h-4 w-4" />
              <span>{formatTimestamp(checkpoint.timestamp)}</span>
              <span className="text-gray-400">
                ({formatRelativeTime(checkpoint.timestamp)})
              </span>
            </div>

            {checkpoint.stepIndex !== undefined && (
              <div className="text-sm text-gray-600">
                <span className="font-medium">Step:</span> {checkpoint.stepIndex + 1}
              </div>
            )}

            {checkpoint.metadata && Object.keys(checkpoint.metadata).length > 0 && (
              <div className="text-xs text-gray-500 pt-2 border-t">
                <span className="font-medium">Metadata:</span>
                <pre className="mt-1 overflow-auto max-h-20">
                  {JSON.stringify(checkpoint.metadata, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {/* Warning */}
          <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-50 border border-amber-200">
            <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-amber-800">
              <p className="font-medium">Warning</p>
              <p className="mt-1">
                Restoring will discard all messages and state changes made after this checkpoint.
                This action cannot be undone.
              </p>
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={onCancel}
            disabled={isRestoring}
          >
            <X className="h-4 w-4 mr-1" />
            Cancel
          </Button>
          <Button
            onClick={onConfirm}
            disabled={isRestoring}
            className={cn(
              'bg-blue-600 hover:bg-blue-700',
              isRestoring && 'opacity-50 cursor-not-allowed'
            )}
          >
            {isRestoring ? (
              <>
                <div className="h-4 w-4 mr-2 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Restoring...
              </>
            ) : (
              <>
                <RotateCcw className="h-4 w-4 mr-1" />
                Restore
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default RestoreConfirmDialog;
