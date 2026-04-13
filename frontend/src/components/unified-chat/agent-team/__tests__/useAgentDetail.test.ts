/**
 * useAgentDetail Hook Tests
 *
 * Sprint 103: AgentDetailDrawer
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useAgentDetail } from '../hooks/useAgentDetail';

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('useAgentDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const mockWorkerResponse = {
    agent_id: 'agent-1',
    agent_name: 'Test Agent',
    agent_type: 'claude_sdk',
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

  it('should fetch agent detail when enabled', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockWorkerResponse),
    });

    const { result } = renderHook(() =>
      useAgentDetail({
        teamId: 'team-1',
        agentId: 'agent-1',
        enabled: true,
      })
    );

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.agent).not.toBeNull();
    expect(result.current.agent?.agentId).toBe('agent-1');
    expect(result.current.agent?.agentName).toBe('Test Agent');
    expect(result.current.error).toBeNull();
  });

  it('should not fetch when disabled', () => {
    renderHook(() =>
      useAgentDetail({
        teamId: 'team-1',
        agentId: 'agent-1',
        enabled: false,
      })
    );

    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('should not fetch when teamId is empty', () => {
    renderHook(() =>
      useAgentDetail({
        teamId: '',
        agentId: 'agent-1',
        enabled: true,
      })
    );

    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('should not fetch when agentId is empty', () => {
    renderHook(() =>
      useAgentDetail({
        teamId: 'team-1',
        agentId: '',
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
      useAgentDetail({
        teamId: 'team-1',
        agentId: 'agent-1',
        enabled: true,
      })
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).not.toBeNull();
    expect(result.current.error?.message).toContain('Failed to fetch');
    expect(result.current.agent).toBeNull();
  });

  it('should transform snake_case to camelCase', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockWorkerResponse),
    });

    const { result } = renderHook(() =>
      useAgentDetail({
        teamId: 'team-1',
        agentId: 'agent-1',
        enabled: true,
      })
    );

    await waitFor(() => {
      expect(result.current.agent).not.toBeNull();
    });

    // Check camelCase conversion
    expect(result.current.agent?.agentId).toBe('agent-1');
    expect(result.current.agent?.agentName).toBe('Test Agent');
    expect(result.current.agent?.agentType).toBe('claude_sdk');
    expect(result.current.agent?.currentAction).toBe('Processing...');
    expect(result.current.agent?.toolCallsCount).toBe(2);
    expect(result.current.agent?.taskDescription).toBe('Test task description');
  });

  it('should call correct API endpoint', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockWorkerResponse),
    });

    renderHook(() =>
      useAgentDetail({
        teamId: 'team-123',
        agentId: 'agent-456',
        enabled: true,
      })
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/agent-team/team-123/agents/agent-456?include_thinking=true&include_messages=true'
    );
  });

  it('should provide refetch function', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockWorkerResponse),
    });

    const { result } = renderHook(() =>
      useAgentDetail({
        teamId: 'team-1',
        agentId: 'agent-1',
        enabled: true,
      })
    );

    await waitFor(() => {
      expect(result.current.agent).not.toBeNull();
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Manual refetch
    await result.current.refetch();

    expect(mockFetch).toHaveBeenCalledTimes(2);
  });
});
