/**
 * useApprovalFlow - HITL Approval Flow Management Hook
 *
 * Sprint 64: Approval Flow & Risk Indicators
 * S64-1: useApprovalFlow Hook
 * Phase 16: Unified Agentic Chat Interface
 *
 * Manages the Human-in-the-Loop approval flow for tool calls,
 * including pending approvals, dialog state, timeout handling,
 * and mode switch confirmations.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import type { PendingApproval, RiskLevel } from '@/types/ag-ui';
import type { ExecutionMode } from '@/types/unified-chat';
import { aguiApi } from '@/api/endpoints/ag-ui';

// =============================================================================
// Types
// =============================================================================

/** Mode switch pending state */
export interface ModeSwitchPending {
  from: ExecutionMode;
  to: ExecutionMode;
  reason: string;
  confidence: number;
  requestedAt: string;
}

/** Approval flow options */
export interface UseApprovalFlowOptions {
  /** Auto-show dialog for high/critical risk */
  autoShowDialog?: boolean;
  /** Default timeout in seconds for approvals */
  defaultTimeout?: number;
  /** Callback when approval is processed */
  onApprovalProcessed?: (toolCallId: string, action: 'approved' | 'rejected') => void;
  /** Callback when approval times out */
  onApprovalTimeout?: (toolCallId: string) => void;
  /** Callback for mode switch confirmation */
  onModeSwitchConfirm?: (to: ExecutionMode) => void;
  /** Callback for mode switch cancellation */
  onModeSwitchCancel?: () => void;
  /** Confidence threshold for auto-accepting mode switches */
  modeSwitchAutoAcceptThreshold?: number;
}

/** Approval flow return type */
export interface UseApprovalFlowReturn {
  // State
  pendingApprovals: PendingApproval[];
  dialogApproval: PendingApproval | null;
  isProcessing: boolean;
  modeSwitchPending: ModeSwitchPending | null;

  // Computed
  hasPendingApprovals: boolean;
  highRiskCount: number;
  criticalRiskCount: number;

  // Actions
  addPendingApproval: (approval: PendingApproval) => void;
  approve: (toolCallId: string) => Promise<void>;
  reject: (toolCallId: string, reason?: string) => Promise<void>;
  dismissDialog: () => void;
  showApprovalDialog: (approval: PendingApproval) => void;

  // Mode switch actions
  requestModeSwitch: (params: Omit<ModeSwitchPending, 'requestedAt'>) => void;
  confirmModeSwitch: () => void;
  cancelModeSwitch: () => void;

