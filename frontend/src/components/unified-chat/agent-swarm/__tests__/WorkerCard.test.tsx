/**
 * WorkerCard Component Tests
 *
 * Sprint 102: AgentSwarmPanel + WorkerCard
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { WorkerCard } from '../WorkerCard';
import type { UIWorkerSummary, WorkerType, WorkerStatus } from '../types';

describe('WorkerCard', () => {
  const createWorker = (overrides: Partial<UIWorkerSummary> = {}): UIWorkerSummary => ({
    workerId: 'worker-1',
    workerName: 'DiagnosticWorker',
    workerType: 'claude_sdk',
    role: 'diagnostic',
    status: 'running',
    progress: 50,
    currentAction: 'Analyzing logs...',
    toolCallsCount: 3,
    createdAt: '2026-01-29T10:00:00Z',
    startedAt: '2026-01-29T10:01:00Z',
    ...overrides,
  });

  const defaultProps = {
    worker: createWorker(),
    index: 0,
    isSelected: false,
    onClick: vi.fn(),
  };

  it('renders worker name', () => {
    render(<WorkerCard {...defaultProps} />);
    expect(screen.getByText('DiagnosticWorker')).toBeInTheDocument();
  });

  it('renders worker index (1-based, padded)', () => {
    render(<WorkerCard {...defaultProps} index={0} />);
    expect(screen.getByText('01')).toBeInTheDocument();
  });

  it('renders worker index correctly for larger numbers', () => {
    render(<WorkerCard {...defaultProps} index={9} />);
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('renders progress percentage', () => {
    render(<WorkerCard {...defaultProps} />);
    expect(screen.getByText('50%')).toBeInTheDocument();
  });

  it('renders tool calls count', () => {
    render(<WorkerCard {...defaultProps} />);
    expect(screen.getByText(/3 tools/)).toBeInTheDocument();
  });

  it('renders singular tool text for 1 tool', () => {
    render(
      <WorkerCard
        {...defaultProps}
        worker={createWorker({ toolCallsCount: 1 })}
      />
    );
    expect(screen.getByText(/1 tool/)).toBeInTheDocument();
  });

  it('renders current action when present', () => {
    render(<WorkerCard {...defaultProps} />);
    expect(screen.getByText(/Analyzing logs.../)).toBeInTheDocument();
  });

  it('does not render current action when absent', () => {
    render(
      <WorkerCard
        {...defaultProps}
        worker={createWorker({ currentAction: undefined })}
      />
    );
    expect(screen.queryByText(/└─/)).not.toBeInTheDocument();
  });

  it('renders worker type badge', () => {
    render(<WorkerCard {...defaultProps} />);
    expect(screen.getByText('Claude SDK')).toBeInTheDocument();
  });

  it('renders different worker types', () => {
    const types: WorkerType[] = ['claude_sdk', 'maf', 'hybrid', 'research', 'custom'];
    const labels = ['Claude SDK', 'MAF', 'Hybrid', 'Research', 'Custom'];

    types.forEach((workerType, index) => {
      const { unmount } = render(
        <WorkerCard
          {...defaultProps}
          worker={createWorker({ workerType })}
        />
      );
      expect(screen.getByText(labels[index])).toBeInTheDocument();
      unmount();
    });
  });

  it('renders role badge', () => {
    render(<WorkerCard {...defaultProps} />);
    expect(screen.getByText('diagnostic')).toBeInTheDocument();
  });

  it('calls onClick when card is clicked', () => {
    const onClick = vi.fn();
    render(<WorkerCard {...defaultProps} onClick={onClick} />);

    fireEvent.click(screen.getByText('DiagnosticWorker').closest('.cursor-pointer')!);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('calls onClick when View button is clicked', () => {
    const onClick = vi.fn();
    render(<WorkerCard {...defaultProps} onClick={onClick} />);

    fireEvent.click(screen.getByText('View'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('applies selected styles when isSelected is true', () => {
    const { container } = render(
      <WorkerCard {...defaultProps} isSelected={true} />
    );
    expect(container.querySelector('.ring-2')).toBeInTheDocument();
  });

  it('renders different statuses', () => {
    const statuses: WorkerStatus[] = ['pending', 'running', 'paused', 'completed', 'failed'];

    statuses.forEach((status) => {
      const { container, unmount } = render(
        <WorkerCard
          {...defaultProps}
          worker={createWorker({ status })}
        />
      );
      expect(container.firstChild).toBeInTheDocument();
      unmount();
    });
  });

  it('clamps progress to valid range', () => {
    render(
      <WorkerCard
        {...defaultProps}
        worker={createWorker({ progress: 150 })}
      />
    );
    expect(screen.getByText('100%')).toBeInTheDocument();
  });
});
