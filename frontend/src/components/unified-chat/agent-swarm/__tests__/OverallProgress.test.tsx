/**
 * OverallProgress Component Tests
 *
 * Sprint 102: AgentSwarmPanel + WorkerCard
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { OverallProgress } from '../OverallProgress';
import type { SwarmStatus } from '../types';

describe('OverallProgress', () => {
  const defaultProps = {
    progress: 65,
    status: 'executing' as SwarmStatus,
  };

  it('renders the progress percentage', () => {
    render(<OverallProgress {...defaultProps} />);
    expect(screen.getByText('65%')).toBeInTheDocument();
  });

  it('renders the overall progress label', () => {
    render(<OverallProgress {...defaultProps} />);
    expect(screen.getByText('Overall Progress')).toBeInTheDocument();
  });

  it('clamps progress to 0 when negative', () => {
    render(<OverallProgress {...defaultProps} progress={-10} />);
    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('clamps progress to 100 when over 100', () => {
    render(<OverallProgress {...defaultProps} progress={150} />);
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('renders with different statuses', () => {
    const statuses: SwarmStatus[] = [
      'initializing',
      'executing',
      'aggregating',
      'completed',
      'failed',
    ];

    statuses.forEach((status) => {
      const { container, unmount } = render(
        <OverallProgress {...defaultProps} status={status} />
      );
      expect(container.firstChild).toBeInTheDocument();
      unmount();
    });
  });

  it('applies animation when animated and executing', () => {
    const { container } = render(
      <OverallProgress {...defaultProps} animated={true} />
    );
    const progressBar = container.querySelector('.animate-pulse');
    expect(progressBar).toBeInTheDocument();
  });

  it('does not apply animation when animated is false', () => {
    const { container } = render(
      <OverallProgress {...defaultProps} animated={false} />
    );
    const progressBar = container.querySelector('.animate-pulse');
    expect(progressBar).not.toBeInTheDocument();
  });

  it('does not apply animation for completed status', () => {
    const { container } = render(
      <OverallProgress {...defaultProps} status="completed" animated={true} />
    );
    const progressBar = container.querySelector('.animate-pulse');
    expect(progressBar).not.toBeInTheDocument();
  });
});
