/**
 * useWorkerDetail Hook Tests
 *
 * Sprint 103: WorkerDetailDrawer
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useWorkerDetail } from '../hooks/useWorkerDetail';

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('useWorkerDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const mockWorkerResponse = {
    worker_id: 'worker-1',
    worker_name: 'Test Worker',
    worker_type: 'claude_sdk',
    role: 'diagnostic',
    status: 'running',
    progress: 50,
    current_action: 'Processing...',
    tool_calls_count: 2,
    created_at: '2026-01-29T10:00:00Z',
    started_at: '2026-01-29T10:01:00Z',
    task_id: 'task-1',
    task_description: 'Test task description',
    thinking_history: [],
    tool_calls: [],
    messages: [],
  };

  it('should fetch worker detail when enabled', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockWorkerResponse),
    });

    const { result } = renderHook(() =>
      useWorkerDetail({
        swarmId: 'swarm-1',
        workerId: 'worker-1',
        enabled: true,
      })
    );

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.worker).not.toBeNull();
    expect(result.current.worker?.workerId).toBe('worker-1');
    expect(result.current.worker?.workerName).toBe('Test Worker');
    expect(result.current.error).toBeNull();
  });

  it('should not fetch when disabled', () => {
    renderHook(() =>
      useWorkerDetail({
        swarmId: 'swarm-1',
        workerId: 'worker-1',
        enabled: false,
      })
    );

    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('should not fetch when swarmId is empty', () => {
    renderHook(() =>
      useWorkerDetail({
        swarmId: '',
        workerId: 'worker-1',
        enabled: true,
      })
    );

    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('should not fetch when workerId is empty', () => {
    renderHook(() =>
      useWorkerDetail({
        swarmId: 'swarm-1',
        workerId: '',
        enabled: true,
      })
    );

    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('should handle fetch error', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      statusText: 'Not Found',
    });

    const { result } = renderHook(() =>
      useWorkerDetail({
        swarmId: 'swarm-1',
        workerId: 'worker-1',
        enabled: true,
      })
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).not.toBeNull();
    expect(result.current.error?.message).toContain('Failed to fetch');
    expect(result.current.worker).toBeNull();
  });

  it('should transform snake_case to camelCase', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockWorkerResponse),
    });

    const { result } = renderHook(() =>
      useWorkerDetail({
        swarmId: 'swarm-1',
        workerId: 'worker-1',
        enabled: true,
      })
    );

    await waitFor(() => {
      expect(result.current.worker).not.toBeNull();
    });

    // Check camelCase conversion
    expect(result.current.worker?.workerId).toBe('worker-1');
    expect(result.current.worker?.workerName).toBe('Test Worker');
    expect(result.current.worker?.workerType).toBe('claude_sdk');
    expect(result.current.worker?.currentAction).toBe('Processing...');
    expect(result.current.worker?.toolCallsCount).toBe(2);
    expect(result.current.worker?.taskDescription).toBe('Test task description');
  });

  it('should call correct API endpoint', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockWorkerResponse),
    });

    renderHook(() =>
      useWorkerDetail({
        swarmId: 'swarm-123',
        workerId: 'worker-456',
        enabled: true,
      })
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/swarm/swarm-123/workers/worker-456?include_thinking=true&include_messages=true'
    );
  });

  it('should provide refetch function', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockWorkerResponse),
    });

    const { result } = renderHook(() =>
      useWorkerDetail({
        swarmId: 'swarm-1',
        workerId: 'worker-1',
        enabled: true,
      })
    );

    await waitFor(() => {
      expect(result.current.worker).not.toBeNull();
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Manual refetch
    await result.current.refetch();

    expect(mockFetch).toHaveBeenCalledTimes(2);
  });
});
