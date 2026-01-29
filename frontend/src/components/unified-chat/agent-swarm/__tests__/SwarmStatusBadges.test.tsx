/**
 * SwarmStatusBadges Component Tests
 *
 * Sprint 102: AgentSwarmPanel + WorkerCard
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SwarmStatusBadges } from '../SwarmStatusBadges';
import type { UIWorkerSummary, WorkerStatus } from '../types';

describe('SwarmStatusBadges', () => {
  const createWorker = (
    id: string,
    name: string,
    status: WorkerStatus = 'running'
  ): UIWorkerSummary => ({
    workerId: id,
    workerName: name,
    workerType: 'claude_sdk',
    role: 'diagnostic',
    status,
    progress: 50,
    currentAction: 'Processing...',
    toolCallsCount: 2,
    createdAt: '2026-01-29T10:00:00Z',
    startedAt: '2026-01-29T10:01:00Z',
  });

  const workers: UIWorkerSummary[] = [
    createWorker('worker-1', 'Worker Alpha', 'completed'),
    createWorker('worker-2', 'Worker Beta', 'running'),
    createWorker('worker-3', 'Worker Gamma', 'pending'),
  ];

  it('renders nothing when no workers', () => {
    const { container } = render(<SwarmStatusBadges workers={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders correct number of badges', () => {
    render(<SwarmStatusBadges workers={workers} />);
    const badges = screen.getAllByText(/0[1-3]/);
    expect(badges).toHaveLength(3);
  });

  it('renders index numbers (1-based, padded)', () => {
    render(<SwarmStatusBadges workers={workers} />);
    expect(screen.getByText('01')).toBeInTheDocument();
    expect(screen.getByText('02')).toBeInTheDocument();
    expect(screen.getByText('03')).toBeInTheDocument();
  });

  it('calls onWorkerClick when badge is clicked', () => {
    const onWorkerClick = vi.fn();
    render(<SwarmStatusBadges workers={workers} onWorkerClick={onWorkerClick} />);

    fireEvent.click(screen.getByText('01').closest('.cursor-pointer')!);
    expect(onWorkerClick).toHaveBeenCalledTimes(1);
    expect(onWorkerClick).toHaveBeenCalledWith(workers[0]);
  });

  it('renders badges for different statuses', () => {
    const allStatuses: WorkerStatus[] = ['pending', 'running', 'paused', 'completed', 'failed'];
    const workersWithStatuses = allStatuses.map((status, index) =>
      createWorker(`worker-${index}`, `Worker ${index}`, status)
    );

    const { container } = render(<SwarmStatusBadges workers={workersWithStatuses} />);
    const badges = container.querySelectorAll('.cursor-pointer');
    expect(badges).toHaveLength(5);
  });

  it('renders worker info in tooltip (basic structure check)', () => {
    // Note: Testing actual tooltip content requires more complex setup
    // This test just verifies the component renders without errors
    const { container } = render(<SwarmStatusBadges workers={workers} />);
    expect(container.firstChild).toBeInTheDocument();
  });
});
