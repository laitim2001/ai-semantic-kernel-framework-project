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
  type ModeDetectionEvent,
} from './useHybridMode';
