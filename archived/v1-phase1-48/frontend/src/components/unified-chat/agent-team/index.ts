/**
 * Agent Team Module - Index
 *
 * Export all agent team related components, hooks, and types.
 * Sprint 101: Event system and SSE integration
 * Sprint 102: UI components (Panel, Cards, Badges)
 * Sprint 103: AgentDetailDrawer and sub-components
 * Sprint 104: ExtendedThinking + AgentActionList
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
export { AgentTeamPanel } from './AgentTeamPanel';
export { AgentTeamHeader } from './AgentTeamHeader';
export { OverallProgress } from './OverallProgress';
export { AgentCard } from './AgentCard';
export { AgentCardList } from './AgentCardList';
export { AgentTeamStatusBadges } from './AgentTeamStatusBadges';

// =============================================================================
// Components (Sprint 103)
// =============================================================================
export { AgentDetailDrawer } from './AgentDetailDrawer';
export { AgentDetailHeader } from './AgentDetailHeader';
export { CurrentTask } from './CurrentTask';
export { ToolCallItem } from './ToolCallItem';
export { ToolCallsPanel } from './ToolCallsPanel';
export { MessageHistory } from './MessageHistory';
export { CheckpointPanel } from './CheckpointPanel';

// =============================================================================
// Components (Sprint 104)
// =============================================================================
export { ExtendedThinkingPanel } from './ExtendedThinkingPanel';
export { AgentActionList, inferActionType } from './AgentActionList';
export type { ActionType, AgentAction } from './AgentActionList';