  // Utility
  getApprovalById: (toolCallId: string) => PendingApproval | undefined;
  clearExpiredApprovals: () => void;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Check if an approval is expired
 */
const isApprovalExpired = (approval: PendingApproval): boolean => {
  return new Date(approval.expiresAt).getTime() < Date.now();
};

/**
 * Get risk level priority (higher = more critical)
 */
const getRiskPriority = (level: RiskLevel): number => {
  const priorities: Record<RiskLevel, number> = {
    low: 1,
    medium: 2,
    high: 3,
    critical: 4,
  };
  return priorities[level] ?? 0;
};

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * useApprovalFlow Hook
 *
 * Manages the complete approval flow for HITL operations.
 *
 * @example
 * ```tsx
 * const {
 *   pendingApprovals,
 *   dialogApproval,
 *   approve,
 *   reject,
 *   dismissDialog,
 * } = useApprovalFlow({
 *   onApprovalProcessed: (id, action) => console.log(`${id} ${action}`),
 * });
 * ```
 */
export function useApprovalFlow(
  options: UseApprovalFlowOptions = {}
): UseApprovalFlowReturn {
  const {
    autoShowDialog = true,
    defaultTimeout: _defaultTimeout = 300, // 5 minutes - reserved for future timeout UI
    onApprovalProcessed,
    onApprovalTimeout,
    onModeSwitchConfirm,
    onModeSwitchCancel,
    modeSwitchAutoAcceptThreshold = 0.9,
  } = options;

  // State
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [dialogApproval, setDialogApproval] = useState<PendingApproval | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [modeSwitchPending, setModeSwitchPending] = useState<ModeSwitchPending | null>(null);

  // Refs for cleanup
  const timeoutRefs = useRef<Map<string, NodeJS.Timeout>>(new Map());

  // ==========================================================================
  // Computed Values
  // ==========================================================================

  const hasPendingApprovals = pendingApprovals.length > 0;

  const highRiskCount = pendingApprovals.filter(
    (a) => a.riskLevel === 'high'
  ).length;

  const criticalRiskCount = pendingApprovals.filter(
    (a) => a.riskLevel === 'critical'
  ).length;

  // ==========================================================================
  // Timeout Management
  // ==========================================================================

  /**
   * Set up timeout for an approval
   */
  const setupApprovalTimeout = useCallback(
    (approval: PendingApproval) => {
      const timeUntilExpiry = new Date(approval.expiresAt).getTime() - Date.now();

      if (timeUntilExpiry <= 0) {
        // Already expired
        onApprovalTimeout?.(approval.toolCallId);
        return;
      }

      const timeoutId = setTimeout(() => {
        setPendingApprovals((prev) =>
          prev.filter((a) => a.toolCallId !== approval.toolCallId)
        );
        if (dialogApproval?.toolCallId === approval.toolCallId) {
          setDialogApproval(null);
        }
        onApprovalTimeout?.(approval.toolCallId);
        timeoutRefs.current.delete(approval.toolCallId);
      }, timeUntilExpiry);

      timeoutRefs.current.set(approval.toolCallId, timeoutId);
    },
    [dialogApproval, onApprovalTimeout]
  );

  /**
   * Clear timeout for an approval
   */
  const clearApprovalTimeout = useCallback((toolCallId: string) => {
    const timeoutId = timeoutRefs.current.get(toolCallId);
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutRefs.current.delete(toolCallId);
    }
  }, []);

  // ==========================================================================
  // Approval Actions
  // ==========================================================================

  /**
   * Add a new pending approval
   */
  const addPendingApproval = useCallback(
    (approval: PendingApproval) => {
      // Check if already exists
      setPendingApprovals((prev) => {
        if (prev.some((a) => a.toolCallId === approval.toolCallId)) {
          return prev;
        }
        return [...prev, approval];
      });

      // Set up timeout
      setupApprovalTimeout(approval);

      // Auto-show dialog for high/critical risk
      if (
        autoShowDialog &&
        (approval.riskLevel === 'high' || approval.riskLevel === 'critical')
      ) {
        // If already showing a dialog, only replace if new is higher priority
        setDialogApproval((prev) => {
          if (!prev) return approval;
          if (getRiskPriority(approval.riskLevel) > getRiskPriority(prev.riskLevel)) {
            return approval;
          }
          return prev;
        });
      }
    },
    [autoShowDialog, setupApprovalTimeout]
  );

  /**
   * Approve a tool call
   */
  const approve = useCallback(
    async (toolCallId: string) => {
      setIsProcessing(true);

      // Store original approval for rollback
      const originalApproval = pendingApprovals.find(
        (a) => a.toolCallId === toolCallId
      );

      try {
        // Optimistic update: Remove from pending immediately
        setPendingApprovals((prev) =>
          prev.filter((a) => a.toolCallId !== toolCallId)
        );

        // Clear timeout
        clearApprovalTimeout(toolCallId);

        // Close dialog if showing this approval
        if (dialogApproval?.toolCallId === toolCallId) {
          setDialogApproval(null);
        }

        // Call API
        await aguiApi.approve(toolCallId);

        // Callback on success
        onApprovalProcessed?.(toolCallId, 'approved');
      } catch (error) {
        // Rollback on failure
        if (originalApproval) {
          setPendingApprovals((prev) => [...prev, originalApproval]);
        }
        console.error('[useApprovalFlow] Failed to approve:', error);
        throw error;
      } finally {
        setIsProcessing(false);
      }
    },
    [pendingApprovals, dialogApproval, clearApprovalTimeout, onApprovalProcessed]
  );

