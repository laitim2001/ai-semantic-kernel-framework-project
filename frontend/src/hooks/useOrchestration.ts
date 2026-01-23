/**
 * useOrchestration Hook
 *
 * Sprint 99: Phase 28 Integration - Orchestration Flow Management
 *
 * Manages the complete orchestration flow for chat messages:
 * 1. Three-layer intent routing
 * 2. Guided dialog for missing information
 * 3. Risk assessment
 * 4. HITL approval flow
 * 5. Hybrid execution
 */

import { useState, useCallback, useRef } from 'react';
import {
  orchestrationApi,
  type RoutingDecision,
  type RiskAssessment,
  type DialogStatusResponse,
  type DialogQuestion,
  type HybridExecuteResponse,
} from '@/api/endpoints/orchestration';

// =============================================================================
// Types
// =============================================================================

/** Orchestration flow state */
export type OrchestrationPhase =
  | 'idle'
  | 'routing'
  | 'dialog'
  | 'risk_assessment'
  | 'awaiting_approval'
  | 'executing'
  | 'completed'
  | 'error';

/** Orchestration state */
export interface OrchestrationState {
  phase: OrchestrationPhase;
  routingDecision: RoutingDecision | null;
  riskAssessment: RiskAssessment | null;
  dialogState: DialogStatusResponse | null;
  executionResult: HybridExecuteResponse | null;
  error: string | null;
  isLoading: boolean;
}

/** Orchestration options */
export interface OrchestrationOptions {
  /** Whether to include risk assessment in routing */
  includeRiskAssessment?: boolean;
  /** Whether to auto-execute after approval (if no approval needed) */
  autoExecute?: boolean;
  /** Session ID for correlation */
  sessionId?: string;
  /** User ID for dialog */
  userId?: string;
  /** Callback when routing is complete */
  onRoutingComplete?: (decision: RoutingDecision) => void;
  /** Callback when dialog questions are generated */
  onDialogQuestions?: (questions: DialogQuestion[]) => void;
  /** Callback when approval is required */
  onApprovalRequired?: (assessment: RiskAssessment) => void;
  /** Callback when execution is complete */
  onExecutionComplete?: (result: HybridExecuteResponse) => void;
  /** Callback on error */
  onError?: (error: string) => void;
}

/** Hook return type */
export interface UseOrchestrationReturn {
  /** Current orchestration state */
  state: OrchestrationState;
  /** Start orchestration flow with user message */
  startOrchestration: (message: string) => Promise<void>;
  /** Respond to dialog questions */
  respondToDialog: (responses: Record<string, unknown>) => Promise<void>;
  /** Proceed with execution (after approval) */
  proceedWithExecution: () => Promise<void>;
  /** Skip orchestration and execute directly */
  executeDirectly: (message: string) => Promise<void>;
  /** Reset orchestration state */
  reset: () => void;
  /** Cancel current operation */
  cancel: () => void;
}

// =============================================================================
// Initial State
// =============================================================================

const initialState: OrchestrationState = {
  phase: 'idle',
  routingDecision: null,
  riskAssessment: null,
  dialogState: null,
  executionResult: null,
  error: null,
  isLoading: false,
};

// =============================================================================
// Hook Implementation
// =============================================================================

