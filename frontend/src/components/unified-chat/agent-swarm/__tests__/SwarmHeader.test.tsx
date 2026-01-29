/**
 * SwarmHeader Component Tests
 *
 * Sprint 102: AgentSwarmPanel + WorkerCard
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SwarmHeader } from '../SwarmHeader';
import type { SwarmMode, SwarmStatus } from '../types';

describe('SwarmHeader', () => {
  const defaultProps = {
    mode: 'parallel' as SwarmMode,
    status: 'executing' as SwarmStatus,
    totalWorkers: 3,
    startedAt: '2026-01-29T10:30:00Z',
  };

  it('renders the swarm title with worker count', () => {
    render(<SwarmHeader {...defaultProps} />);
    expect(screen.getByText(/AGENT SWARM \(3 Workers\)/)).toBeInTheDocument();
  });

  it('renders singular worker text for 1 worker', () => {
    render(<SwarmHeader {...defaultProps} totalWorkers={1} />);
    expect(screen.getByText(/AGENT SWARM \(1 Worker\)/)).toBeInTheDocument();
  });

  it('displays the mode badge', () => {
    render(<SwarmHeader {...defaultProps} />);
    expect(screen.getByText('Parallel')).toBeInTheDocument();
  });

  it('displays the status label', () => {
    render(<SwarmHeader {...defaultProps} />);
    expect(screen.getByText('Executing')).toBeInTheDocument();
  });

  it('displays different status labels', () => {
    const statuses: SwarmStatus[] = [
      'initializing',
      'executing',
      'aggregating',
      'completed',
      'failed',
    ];

    const labels = ['Initializing', 'Executing', 'Aggregating', 'Completed', 'Failed'];

    statuses.forEach((status, index) => {
      const { unmount } = render(<SwarmHeader {...defaultProps} status={status} />);
      expect(screen.getByText(labels[index])).toBeInTheDocument();
      unmount();
    });
  });

  it('displays different mode labels', () => {
    const modes: SwarmMode[] = ['sequential', 'parallel', 'pipeline', 'hierarchical', 'hybrid'];
    const labels = ['Sequential', 'Parallel', 'Pipeline', 'Hierarchical', 'Hybrid'];

    modes.forEach((mode, index) => {
      const { unmount } = render(<SwarmHeader {...defaultProps} mode={mode} />);
      expect(screen.getByText(labels[index])).toBeInTheDocument();
      unmount();
    });
  });

  it('displays formatted start time', () => {
    render(<SwarmHeader {...defaultProps} />);
    expect(screen.getByText(/Started:/)).toBeInTheDocument();
  });

  it('handles missing startedAt gracefully', () => {
    render(<SwarmHeader {...defaultProps} startedAt={undefined} />);
    expect(screen.queryByText(/Started:/)).not.toBeInTheDocument();
  });

  it('handles invalid startedAt gracefully', () => {
    render(<SwarmHeader {...defaultProps} startedAt="invalid-date" />);
    expect(screen.getByText('Started: --:--:--')).toBeInTheDocument();
  });
});
