/**
 * Hooks Index
 *
 * Central export for all custom React hooks.
 * Sprint 62: Added useHybridMode for unified chat interface.
 */

// AG-UI Protocol Hooks
export { useAGUI, type UseAGUIOptions, type UseAGUIReturn } from './useAGUI';
export {
  useSharedState,
  type UseSharedStateOptions,
  type UseSharedStateReturn,
} from './useSharedState';
export {
  useOptimisticState,
  type UseOptimisticStateOptions,
  type UseOptimisticStateReturn,
} from './useOptimisticState';

// Phase 16: Unified Chat Interface Hooks
export {
  useHybridMode,
  dispatchModeDetection,
  type UseHybridModeConfig,
  type UseHybridModeReturn,
  type ModeDetectionEvent,
} from './useHybridMode';

// Sprint 63: Unified Chat Orchestration Hook
export {
  useUnifiedChat,
  type UseUnifiedChatOptions,
  type UseUnifiedChatReturn,
} from './useUnifiedChat';

// Sprint 64: Approval Flow Hook
export {
  useApprovalFlow,
  type UseApprovalFlowOptions,
  type UseApprovalFlowReturn,
  type ModeSwitchPending,
} from './useApprovalFlow';

// Sprint 65: Execution Metrics Hook
export {
  useExecutionMetrics,
  type UseExecutionMetricsOptions,
  type UseExecutionMetricsReturn,
  type TokenMetrics,
  type TimeMetrics,
  type ToolMetrics,
  type MessageMetrics,
  type ExecutionMetricsState,
} from './useExecutionMetrics';

// Sprint 65: Checkpoint Management Hook
export {
  useCheckpoints,
  type UseCheckpointsOptions,
  type UseCheckpointsReturn,
  type RestoreConfirmation,
  type RestoreResult,
} from './useCheckpoints';
