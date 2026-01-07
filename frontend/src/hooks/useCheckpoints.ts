/**
 * useCheckpoints - Checkpoint Management Hook
 *
 * Sprint 65: Metrics, Checkpoints & Polish
 * S65-2: Checkpoint Integration
 * Phase 16: Unified Agentic Chat Interface
 *
 * Manages checkpoint loading, state tracking, and restore functionality
 * with API integration and confirmation dialogs.
 */

import { useState, useCallback, useEffect } from 'react';
import type { Checkpoint } from '@/types/unified-chat';
import { aguiApi } from '@/api/endpoints/ag-ui';

// =============================================================================
// Types
// =============================================================================

/** Restore confirmation state */
export interface RestoreConfirmation {
  checkpointId: string;
  checkpoint: Checkpoint;
  isOpen: boolean;
}

/** Restore result from API */
export interface RestoreResult {
  success: boolean;
  checkpointId: string;
  restoredState?: Record<string, unknown>;
  error?: string;
}

/** Hook options */
export interface UseCheckpointsOptions {
  /** Session ID for loading checkpoints */
  sessionId?: string;
  /** Thread ID for loading checkpoints */
  threadId?: string;
  /** Callback when restore succeeds */
  onRestoreSuccess?: (result: RestoreResult) => void;
  /** Callback when restore fails */
  onRestoreError?: (error: Error, checkpointId: string) => void;
  /** Whether to disable restore during execution */
  disableDuringExecution?: boolean;
  /** Check if execution is active */
  isExecuting?: boolean;
}

/** Hook return type */
export interface UseCheckpointsReturn {
  // State
  checkpoints: Checkpoint[];
  currentCheckpoint: string | null;
  isRestoring: boolean;
  isLoading: boolean;
  error: string | null;

  // Confirmation dialog state
  restoreConfirmation: RestoreConfirmation | null;

  // Computed
  canRestore: boolean;
  hasCheckpoints: boolean;

  // Actions
  loadCheckpoints: () => Promise<void>;
  addCheckpoint: (checkpoint: Checkpoint) => void;
  setCheckpoints: (checkpoints: Checkpoint[]) => void;
  setCurrentCheckpoint: (id: string | null) => void;

  // Restore actions
  requestRestore: (checkpointId: string) => void;
  confirmRestore: () => Promise<void>;
  cancelRestore: () => void;

  // Direct restore (without confirmation)
  restoreCheckpoint: (checkpointId: string) => Promise<RestoreResult>;

  // Clear
  clearCheckpoints: () => void;
  clearError: () => void;
}

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * useCheckpoints Hook
 *
 * Manages checkpoint state and restore operations.
 *
 * @example
 * ```tsx
 * const {
 *   checkpoints,
 *   currentCheckpoint,
 *   isRestoring,
 *   restoreConfirmation,
 *   requestRestore,
 *   confirmRestore,
 *   cancelRestore,
 * } = useCheckpoints({
 *   sessionId: 'session-123',
 *   onRestoreSuccess: (result) => console.log('Restored:', result),
 * });
 *
 * // Request restore with confirmation
 * <Button onClick={() => requestRestore(checkpoint.id)}>Restore</Button>
 *
 * // Confirmation dialog
 * {restoreConfirmation && (
 *   <Dialog open={restoreConfirmation.isOpen}>
 *     <DialogContent>
 *       <p>Restore to checkpoint {restoreConfirmation.checkpoint.label}?</p>
 *       <Button onClick={confirmRestore}>Confirm</Button>
 *       <Button onClick={cancelRestore}>Cancel</Button>
 *     </DialogContent>
 *   </Dialog>
 * )}
 * ```
 */
