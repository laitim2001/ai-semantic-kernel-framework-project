/**
 * WorkerCardList Component Tests
 *
 * Sprint 102: AgentSwarmPanel + WorkerCard
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { WorkerCardList } from '../WorkerCardList';
import type { UIWorkerSummary } from '../types';

describe('WorkerCardList', () => {
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

  const workers: UIWorkerSummary[] = [
    createWorker('worker-1', 'Worker Alpha'),
    createWorker('worker-2', 'Worker Beta'),
    createWorker('worker-3', 'Worker Gamma'),
  ];

  it('renders empty state when no workers', () => {
    render(<WorkerCardList workers={[]} />);
    expect(screen.getByText('No workers assigned yet')).toBeInTheDocument();
    expect(screen.getByText(/Workers will appear when the swarm starts/)).toBeInTheDocument();
  });

  it('renders all workers', () => {
    render(<WorkerCardList workers={workers} />);
    expect(screen.getByText('Worker Alpha')).toBeInTheDocument();
    expect(screen.getByText('Worker Beta')).toBeInTheDocument();
    expect(screen.getByText('Worker Gamma')).toBeInTheDocument();
  });

  it('calls onWorkerClick when a worker card is clicked', () => {
    const onWorkerClick = vi.fn();
    render(<WorkerCardList workers={workers} onWorkerClick={onWorkerClick} />);

    fireEvent.click(screen.getByText('Worker Alpha').closest('.cursor-pointer')!);
    expect(onWorkerClick).toHaveBeenCalledTimes(1);
    expect(onWorkerClick).toHaveBeenCalledWith(workers[0]);
  });

  it('passes selected state to correct worker card', () => {
    const { container } = render(
      <WorkerCardList workers={workers} selectedWorkerId="worker-2" />
    );
    const selectedCards = container.querySelectorAll('.ring-2');
    expect(selectedCards).toHaveLength(1);
  });

  it('renders workers in correct order', () => {
    render(<WorkerCardList workers={workers} />);

    const workerNames = screen.getAllByText(/Worker/);
    expect(workerNames[0]).toHaveTextContent('Worker Alpha');
    expect(workerNames[1]).toHaveTextContent('Worker Beta');
    expect(workerNames[2]).toHaveTextContent('Worker Gamma');
  });

  it('renders correct index numbers', () => {
    render(<WorkerCardList workers={workers} />);
    expect(screen.getByText('01')).toBeInTheDocument();
    expect(screen.getByText('02')).toBeInTheDocument();
    expect(screen.getByText('03')).toBeInTheDocument();
  });
});
