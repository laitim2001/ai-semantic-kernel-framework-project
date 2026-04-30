/**
 * AgentTeamHeader Component Tests
 *
 * Sprint 102: AgentTeamPanel + AgentCard
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AgentTeamHeader } from '../AgentTeamHeader';
import type { TeamMode, TeamStatus } from '../types';

describe('AgentTeamHeader', () => {
  const defaultProps = {
    mode: 'parallel' as TeamMode,
    status: 'executing' as TeamStatus,
    totalAgents: 3,
    startedAt: '2026-01-29T10:30:00Z',
  };

  it('renders the team title with agent count', () => {
    render(<AgentTeamHeader {...defaultProps} />);
    expect(screen.getByText(/AGENT TEAM \(3 Workers\)/)).toBeInTheDocument();
  });

  it('renders singular agent text for 1 agent', () => {
    render(<AgentTeamHeader {...defaultProps} totalAgents={1} />);
    expect(screen.getByText(/AGENT TEAM \(1 Agent\)/)).toBeInTheDocument();
  });

  it('displays the mode badge', () => {
    render(<AgentTeamHeader {...defaultProps} />);
    expect(screen.getByText('Parallel')).toBeInTheDocument();
  });

  it('displays the status label', () => {
    render(<AgentTeamHeader {...defaultProps} />);
    expect(screen.getByText('Executing')).toBeInTheDocument();
  });

  it('displays different status labels', () => {
    const statuses: TeamStatus[] = [
      'initializing',
      'executing',
      'aggregating',
      'completed',
      'failed',
    ];

    const labels = ['Initializing', 'Executing', 'Aggregating', 'Completed', 'Failed'];

    statuses.forEach((status, index) => {
      const { unmount } = render(<AgentTeamHeader {...defaultProps} status={status} />);
      expect(screen.getByText(labels[index])).toBeInTheDocument();
      unmount();
    });
  });

  it('displays different mode labels', () => {
    const modes: TeamMode[] = ['sequential', 'parallel', 'pipeline', 'hierarchical', 'hybrid'];
    const labels = ['Sequential', 'Parallel', 'Pipeline', 'Hierarchical', 'Hybrid'];

    modes.forEach((mode, index) => {
      const { unmount } = render(<AgentTeamHeader {...defaultProps} mode={mode} />);
      expect(screen.getByText(labels[index])).toBeInTheDocument();
      unmount();
    });
  });

  it('displays formatted start time', () => {
    render(<AgentTeamHeader {...defaultProps} />);
    expect(screen.getByText(/Started:/)).toBeInTheDocument();
  });

  it('handles missing startedAt gracefully', () => {
    render(<AgentTeamHeader {...defaultProps} startedAt={undefined} />);
    expect(screen.queryByText(/Started:/)).not.toBeInTheDocument();
  });

  it('handles invalid startedAt gracefully', () => {
    render(<AgentTeamHeader {...defaultProps} startedAt="invalid-date" />);
    expect(screen.getByText('Started: --:--:--')).toBeInTheDocument();
  });
});
