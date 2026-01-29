/**
 * Agent Swarm Module - Index
 *
 * Export all agent swarm related components, hooks, and types.
 * Sprint 101: Event system and SSE integration
 * Sprint 102: UI components (Panel, Cards, Badges)
 * Sprint 103: WorkerDetailDrawer and sub-components
 * Sprint 104: ExtendedThinking + WorkerActionList
 */

// =============================================================================
// Types
// =============================================================================
export * from './types';

// =============================================================================
// Hooks
// =============================================================================
export * from './hooks';

// =============================================================================
// Components (Sprint 102)
// =============================================================================
export { AgentSwarmPanel } from './AgentSwarmPanel';
export { SwarmHeader } from './SwarmHeader';
export { OverallProgress } from './OverallProgress';
export { WorkerCard } from './WorkerCard';
export { WorkerCardList } from './WorkerCardList';
export { SwarmStatusBadges } from './SwarmStatusBadges';

// =============================================================================
// Components (Sprint 103)
// =============================================================================
export { WorkerDetailDrawer } from './WorkerDetailDrawer';
export { WorkerDetailHeader } from './WorkerDetailHeader';
export { CurrentTask } from './CurrentTask';
export { ToolCallItem } from './ToolCallItem';
export { ToolCallsPanel } from './ToolCallsPanel';
export { MessageHistory } from './MessageHistory';
export { CheckpointPanel } from './CheckpointPanel';

// =============================================================================
// Components (Sprint 104)
// =============================================================================
export { ExtendedThinkingPanel } from './ExtendedThinkingPanel';
export { WorkerActionList, inferActionType } from './WorkerActionList';
export type { ActionType, WorkerAction } from './WorkerActionList';