  /**
   * Reject a tool call
   */
  const reject = useCallback(
    async (toolCallId: string, reason?: string) => {
      setIsProcessing(true);

      // Store original approval for rollback
      const originalApproval = pendingApprovals.find(
        (a) => a.toolCallId === toolCallId
      );

      try {
        // Optimistic update: Remove from pending immediately
        setPendingApprovals((prev) =>
          prev.filter((a) => a.toolCallId !== toolCallId)
        );

        // Clear timeout
        clearApprovalTimeout(toolCallId);

        // Close dialog if showing this approval
        if (dialogApproval?.toolCallId === toolCallId) {
          setDialogApproval(null);
        }

        // Call API
        await aguiApi.reject(toolCallId, reason);

        // Callback on success
        onApprovalProcessed?.(toolCallId, 'rejected');
      } catch (error) {
        // Rollback on failure
        if (originalApproval) {
          setPendingApprovals((prev) => [...prev, originalApproval]);
        }
        console.error('[useApprovalFlow] Failed to reject:', error);
        throw error;
      } finally {
        setIsProcessing(false);
      }
    },
    [pendingApprovals, dialogApproval, clearApprovalTimeout, onApprovalProcessed]
  );

  /**
   * Dismiss the approval dialog
   */
  const dismissDialog = useCallback(() => {
    setDialogApproval(null);
  }, []);

  /**
   * Show approval dialog for a specific approval
   */
  const showApprovalDialog = useCallback((approval: PendingApproval) => {
    setDialogApproval(approval);
  }, []);

  /**
   * Get approval by tool call ID
   */
  const getApprovalById = useCallback(
    (toolCallId: string): PendingApproval | undefined => {
      return pendingApprovals.find((a) => a.toolCallId === toolCallId);
    },
    [pendingApprovals]
  );

  /**
   * Clear all expired approvals
   */
  const clearExpiredApprovals = useCallback(() => {
    setPendingApprovals((prev) =>
      prev.filter((a) => !isApprovalExpired(a))
    );
  }, []);

  // ==========================================================================
  // Mode Switch Actions
  // ==========================================================================

  /**
   * Request a mode switch (shows confirmation if needed)
   */
  const requestModeSwitch = useCallback(
    (params: Omit<ModeSwitchPending, 'requestedAt'>) => {
      // Auto-accept high-confidence simple switches
      if (params.confidence >= modeSwitchAutoAcceptThreshold) {
        onModeSwitchConfirm?.(params.to);
        return;
      }

      // Require confirmation for complex or lower-confidence switches
      setModeSwitchPending({
        ...params,
        requestedAt: new Date().toISOString(),
      });
    },
    [modeSwitchAutoAcceptThreshold, onModeSwitchConfirm]
  );

  /**
   * Confirm pending mode switch
   */
  const confirmModeSwitch = useCallback(() => {
    if (modeSwitchPending) {
      onModeSwitchConfirm?.(modeSwitchPending.to);
      setModeSwitchPending(null);
    }
  }, [modeSwitchPending, onModeSwitchConfirm]);

  /**
   * Cancel pending mode switch
   */
  const cancelModeSwitch = useCallback(() => {
    onModeSwitchCancel?.();
    setModeSwitchPending(null);
  }, [onModeSwitchCancel]);

  // ==========================================================================
  // Effects
  // ==========================================================================

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      timeoutRefs.current.forEach((timeoutId) => clearTimeout(timeoutId));
      timeoutRefs.current.clear();
    };
  }, []);

  // Periodic cleanup of expired approvals
  useEffect(() => {
    const interval = setInterval(clearExpiredApprovals, 10000); // Every 10 seconds
    return () => clearInterval(interval);
  }, [clearExpiredApprovals]);

  // ==========================================================================
  // Return
  // ==========================================================================

  return {
    // State
    pendingApprovals,
    dialogApproval,
    isProcessing,
    modeSwitchPending,

    // Computed
    hasPendingApprovals,
    highRiskCount,
    criticalRiskCount,

    // Actions
    addPendingApproval,
    approve,
    reject,
    dismissDialog,
    showApprovalDialog,

    // Mode switch actions
    requestModeSwitch,
    confirmModeSwitch,
    cancelModeSwitch,

    // Utility
    getApprovalById,
    clearExpiredApprovals,
  };
}

export default useApprovalFlow;
