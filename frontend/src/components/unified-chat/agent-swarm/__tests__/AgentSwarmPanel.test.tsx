/**
 * AgentSwarmPanel Component Tests
 *
 * Sprint 102: AgentSwarmPanel + WorkerCard
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AgentSwarmPanel } from '../AgentSwarmPanel';
import type { UIAgentSwarmStatus, UIWorkerSummary } from '../types';

describe('AgentSwarmPanel', () => {
  const createWorker = (id: string, name: string): UIWorkerSummary => ({
    workerId: id,
    workerName: name,
    workerType: 'claude_sdk',
    role: 'diagnostic',
    status: 'running',
    progress: 50,
    currentAction: 'Processing...',
    toolCallsCount: 2,
    createdAt: '2026-01-29T10:00:00Z',
    startedAt: '2026-01-29T10:01:00Z',
  });

  const createSwarmStatus = (overrides: Partial<UIAgentSwarmStatus> = {}): UIAgentSwarmStatus => ({
    swarmId: 'swarm-1',
    sessionId: 'session-1',
    mode: 'parallel',
    status: 'executing',
    totalWorkers: 3,
    overallProgress: 50,
    workers: [
      createWorker('worker-1', 'Worker Alpha'),
      createWorker('worker-2', 'Worker Beta'),
      createWorker('worker-3', 'Worker Gamma'),
    ],
    createdAt: '2026-01-29T10:00:00Z',
    startedAt: '2026-01-29T10:00:30Z',
    metadata: {},
    ...overrides,
  });

  it('renders loading state when isLoading is true', () => {
    const { container } = render(
      <AgentSwarmPanel swarmStatus={null} isLoading={true} />
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('renders empty state when swarmStatus is null', () => {
    render(<AgentSwarmPanel swarmStatus={null} />);
    expect(screen.getByText('No active Agent Swarm')).toBeInTheDocument();
    expect(screen.getByText(/A swarm will appear/)).toBeInTheDocument();
  });

  it('renders swarm header with correct info', () => {
    render(<AgentSwarmPanel swarmStatus={createSwarmStatus()} />);
    expect(screen.getByText(/AGENT SWARM \(3 Workers\)/)).toBeInTheDocument();
    expect(screen.getByText('Parallel')).toBeInTheDocument();
    expect(screen.getByText('Executing')).toBeInTheDocument();
  });

  it('renders overall progress', () => {
    render(<AgentSwarmPanel swarmStatus={createSwarmStatus()} />);
    expect(screen.getByText('Overall Progress')).toBeInTheDocument();
    // Multiple elements have 50% (overall progress and worker cards)
    const progressTexts = screen.getAllByText('50%');
    expect(progressTexts.length).toBeGreaterThanOrEqual(1);
  });

  it('renders worker cards', () => {
    render(<AgentSwarmPanel swarmStatus={createSwarmStatus()} />);
    expect(screen.getByText('Worker Alpha')).toBeInTheDocument();
    expect(screen.getByText('Worker Beta')).toBeInTheDocument();
    expect(screen.getByText('Worker Gamma')).toBeInTheDocument();
  });

  it('calls onWorkerClick when a worker is clicked', () => {
    const onWorkerClick = vi.fn();
    const swarmStatus = createSwarmStatus();

    render(
      <AgentSwarmPanel swarmStatus={swarmStatus} onWorkerClick={onWorkerClick} />
    );

    fireEvent.click(screen.getByText('Worker Alpha').closest('.cursor-pointer')!);
    expect(onWorkerClick).toHaveBeenCalledTimes(1);
    expect(onWorkerClick).toHaveBeenCalledWith(swarmStatus.workers[0]);
  });

  it('applies custom className', () => {
    const { container } = render(
      <AgentSwarmPanel
        swarmStatus={createSwarmStatus()}
        className="custom-class"
      />
    );
    expect(container.querySelector('.custom-class')).toBeInTheDocument();
  });

  it('renders empty worker list message when no workers', () => {
    render(
      <AgentSwarmPanel
        swarmStatus={createSwarmStatus({ workers: [], totalWorkers: 0 })}
      />
    );
    expect(screen.getByText('No workers assigned yet')).toBeInTheDocument();
  });

  it('renders different swarm statuses', () => {
    const statuses = ['initializing', 'executing', 'aggregating', 'completed', 'failed'] as const;
    const labels = ['Initializing', 'Executing', 'Aggregating', 'Completed', 'Failed'];

    statuses.forEach((status, index) => {
      const { unmount } = render(
        <AgentSwarmPanel swarmStatus={createSwarmStatus({ status })} />
      );
      expect(screen.getByText(labels[index])).toBeInTheDocument();
      unmount();
    });
  });

  it('renders different swarm modes', () => {
    const modes = ['sequential', 'parallel', 'pipeline', 'hierarchical', 'hybrid'] as const;
    const labels = ['Sequential', 'Parallel', 'Pipeline', 'Hierarchical', 'Hybrid'];

    modes.forEach((mode, index) => {
      const { unmount } = render(
        <AgentSwarmPanel swarmStatus={createSwarmStatus({ mode })} />
      );
      expect(screen.getByText(labels[index])).toBeInTheDocument();
      unmount();
    });
  });
});
