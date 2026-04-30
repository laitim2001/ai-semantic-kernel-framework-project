/**
 * Agent Team Hooks - Index
 *
 * Export all agent-team-related hooks.
 * Sprint 101: Agent Team Event System + SSE Integration
 * Sprint 103: AgentDetailDrawer
 * Sprint 105: OrchestrationPanel 整合 + 狀態管理
 */

export {
  useAgentTeamEvents,
  isTeamEvent,
  getTeamEventCategory,
} from './useAgentTeamEvents';

export { useAgentDetail } from './useAgentDetail';
export type {
  UseAgentDetailOptions,
  UseAgentDetailResult,
} from './useAgentDetail';

export { useTeamStatus } from './useAgentTeamStatus';
export type { UseTeamStatusReturn } from './useAgentTeamStatus';

export { useAgentTeamEventHandler } from './useAgentTeamEventHandler';
export type { UseAgentTeamEventHandlerOptions } from './useAgentTeamEventHandler';
