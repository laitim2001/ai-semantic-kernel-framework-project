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

// Sprint 89: DevTools Streaming Hook
export {
  useDevToolsStream,
  type ConnectionStatus,
  type UseDevToolsStreamOptions,
  type UseDevToolsStreamReturn,
} from './useDevToolsStream';

// Sprint 138: Orchestrator Chat Hook (Phase 40)
export {
  useOrchestratorChat,
  type UseOrchestratorChatOptions,
  type UseOrchestratorChatReturn,
} from './useOrchestratorChat';

// Sprint 138: Session Management Hooks (Phase 40)
export {
  useSessions,
  useSession,
  useSessionMessages,
  useRecoverableSessions,
  useResumeSession,
  useDeleteSession,
  sessionKeys,
} from './useSessions';

// Sprint 139: Task Management Hooks (Phase 40)
export {
  useTasks,
  useTask,
  useTaskSteps,
  useCancelTask,
  useRetryTask,
  taskKeys,
} from './useTasks';

// Sprint 140: Knowledge Management Hooks (Phase 40)
export {
  useKnowledgeSearch,
  useDocuments,
  useUploadDocument,
  useDeleteDocument,
  useSkills,
  useKnowledgeStatus,
  knowledgeKeys,
} from './useKnowledge';

// Sprint 140: Memory System Hooks (Phase 40)
export {
  useMemorySearch,
  useUserMemories,
  useMemoryStats,
  useDeleteMemory,
  memoryKeys,
} from './useMemory';

// Phase 41: Typewriter Effect Hook (Sprint 141)
export {
  useTypewriterEffect,
} from './useTypewriterEffect';

// Phase 41: Tool Call Events Hook (Sprint 142)
export {
  useToolCallEvents,
} from './useToolCallEvents';

// Sprint 89: Event Filter Hook
export {
  useEventFilter,
  type EventFilterState,
  type UseEventFilterOptions,
  type UseEventFilterReturn,
} from './useEventFilter';
