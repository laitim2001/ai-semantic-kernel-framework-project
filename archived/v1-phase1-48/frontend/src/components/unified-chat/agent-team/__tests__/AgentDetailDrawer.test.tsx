/**
 * AgentDetailDrawer Component Tests
 *
 * Sprint 103: AgentDetailDrawer
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AgentDetailDrawer } from '../AgentDetailDrawer';
import type { UIAgentSummary } from '../types';

// Mock useAgentDetail hook
vi.mock('../hooks/useAgentDetail', () => ({
  useAgentDetail: vi.fn(),
}));

import { useAgentDetail } from '../hooks/useAgentDetail';

describe('AgentDetailDrawer', () => {
  const mockWorker: UIAgentSummary = {
    agentId: 'agent-1',
    agentName: 'Test Agent',
    agentType: 'claude_sdk',
    role: 'diagnostic',
    status: 'running',
    progress: 50,
    currentAction: 'Processing...',
    toolCallsCount: 2,
    createdAt: '2026-01-29T10:00:00Z',
    startedAt: '2026-01-29T10:01:00Z',
  };

  const mockAgentDetail = {
    ...mockWorker,
    taskId: 'task-1',
    taskDescription: 'Test task description',
    thinkingHistory: [],
    toolCalls: [
      {
        toolCallId: 'tc-1',
        toolName: 'test_tool',
        status: 'completed' as const,
        inputArgs: { query: 'test' },
        outputResult: { result: 'success' },
        durationMs: 1000,
      },
    ],
    messages: [
      {
        role: 'assistant' as const,
        content: 'Test message',
        timestamp: '2026-01-29T10:02:00Z',
      },
    ],
  };

  const defaultProps = {
    open: true,
    onClose: vi.fn(),
    teamId: 'team-1',
    agent: mockWorker,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state', () => {
    (useAgentDetail as ReturnType<typeof vi.fn>).mockReturnValue({
      agent: null,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });

    render(<AgentDetailDrawer {...defaultProps} />);

    // Should show loading skeletons (Portal renders to document.body)
    const skeletons = document.body.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('renders error state', () => {
    (useAgentDetail as ReturnType<typeof vi.fn>).mockReturnValue({
      agent: null,
      isLoading: false,
      error: new Error('Test error'),
      refetch: vi.fn(),
    });

    render(<AgentDetailDrawer {...defaultProps} />);

    expect(screen.getByText('Failed to load agent details')).toBeInTheDocument();
    expect(screen.getByText('Test error')).toBeInTheDocument();
  });

  it('renders agent details when data is loaded', () => {
    (useAgentDetail as ReturnType<typeof vi.fn>).mockReturnValue({
      agent: mockAgentDetail,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<AgentDetailDrawer {...defaultProps} />);

    // Agent name
    expect(screen.getByText('Test Agent')).toBeInTheDocument();

    // Task description
    expect(screen.getByText('Test task description')).toBeInTheDocument();

    // Tool calls
    expect(screen.getByText('Tool Calls (1)')).toBeInTheDocument();
    expect(screen.getByText('test_tool')).toBeInTheDocument();

    // Messages
    expect(screen.getByText('Message History (1)')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    (useAgentDetail as ReturnType<typeof vi.fn>).mockReturnValue({
      agent: null,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<AgentDetailDrawer {...defaultProps} open={false} />);

    expect(screen.queryByText('Test Agent')).not.toBeInTheDocument();
  });

  it('calls useAgentDetail with correct parameters', () => {
    (useAgentDetail as ReturnType<typeof vi.fn>).mockReturnValue({
      agent: mockAgentDetail,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<AgentDetailDrawer {...defaultProps} />);

    expect(useAgentDetail).toHaveBeenCalledWith({
      teamId: 'team-1',
      agentId: 'agent-1',
      enabled: true,
      pollInterval: 2000, // running agent should poll
    });
  });

  it('does not poll for completed agent', () => {
    const completedWorker = { ...mockWorker, status: 'completed' as const };

    (useAgentDetail as ReturnType<typeof vi.fn>).mockReturnValue({
      agent: { ...mockAgentDetail, status: 'completed' },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <AgentDetailDrawer
        {...defaultProps}
        agent={completedWorker}
      />
    );

    expect(useAgentDetail).toHaveBeenCalledWith({
      teamId: 'team-1',
      agentId: 'agent-1',
      enabled: true,
      pollInterval: undefined, // completed agent should not poll
    });
  });
});
