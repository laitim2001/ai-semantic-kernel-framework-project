/**
 * WorkerDetailDrawer Component Tests
 *
 * Sprint 103: WorkerDetailDrawer
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { WorkerDetailDrawer } from '../WorkerDetailDrawer';
import type { UIWorkerSummary } from '../types';

// Mock useWorkerDetail hook
vi.mock('../hooks/useWorkerDetail', () => ({
  useWorkerDetail: vi.fn(),
}));

import { useWorkerDetail } from '../hooks/useWorkerDetail';

describe('WorkerDetailDrawer', () => {
  const mockWorker: UIWorkerSummary = {
    workerId: 'worker-1',
    workerName: 'Test Worker',
    workerType: 'claude_sdk',
    role: 'diagnostic',
    status: 'running',
    progress: 50,
    currentAction: 'Processing...',
    toolCallsCount: 2,
    createdAt: '2026-01-29T10:00:00Z',
    startedAt: '2026-01-29T10:01:00Z',
  };

  const mockWorkerDetail = {
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
    swarmId: 'swarm-1',
    worker: mockWorker,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state', () => {
    (useWorkerDetail as ReturnType<typeof vi.fn>).mockReturnValue({
      worker: null,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });

    render(<WorkerDetailDrawer {...defaultProps} />);

    // Should show loading skeletons (Portal renders to document.body)
    const skeletons = document.body.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('renders error state', () => {
    (useWorkerDetail as ReturnType<typeof vi.fn>).mockReturnValue({
      worker: null,
      isLoading: false,
      error: new Error('Test error'),
      refetch: vi.fn(),
    });

    render(<WorkerDetailDrawer {...defaultProps} />);

    expect(screen.getByText('Failed to load worker details')).toBeInTheDocument();
    expect(screen.getByText('Test error')).toBeInTheDocument();
  });

  it('renders worker details when data is loaded', () => {
    (useWorkerDetail as ReturnType<typeof vi.fn>).mockReturnValue({
      worker: mockWorkerDetail,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<WorkerDetailDrawer {...defaultProps} />);

    // Worker name
    expect(screen.getByText('Test Worker')).toBeInTheDocument();

    // Task description
    expect(screen.getByText('Test task description')).toBeInTheDocument();

    // Tool calls
    expect(screen.getByText('Tool Calls (1)')).toBeInTheDocument();
    expect(screen.getByText('test_tool')).toBeInTheDocument();

    // Messages
    expect(screen.getByText('Message History (1)')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    (useWorkerDetail as ReturnType<typeof vi.fn>).mockReturnValue({
      worker: null,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<WorkerDetailDrawer {...defaultProps} open={false} />);

    expect(screen.queryByText('Test Worker')).not.toBeInTheDocument();
  });

  it('calls useWorkerDetail with correct parameters', () => {
    (useWorkerDetail as ReturnType<typeof vi.fn>).mockReturnValue({
      worker: mockWorkerDetail,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<WorkerDetailDrawer {...defaultProps} />);

    expect(useWorkerDetail).toHaveBeenCalledWith({
      swarmId: 'swarm-1',
      workerId: 'worker-1',
      enabled: true,
      pollInterval: 2000, // running worker should poll
    });
  });

  it('does not poll for completed worker', () => {
    const completedWorker = { ...mockWorker, status: 'completed' as const };

    (useWorkerDetail as ReturnType<typeof vi.fn>).mockReturnValue({
      worker: { ...mockWorkerDetail, status: 'completed' },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <WorkerDetailDrawer
        {...defaultProps}
        worker={completedWorker}
      />
    );

    expect(useWorkerDetail).toHaveBeenCalledWith({
      swarmId: 'swarm-1',
      workerId: 'worker-1',
      enabled: true,
      pollInterval: undefined, // completed worker should not poll
    });
  });
});
