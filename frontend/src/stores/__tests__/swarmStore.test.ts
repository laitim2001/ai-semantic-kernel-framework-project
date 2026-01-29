/**
 * SwarmStore Test Suite
 *
 * Tests for the Agent Swarm Zustand store.
 * Sprint 105: OrchestrationPanel 整合 + 狀態管理
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { act } from '@testing-library/react';
import {
  useSwarmStore,
  selectSwarmStatus,
  selectWorkers,
  selectCompletedWorkers,
  selectRunningWorkers,
  selectFailedWorkers,
  selectIsSwarmActive,
} from '../swarmStore';
import type { UIAgentSwarmStatus, UIWorkerSummary } from '@/components/unified-chat/agent-swarm/types';

// =============================================================================
// Test Fixtures
// =============================================================================

const createMockSwarmStatus = (overrides?: Partial<UIAgentSwarmStatus>): UIAgentSwarmStatus => ({
  swarmId: 'swarm-1',
  sessionId: 'session-1',
  mode: 'parallel',
  status: 'executing',
  totalWorkers: 2,
  overallProgress: 50,
  workers: [
    {
      workerId: 'worker-1',
      workerName: 'Research Agent',
      workerType: 'research',
      role: 'Data Gatherer',
      status: 'running',
      progress: 50,
      currentAction: 'Searching...',
      toolCallsCount: 3,
      createdAt: '2026-01-29T10:00:00Z',
      startedAt: '2026-01-29T10:00:00Z',
    },
    {
      workerId: 'worker-2',
      workerName: 'Writer Agent',
      workerType: 'custom',
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

const createMockWorker = (overrides?: Partial<UIWorkerSummary>): UIWorkerSummary => ({
  workerId: 'worker-new',
  workerName: 'New Worker',
  workerType: 'custom',
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

describe('SwarmStore', () => {
  // Reset store before each test
  beforeEach(() => {
    act(() => {
      useSwarmStore.getState().reset();
    });
  });

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      const state = useSwarmStore.getState();

      expect(state.swarmStatus).toBeNull();
      expect(state.selectedWorkerId).toBeNull();
      expect(state.selectedWorkerDetail).toBeNull();
      expect(state.isDrawerOpen).toBe(false);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });
  });

  describe('Swarm-level Actions', () => {
    it('should set swarm status', () => {
      const mockStatus = createMockSwarmStatus();

      act(() => {
        useSwarmStore.getState().setSwarmStatus(mockStatus);
      });

      const state = useSwarmStore.getState();
      expect(state.swarmStatus).toEqual(mockStatus);
      expect(state.swarmStatus?.swarmId).toBe('swarm-1');
    });

    it('should clear swarm status when set to null', () => {
      const mockStatus = createMockSwarmStatus();

      act(() => {
        useSwarmStore.getState().setSwarmStatus(mockStatus);
        useSwarmStore.getState().setSwarmStatus(null);
      });

      expect(useSwarmStore.getState().swarmStatus).toBeNull();
    });

    it('should update swarm progress', () => {
      const mockStatus = createMockSwarmStatus();

      act(() => {
        useSwarmStore.getState().setSwarmStatus(mockStatus);
        useSwarmStore.getState().updateSwarmProgress(75);
      });

      expect(useSwarmStore.getState().swarmStatus?.overallProgress).toBe(75);
    });

    it('should complete swarm', () => {
      const mockStatus = createMockSwarmStatus();

      act(() => {
        useSwarmStore.getState().setSwarmStatus(mockStatus);
        useSwarmStore.getState().completeSwarm('completed', '2026-01-29T11:00:00Z');
      });

      const state = useSwarmStore.getState();
      expect(state.swarmStatus?.status).toBe('completed');
      expect(state.swarmStatus?.overallProgress).toBe(100);
      expect(state.swarmStatus?.completedAt).toBe('2026-01-29T11:00:00Z');
    });

    it('should handle failed swarm completion', () => {
      const mockStatus = createMockSwarmStatus();

      act(() => {
        useSwarmStore.getState().setSwarmStatus(mockStatus);
        useSwarmStore.getState().completeSwarm('failed');
      });

      const state = useSwarmStore.getState();
      expect(state.swarmStatus?.status).toBe('failed');
      // Progress should not be forced to 100 on failure
    });
  });

  describe('Worker-level Actions', () => {
    it('should add worker to swarm', () => {
      const mockStatus = createMockSwarmStatus();
      const newWorker = createMockWorker();

      act(() => {
        useSwarmStore.getState().setSwarmStatus(mockStatus);
        useSwarmStore.getState().addWorker(newWorker);
      });

      const state = useSwarmStore.getState();
      expect(state.swarmStatus?.workers.length).toBe(3);
      expect(state.swarmStatus?.totalWorkers).toBe(3);
    });

    it('should not add duplicate worker', () => {
      const mockStatus = createMockSwarmStatus();
      const existingWorker = createMockWorker({ workerId: 'worker-1' });

      act(() => {
        useSwarmStore.getState().setSwarmStatus(mockStatus);
        useSwarmStore.getState().addWorker(existingWorker);
      });

      expect(useSwarmStore.getState().swarmStatus?.workers.length).toBe(2);
    });

    it('should update worker progress', () => {
      const mockStatus = createMockSwarmStatus();

      act(() => {
        useSwarmStore.getState().setSwarmStatus(mockStatus);
        useSwarmStore.getState().updateWorkerProgress({
          swarm_id: 'swarm-1',
          worker_id: 'worker-1',
          progress: 75,
          current_action: 'Processing...',
          status: 'running',
          updated_at: '2026-01-29T10:30:00Z',
        });
      });

      const state = useSwarmStore.getState();
      const worker = state.swarmStatus?.workers.find((w) => w.workerId === 'worker-1');
      expect(worker?.progress).toBe(75);
      expect(worker?.currentAction).toBe('Processing...');
    });

    it('should recalculate overall progress when worker progress updates', () => {
      const mockStatus = createMockSwarmStatus({
        workers: [
          createMockWorker({ workerId: 'worker-1', progress: 0 }),
          createMockWorker({ workerId: 'worker-2', progress: 0 }),
        ],
      });

      act(() => {
        useSwarmStore.getState().setSwarmStatus(mockStatus);
        useSwarmStore.getState().updateWorkerProgress({
          swarm_id: 'swarm-1',
          worker_id: 'worker-1',
          progress: 100,
          status: 'completed',
          updated_at: '2026-01-29T10:30:00Z',
        });
      });

      // Overall should be 50% (100 + 0) / 2
      expect(useSwarmStore.getState().swarmStatus?.overallProgress).toBe(50);
    });

    it('should complete worker', () => {
      const mockStatus = createMockSwarmStatus();

      act(() => {
        useSwarmStore.getState().setSwarmStatus(mockStatus);
        useSwarmStore.getState().completeWorker({
          swarm_id: 'swarm-1',
          worker_id: 'worker-1',
          status: 'completed',
          result: { data: 'test result' },
          duration_ms: 5000,
          completed_at: '2026-01-29T10:30:00Z',
        });
      });

      const state = useSwarmStore.getState();
      const worker = state.swarmStatus?.workers.find((w) => w.workerId === 'worker-1');
      expect(worker?.status).toBe('completed');
      expect(worker?.progress).toBe(100);
      expect(worker?.completedAt).toBe('2026-01-29T10:30:00Z');
    });
  });

  describe('UI Actions', () => {
    it('should select worker', () => {
      const mockWorker = createMockWorker();

      act(() => {
        useSwarmStore.getState().selectWorker(mockWorker);
      });

      expect(useSwarmStore.getState().selectedWorkerId).toBe('worker-new');
    });

    it('should clear selection when selecting null', () => {
      const mockWorker = createMockWorker();

      act(() => {
        useSwarmStore.getState().selectWorker(mockWorker);
        useSwarmStore.getState().selectWorker(null);
      });

      expect(useSwarmStore.getState().selectedWorkerId).toBeNull();
    });

    it('should open drawer', () => {
      act(() => {
        useSwarmStore.getState().openDrawer();
      });

      expect(useSwarmStore.getState().isDrawerOpen).toBe(true);
    });

    it('should close drawer and clear selection', () => {
      const mockWorker = createMockWorker();

      act(() => {
        useSwarmStore.getState().selectWorker(mockWorker);
        useSwarmStore.getState().openDrawer();
        useSwarmStore.getState().closeDrawer();
      });

      const state = useSwarmStore.getState();
      expect(state.isDrawerOpen).toBe(false);
      expect(state.selectedWorkerId).toBeNull();
      expect(state.selectedWorkerDetail).toBeNull();
    });
  });

  describe('Utility Actions', () => {
    it('should set loading state', () => {
      act(() => {
        useSwarmStore.getState().setLoading(true);
      });

      expect(useSwarmStore.getState().isLoading).toBe(true);
    });

    it('should set error', () => {
      act(() => {
        useSwarmStore.getState().setError('Test error');
      });

      expect(useSwarmStore.getState().error).toBe('Test error');
    });

    it('should reset to initial state', () => {
      const mockStatus = createMockSwarmStatus();

      act(() => {
        useSwarmStore.getState().setSwarmStatus(mockStatus);
        useSwarmStore.getState().setLoading(true);
        useSwarmStore.getState().setError('error');
        useSwarmStore.getState().openDrawer();
        useSwarmStore.getState().reset();
      });

      const state = useSwarmStore.getState();
      expect(state.swarmStatus).toBeNull();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
      expect(state.isDrawerOpen).toBe(false);
    });
  });

  describe('Selectors', () => {
    it('should select swarm status', () => {
      const mockStatus = createMockSwarmStatus();

      act(() => {
        useSwarmStore.getState().setSwarmStatus(mockStatus);
      });

      expect(selectSwarmStatus(useSwarmStore.getState())).toEqual(mockStatus);
    });

    it('should select workers', () => {
      const mockStatus = createMockSwarmStatus();

      act(() => {
        useSwarmStore.getState().setSwarmStatus(mockStatus);
      });

      const workers = selectWorkers(useSwarmStore.getState());
      expect(workers.length).toBe(2);
    });

    it('should select completed workers', () => {
      const mockStatus = createMockSwarmStatus({
        workers: [
          createMockWorker({ workerId: 'w1', status: 'completed' }),
          createMockWorker({ workerId: 'w2', status: 'running' }),
          createMockWorker({ workerId: 'w3', status: 'completed' }),
        ],
      });

      act(() => {
        useSwarmStore.getState().setSwarmStatus(mockStatus);
      });

      expect(selectCompletedWorkers(useSwarmStore.getState()).length).toBe(2);
    });

    it('should select running workers', () => {
      const mockStatus = createMockSwarmStatus({
        workers: [
          createMockWorker({ workerId: 'w1', status: 'running' }),
          createMockWorker({ workerId: 'w2', status: 'pending' }),
        ],
      });

      act(() => {
        useSwarmStore.getState().setSwarmStatus(mockStatus);
      });

      expect(selectRunningWorkers(useSwarmStore.getState()).length).toBe(1);
    });

    it('should select failed workers', () => {
      const mockStatus = createMockSwarmStatus({
        workers: [
          createMockWorker({ workerId: 'w1', status: 'failed' }),
          createMockWorker({ workerId: 'w2', status: 'completed' }),
        ],
      });

      act(() => {
        useSwarmStore.getState().setSwarmStatus(mockStatus);
      });

      expect(selectFailedWorkers(useSwarmStore.getState()).length).toBe(1);
    });

    it('should determine if swarm is active', () => {
      act(() => {
        useSwarmStore.getState().setSwarmStatus(createMockSwarmStatus({ status: 'executing' }));
      });

      expect(selectIsSwarmActive(useSwarmStore.getState())).toBe(true);

      act(() => {
        useSwarmStore.getState().setSwarmStatus(createMockSwarmStatus({ status: 'completed' }));
      });

      expect(selectIsSwarmActive(useSwarmStore.getState())).toBe(false);
    });
  });
});