export function useCheckpoints(
  options: UseCheckpointsOptions = {}
): UseCheckpointsReturn {
  const {
    sessionId,
    threadId,
    onRestoreSuccess,
    onRestoreError,
    disableDuringExecution = true,
    isExecuting = false,
  } = options;

  // State
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [currentCheckpoint, setCurrentCheckpoint] = useState<string | null>(null);
  const [isRestoring, setIsRestoring] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [restoreConfirmation, setRestoreConfirmation] = useState<RestoreConfirmation | null>(null);

  // ==========================================================================
  // Computed
  // ==========================================================================

  const canRestore = !isRestoring && !(disableDuringExecution && isExecuting);
  const hasCheckpoints = checkpoints.length > 0;

  // ==========================================================================
  // Load Checkpoints
  // ==========================================================================

  const loadCheckpoints = useCallback(async () => {
    if (!sessionId && !threadId) return;

    setIsLoading(true);
    setError(null);

    try {
      const loadedCheckpoints = await aguiApi.getCheckpoints(sessionId || threadId!);
      setCheckpoints(loadedCheckpoints);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load checkpoints';
      setError(message);
      console.error('[useCheckpoints] Failed to load checkpoints:', err);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, threadId]);

  // ==========================================================================
  // Add/Set Checkpoints
  // ==========================================================================

  const addCheckpoint = useCallback((checkpoint: Checkpoint) => {
    setCheckpoints((prev) => {
      // Check if already exists
      const exists = prev.some((cp) => cp.id === checkpoint.id);
      if (exists) {
        // Update existing
        return prev.map((cp) =>
          cp.id === checkpoint.id ? checkpoint : cp
        );
      }
      // Add new
      return [...prev, checkpoint];
    });

    // Set as current if no current checkpoint
    setCurrentCheckpoint((prev) => prev || checkpoint.id);
  }, []);

  const setCheckpointsHandler = useCallback((newCheckpoints: Checkpoint[]) => {
    setCheckpoints(newCheckpoints);
  }, []);

  const setCurrentCheckpointHandler = useCallback((id: string | null) => {
    setCurrentCheckpoint(id);
  }, []);

  // ==========================================================================
  // Restore Actions
  // ==========================================================================

  /**
   * Request restore with confirmation dialog
   */
  const requestRestore = useCallback((checkpointId: string) => {
    if (!canRestore) return;

    const checkpoint = checkpoints.find((cp) => cp.id === checkpointId);
    if (!checkpoint) {
      console.error('[useCheckpoints] Checkpoint not found:', checkpointId);
      return;
    }

    if (!checkpoint.canRestore) {
      console.error('[useCheckpoints] Checkpoint cannot be restored:', checkpointId);
      return;
    }

    setRestoreConfirmation({
      checkpointId,
      checkpoint,
      isOpen: true,
    });
  }, [canRestore, checkpoints]);

  /**
   * Confirm restore from confirmation dialog
   */
  const confirmRestore = useCallback(async () => {
    if (!restoreConfirmation) return;

    const { checkpointId } = restoreConfirmation;

    // Close dialog first
    setRestoreConfirmation(null);

    // Perform restore
    await restoreCheckpoint(checkpointId);
  }, [restoreConfirmation]);

  /**
   * Cancel restore confirmation
   */
  const cancelRestore = useCallback(() => {
    setRestoreConfirmation(null);
  }, []);

  /**
   * Direct restore without confirmation
   */
  const restoreCheckpoint = useCallback(async (checkpointId: string): Promise<RestoreResult> => {
    if (!canRestore) {
      return {
        success: false,
        checkpointId,
        error: isExecuting ? 'Cannot restore during execution' : 'Restore not available',
      };
    }

    setIsRestoring(true);
    setError(null);

    try {
      const result = await aguiApi.restoreCheckpoint(checkpointId);

      // Update current checkpoint
      setCurrentCheckpoint(checkpointId);

      const restoreResult: RestoreResult = {
        success: true,
        checkpointId,
        restoredState: result.restoredState,
      };

      onRestoreSuccess?.(restoreResult);
      return restoreResult;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to restore checkpoint';
      setError(errorMessage);

      if (err instanceof Error) {
        onRestoreError?.(err, checkpointId);
      }

      console.error('[useCheckpoints] Failed to restore checkpoint:', err);

      return {
        success: false,
        checkpointId,
        error: errorMessage,
      };
    } finally {
      setIsRestoring(false);
    }
  }, [canRestore, isExecuting, onRestoreSuccess, onRestoreError]);

  // ==========================================================================
  // Clear Actions
  // ==========================================================================

  const clearCheckpoints = useCallback(() => {
    setCheckpoints([]);
    setCurrentCheckpoint(null);
    setRestoreConfirmation(null);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // ==========================================================================
  // Effects
  // ==========================================================================

  // Load checkpoints when session/thread changes
  useEffect(() => {
    if (sessionId || threadId) {
      loadCheckpoints();
    }
  }, [sessionId, threadId, loadCheckpoints]);

  // ==========================================================================
  // Return
  // ==========================================================================

  return {
    // State
    checkpoints,
    currentCheckpoint,
    isRestoring,
    isLoading,
    error,

    // Confirmation dialog state
    restoreConfirmation,

    // Computed
    canRestore,
    hasCheckpoints,

    // Actions
    loadCheckpoints,
    addCheckpoint,
    setCheckpoints: setCheckpointsHandler,
    setCurrentCheckpoint: setCurrentCheckpointHandler,

    // Restore actions
    requestRestore,
    confirmRestore,
    cancelRestore,

    // Direct restore
    restoreCheckpoint,

    // Clear
    clearCheckpoints,
    clearError,
  };
}

export default useCheckpoints;