export function useOrchestration(options: OrchestrationOptions = {}): UseOrchestrationReturn {
  const {
    includeRiskAssessment = true,
    autoExecute = true,
    sessionId,
    userId,
    onRoutingComplete,
    onDialogQuestions,
    onApprovalRequired,
    onExecutionComplete,
    onError,
  } = options;

  const [state, setState] = useState<OrchestrationState>(initialState);
  const cancelledRef = useRef(false);
  const currentMessageRef = useRef<string>('');

  // Update state helper
  const updateState = useCallback((updates: Partial<OrchestrationState>) => {
    setState((prev) => ({ ...prev, ...updates }));
  }, []);

  // Handle error
  const handleError = useCallback(
    (error: unknown) => {
      const errorMessage = error instanceof Error ? error.message : String(error);
      updateState({ phase: 'error', error: errorMessage, isLoading: false });
      onError?.(errorMessage);
    },
    [updateState, onError]
  );

  // Start orchestration flow
  const startOrchestration = useCallback(
    async (message: string) => {
      cancelledRef.current = false;
      currentMessageRef.current = message;

      try {
        // Phase 1: Intent Routing
        updateState({
          phase: 'routing',
          isLoading: true,
          error: null,
          routingDecision: null,
          riskAssessment: null,
          dialogState: null,
          executionResult: null,
        });

        const classifyResponse = await orchestrationApi.classify({
          content: message,
          include_risk_assessment: includeRiskAssessment,
        });

        if (cancelledRef.current) return;

        const { routing_decision: routingDecision, risk_assessment: riskAssessment } =
          classifyResponse;

        updateState({
          routingDecision,
          riskAssessment,
        });

        onRoutingComplete?.(routingDecision);

        // Check if information is complete
        const isComplete = routingDecision.completeness?.is_complete ?? true;
        const completenessScore = routingDecision.completeness?.completeness_score ?? 1.0;

        // Phase 2: Guided Dialog (if needed)
        if (!isComplete || completenessScore < 0.7) {
          updateState({ phase: 'dialog', isLoading: true });

          const dialogResponse = await orchestrationApi.startDialog({
            content: message,
            user_id: userId,
            session_id: sessionId,
          });

          if (cancelledRef.current) return;

          updateState({
            dialogState: dialogResponse,
            isLoading: false,
          });

          if (dialogResponse.questions && dialogResponse.questions.length > 0) {
            onDialogQuestions?.(dialogResponse.questions);
            return; // Wait for user response
          }
        }

        // Phase 3: Risk Assessment Check
        if (riskAssessment && riskAssessment.requires_approval) {
          updateState({
            phase: 'awaiting_approval',
            isLoading: false,
          });
          onApprovalRequired?.(riskAssessment);
          return; // Wait for approval
        }

        // Phase 4: Auto Execute (if enabled and no approval needed)
        if (autoExecute) {
          await executeInternal(message);
        } else {
          updateState({ phase: 'completed', isLoading: false });
        }
      } catch (error) {
        handleError(error);
      }
    },
    [
      includeRiskAssessment,
      autoExecute,
      sessionId,
      userId,
      updateState,
      handleError,
      onRoutingComplete,
      onDialogQuestions,
      onApprovalRequired,
    ]
  );

  // Internal execution function
  const executeInternal = useCallback(
    async (message: string) => {
      try {
        updateState({ phase: 'executing', isLoading: true });

        const result = await orchestrationApi.execute({
          input_text: message,
          session_id: sessionId,
        });

        if (cancelledRef.current) return;

        updateState({
          phase: 'completed',
          executionResult: result,
          isLoading: false,
        });

        onExecutionComplete?.(result);
      } catch (error) {
        handleError(error);
      }
    },
    [sessionId, updateState, handleError, onExecutionComplete]
  );

  // Respond to dialog questions
  const respondToDialog = useCallback(
    async (responses: Record<string, unknown>) => {
      if (!state.dialogState?.dialog_id) {
        handleError(new Error('No active dialog session'));
        return;
      }

      try {
        updateState({ isLoading: true });

        const dialogResponse = await orchestrationApi.respondToDialog(
          state.dialogState.dialog_id,
          { responses }
        );

        if (cancelledRef.current) return;

        updateState({ dialogState: dialogResponse });

        // Check if dialog is complete
        if (!dialogResponse.needs_more_info) {
          // Dialog is complete - proceed to risk assessment / execution
          // DON'T re-classify, just check if we need approval
          const currentRiskAssessment = state.riskAssessment;

          if (currentRiskAssessment && currentRiskAssessment.requires_approval) {
            updateState({
              phase: 'awaiting_approval',
              isLoading: false,
            });
            onApprovalRequired?.(currentRiskAssessment);
          } else if (autoExecute) {
            // No approval needed, execute directly
            await executeInternal(currentMessageRef.current);
          } else {
            updateState({ phase: 'completed', isLoading: false });
          }
        } else if (dialogResponse.questions && dialogResponse.questions.length > 0) {
          updateState({ isLoading: false });
          onDialogQuestions?.(dialogResponse.questions);
        }
      } catch (error) {
        handleError(error);
      }
    },
    [
      state.dialogState?.dialog_id, state.riskAssessment, autoExecute,
      updateState, handleError, executeInternal, onDialogQuestions, onApprovalRequired
    ]
  );

  // Proceed with execution after approval
  const proceedWithExecution = useCallback(async () => {
    await executeInternal(currentMessageRef.current);
  }, [executeInternal]);

  // Execute directly without orchestration
  const executeDirectly = useCallback(
    async (message: string) => {
      currentMessageRef.current = message;
      await executeInternal(message);
    },
    [executeInternal]
  );

  // Reset state
  const reset = useCallback(() => {
    cancelledRef.current = true;
    currentMessageRef.current = '';
    setState(initialState);
  }, []);

  // Cancel current operation
  const cancel = useCallback(() => {
    cancelledRef.current = true;
    updateState({ isLoading: false });
  }, [updateState]);

  return {
    state,
    startOrchestration,
    respondToDialog,
    proceedWithExecution,
    executeDirectly,
    reset,
    cancel,
  };
}

export default useOrchestration;
