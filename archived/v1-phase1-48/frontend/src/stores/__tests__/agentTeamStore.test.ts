/**
 * AgentTeamStore Test Suite
 *
 * Tests for the Agent Team Zustand store.
 * Sprint 105: OrchestrationPanel 整合 + 狀態管理
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { act } from '@testing-library/react';
import {
  useAgentTeamStore,
  selectTeamStatus,
  selectAgents,
  selectCompletedAgents,
  selectRunningAgents,
  selectFailedAgents,
  selectIsTeamActive,
} from '../agentTeamStore';
import type { UIAgentTeamStatus, UIAgentSummary } from '@/components/unified-chat/agent-team/types';

// =============================================================================
// Test Fixtures
// =============================================================================

const createMockTeamStatus = (overrides?: Partial<UIAgentTeamStatus>): UIAgentTeamStatus => ({
  teamId: 'team-1',
  sessionId: 'session-1',
  mode: 'parallel',
  status: 'executing',
  totalAgents: 2,
  overallProgress: 50,
  agents: [
    {
      agentId: 'agent-1',
      agentName: 'Research Agent',
      agentType: 'research',
      role: 'Data Gatherer',
      status: 'running',
      progress: 50,
      currentAction: 'Searching...',
      toolCallsCount: 3,
      createdAt: '2026-01-29T10:00:00Z',
      startedAt: '2026-01-29T10:00:00Z',
    },
    {
      agentId: 'agent-2',
      agentName: 'Writer Agent',
      agentType: 'custom',
      role: 'Content Writer',
      status: 'pending',
      progress: 0,
      toolCallsCount: 0,
      createdAt: '2026-01-29T10:00:00Z',
    },
  ],
  createdAt: '2026-01-29T10:00:00Z',
  metadata: {},
  ...overrides,
});

const createMockAgent = (overrides?: Partial<UIAgentSummary>): UIAgentSummary => ({
  agentId: 'agent-new',
  agentName: 'New Agent',
  agentType: 'custom',
  role: 'Helper',
  status: 'pending',
  progress: 0,
  toolCallsCount: 0,
  createdAt: '2026-01-29T10:00:00Z',
  ...overrides,
});

// =============================================================================
// Tests
// =============================================================================

describe('AgentTeamStore', () => {
  // Reset store before each test
  beforeEach(() => {
    act(() => {
      useAgentTeamStore.getState().reset();
    });
  });

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      const state = useAgentTeamStore.getState();

      expect(state.agentTeamStatus).toBeNull();
      expect(state.selectedAgentId).toBeNull();
      expect(state.selectedAgentDetail).toBeNull();
      expect(state.isDrawerOpen).toBe(false);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });
  });

  describe('Team-level Actions', () => {
    it('should set team status', () => {
      const mockStatus = createMockTeamStatus();

      act(() => {
        useAgentTeamStore.getState().setTeamStatus(mockStatus);
      });

      const state = useAgentTeamStore.getState();
      expect(state.agentTeamStatus).toEqual(mockStatus);
      expect(state.agentTeamStatus?.teamId).toBe('team-1');
    });

    it('should clear team status when set to null', () => {
      const mockStatus = createMockTeamStatus();

      act(() => {
        useAgentTeamStore.getState().setTeamStatus(mockStatus);
        useAgentTeamStore.getState().setTeamStatus(null);
      });

      expect(useAgentTeamStore.getState().agentTeamStatus).toBeNull();
    });

    it('should update team progress', () => {
      const mockStatus = createMockTeamStatus();

      act(() => {
        useAgentTeamStore.getState().setTeamStatus(mockStatus);
        useAgentTeamStore.getState().updateTeamProgress(75);
      });

      expect(useAgentTeamStore.getState().agentTeamStatus?.overallProgress).toBe(75);
    });

    it('should complete team', () => {
      const mockStatus = createMockTeamStatus();

      act(() => {
        useAgentTeamStore.getState().setTeamStatus(mockStatus);
        useAgentTeamStore.getState().completeTeam('completed', '2026-01-29T11:00:00Z');
      });

      const state = useAgentTeamStore.getState();
      expect(state.agentTeamStatus?.status).toBe('completed');
      expect(state.agentTeamStatus?.overallProgress).toBe(100);
      expect(state.agentTeamStatus?.completedAt).toBe('2026-01-29T11:00:00Z');
    });

    it('should handle failed team completion', () => {
      const mockStatus = createMockTeamStatus();

      act(() => {
        useAgentTeamStore.getState().setTeamStatus(mockStatus);
        useAgentTeamStore.getState().completeTeam('failed');
      });

      const state = useAgentTeamStore.getState();
      expect(state.agentTeamStatus?.status).toBe('failed');
      // Progress should not be forced to 100 on failure
    });
  });

  describe('Agent-level Actions', () => {
    it('should add agent to team', () => {
      const mockStatus = createMockTeamStatus();
      const newAgent = createMockAgent();

      act(() => {
        useAgentTeamStore.getState().setTeamStatus(mockStatus);
        useAgentTeamStore.getState().addAgent(newAgent);
      });

      const state = useAgentTeamStore.getState();
      expect(state.agentTeamStatus?.agents.length).toBe(3);
      expect(state.agentTeamStatus?.totalAgents).toBe(3);
    });

    it('should not add duplicate agent', () => {
      const mockStatus = createMockTeamStatus();
      const existingWorker = createMockAgent({ agentId: 'agent-1' });

      act(() => {
        useAgentTeamStore.getState().setTeamStatus(mockStatus);
        useAgentTeamStore.getState().addAgent(existingWorker);
      });

      expect(useAgentTeamStore.getState().agentTeamStatus?.agents.length).toBe(2);
    });

    it('should update agent progress', () => {
      const mockStatus = createMockTeamStatus();

      act(() => {
        useAgentTeamStore.getState().setTeamStatus(mockStatus);
        useAgentTeamStore.getState().updateAgentProgress({
          team_id: 'team-1',
          agent_id: 'agent-1',
          progress: 75,
          current_action: 'Processing...',
          status: 'running',
          updated_at: '2026-01-29T10:30:00Z',
        });
      });

      const state = useAgentTeamStore.getState();
      const agent = state.agentTeamStatus?.agents.find((w) => w.agentId === 'agent-1');
      expect(agent?.progress).toBe(75);
      expect(agent?.currentAction).toBe('Processing...');
    });

    it('should recalculate overall progress when agent progress updates', () => {
      const mockStatus = createMockTeamStatus({
        agents: [
          createMockAgent({ agentId: 'agent-1', progress: 0 }),
          createMockAgent({ agentId: 'agent-2', progress: 0 }),
        ],
      });

      act(() => {
        useAgentTeamStore.getState().setTeamStatus(mockStatus);
        useAgentTeamStore.getState().updateAgentProgress({
          team_id: 'team-1',
          agent_id: 'agent-1',
          progress: 100,
          status: 'completed',
          updated_at: '2026-01-29T10:30:00Z',
        });
      });

      // Overall should be 50% (100 + 0) / 2
      expect(useAgentTeamStore.getState().agentTeamStatus?.overallProgress).toBe(50);
    });

    it('should complete agent', () => {
      const mockStatus = createMockTeamStatus();

      act(() => {
        useAgentTeamStore.getState().setTeamStatus(mockStatus);
        useAgentTeamStore.getState().completeAgent({
          team_id: 'team-1',
          agent_id: 'agent-1',
          status: 'completed',
          result: { data: 'test result' },
          duration_ms: 5000,
          completed_at: '2026-01-29T10:30:00Z',
        });
      });

      const state = useAgentTeamStore.getState();
      const agent = state.agentTeamStatus?.agents.find((w) => w.agentId === 'agent-1');
      expect(agent?.status).toBe('completed');
      expect(agent?.progress).toBe(100);
      expect(agent?.completedAt).toBe('2026-01-29T10:30:00Z');
    });
  });

  describe('UI Actions', () => {
    it('should select agent', () => {
      const mockWorker = createMockAgent();

      act(() => {
        useAgentTeamStore.getState().selectAgent(mockWorker);
      });

      expect(useAgentTeamStore.getState().selectedAgentId).toBe('agent-new');
    });

    it('should clear selection when selecting null', () => {
      const mockWorker = createMockAgent();

      act(() => {
        useAgentTeamStore.getState().selectAgent(mockWorker);
        useAgentTeamStore.getState().selectAgent(null);
      });

      expect(useAgentTeamStore.getState().selectedAgentId).toBeNull();
    });

    it('should open drawer', () => {
      act(() => {
        useAgentTeamStore.getState().openDrawer();
      });

      expect(useAgentTeamStore.getState().isDrawerOpen).toBe(true);
    });

    it('should close drawer and clear selection', () => {
      const mockWorker = createMockAgent();

      act(() => {
        useAgentTeamStore.getState().selectAgent(mockWorker);
        useAgentTeamStore.getState().openDrawer();
        useAgentTeamStore.getState().closeDrawer();
      });

      const state = useAgentTeamStore.getState();
      expect(state.isDrawerOpen).toBe(false);
      expect(state.selectedAgentId).toBeNull();
      expect(state.selectedAgentDetail).toBeNull();
    });
  });

  describe('Utility Actions', () => {
    it('should set loading state', () => {
      act(() => {
        useAgentTeamStore.getState().setLoading(true);
      });

      expect(useAgentTeamStore.getState().isLoading).toBe(true);
    });

    it('should set error', () => {
      act(() => {
        useAgentTeamStore.getState().setError('Test error');
      });

      expect(useAgentTeamStore.getState().error).toBe('Test error');
    });

    it('should reset to initial state', () => {
      const mockStatus = createMockTeamStatus();

      act(() => {
        useAgentTeamStore.getState().setTeamStatus(mockStatus);
        useAgentTeamStore.getState().setLoading(true);
        useAgentTeamStore.getState().setError('error');
        useAgentTeamStore.getState().openDrawer();
        useAgentTeamStore.getState().reset();
      });

      const state = useAgentTeamStore.getState();
      expect(state.agentTeamStatus).toBeNull();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
      expect(state.isDrawerOpen).toBe(false);
    });
  });

  describe('Selectors', () => {
    it('should select team status', () => {
      const mockStatus = createMockTeamStatus();

      act(() => {
        useAgentTeamStore.getState().setTeamStatus(mockStatus);
      });

      expect(selectTeamStatus(useAgentTeamStore.getState())).toEqual(mockStatus);
    });

    it('should select agents', () => {
      const mockStatus = createMockTeamStatus();

      act(() => {
        useAgentTeamStore.getState().setTeamStatus(mockStatus);
      });

      const agents = selectAgents(useAgentTeamStore.getState());
      expect(agents.length).toBe(2);
    });

    it('should select completed agents', () => {
      const mockStatus = createMockTeamStatus({
        agents: [
          createMockAgent({ agentId: 'w1', status: 'completed' }),
          createMockAgent({ agentId: 'w2', status: 'running' }),
          createMockAgent({ agentId: 'w3', status: 'completed' }),
        ],
      });

      act(() => {
        useAgentTeamStore.getState().setTeamStatus(mockStatus);
      });

      expect(selectCompletedAgents(useAgentTeamStore.getState()).length).toBe(2);
    });

    it('should select running agents', () => {
      const mockStatus = createMockTeamStatus({
        agents: [
          createMockAgent({ agentId: 'w1', status: 'running' }),
          createMockAgent({ agentId: 'w2', status: 'pending' }),
        ],
      });

      act(() => {
        useAgentTeamStore.getState().setTeamStatus(mockStatus);
      });

      expect(selectRunningAgents(useAgentTeamStore.getState()).length).toBe(1);
    });

    it('should select failed agents', () => {
      const mockStatus = createMockTeamStatus({
        agents: [
          createMockAgent({ agentId: 'w1', status: 'failed' }),
          createMockAgent({ agentId: 'w2', status: 'completed' }),
        ],
      });

      act(() => {
        useAgentTeamStore.getState().setTeamStatus(mockStatus);
      });

      expect(selectFailedAgents(useAgentTeamStore.getState()).length).toBe(1);
    });

    it('should determine if team is active', () => {
      act(() => {
        useAgentTeamStore.getState().setTeamStatus(createMockTeamStatus({ status: 'executing' }));
      });

      expect(selectIsTeamActive(useAgentTeamStore.getState())).toBe(true);

      act(() => {
        useAgentTeamStore.getState().setTeamStatus(createMockTeamStatus({ status: 'completed' }));
      });

      expect(selectIsTeamActive(useAgentTeamStore.getState())).toBe(false);
    });
  });
});
