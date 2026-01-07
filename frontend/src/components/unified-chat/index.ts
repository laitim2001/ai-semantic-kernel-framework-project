/**
 * Unified Chat Components
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * Phase 16: Unified Agentic Chat Interface
 *
 * Export all unified chat components for easy import.
 */

// S62-1: Base Architecture
export { ChatHeader } from './ChatHeader';
export { ChatInput } from './ChatInput';
export { StatusBar } from './StatusBar';

// S62-3: Chat Area
export { ChatArea } from './ChatArea';
export { MessageList } from './MessageList';
export { InlineApproval } from './InlineApproval';

// S62-4: Workflow Side Panel
export { WorkflowSidePanel } from './WorkflowSidePanel';
export { StepProgress } from './StepProgress';
export { ToolCallTracker } from './ToolCallTracker';
export { CheckpointList } from './CheckpointList';

// Re-export types for convenience
export type {
  ChatHeaderProps,
  ChatInputProps,
  StatusBarProps,
  ChatAreaProps,
  InlineApprovalProps,
  WorkflowSidePanelProps,
  StepProgressProps,
  ToolCallTrackerProps,
  CheckpointListProps,
  ExecutionMode,
  ConnectionStatus,
} from '@/types/unified-chat';
