/**
 * AgentTeamPanel Component Tests
 *
 * Sprint 102: AgentTeamPanel + AgentCard
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AgentTeamPanel } from '../AgentTeamPanel';
import type { UIAgentTeamStatus, UIAgentSummary } from '../types';

describe('AgentTeamPanel', () => {
  const createAgent = (id: string, name: string): UIAgentSummary => ({
    agentId: id,
    agentName: name,
    agentType: 'claude_sdk',
    role: 'diagnostic',
    status: 'running',
    progress: 50,
    currentAction: 'Processing...',
    toolCallsCount: 2,
    createdAt: '2026-01-29T10:00:00Z',
    startedAt: '2026-01-29T10:01:00Z',
  });

  const createTeamStatus = (overrides: Partial<UIAgentTeamStatus> = {}): UIAgentTeamStatus => ({
    teamId: 'team-1',
    sessionId: 'session-1',
    mode: 'parallel',
    status: 'executing',
    totalAgents: 3,
    overallProgress: 50,
    agents: [
      createAgent('agent-1', 'Agent Alpha'),
      createAgent('agent-2', 'Agent Beta'),
      createAgent('agent-3', 'Agent Gamma'),
    ],
    createdAt: '2026-01-29T10:00:00Z',
    startedAt: '2026-01-29T10:00:30Z',
    metadata: {},
    ...overrides,
  });

  it('renders loading state when isLoading is true', () => {
    const { container } = render(
      <AgentTeamPanel agentTeamStatus={null} isLoading={true} />
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('renders empty state when agentTeamStatus is null', () => {
    render(<AgentTeamPanel agentTeamStatus={null} />);
    expect(screen.getByText('No active Agent Team')).toBeInTheDocument();
    expect(screen.getByText(/A team will appear/)).toBeInTheDocument();
  });

  it('renders team header with correct info', () => {
    render(<AgentTeamPanel agentTeamStatus={createTeamStatus()} />);
    expect(screen.getByText(/AGENT TEAM \(3 Workers\)/)).toBeInTheDocument();
    expect(screen.getByText('Parallel')).toBeInTheDocument();
    expect(screen.getByText('Executing')).toBeInTheDocument();
  });

  it('renders overall progress', () => {
    render(<AgentTeamPanel agentTeamStatus={createTeamStatus()} />);
    expect(screen.getByText('Overall Progress')).toBeInTheDocument();
    // Multiple elements have 50% (overall progress and agent cards)
    const progressTexts = screen.getAllByText('50%');
    expect(progressTexts.length).toBeGreaterThanOrEqual(1);
  });

  it('renders agent cards', () => {
    render(<AgentTeamPanel agentTeamStatus={createTeamStatus()} />);
    expect(screen.getByText('Agent Alpha')).toBeInTheDocument();
    expect(screen.getByText('Agent Beta')).toBeInTheDocument();
    expect(screen.getByText('Agent Gamma')).toBeInTheDocument();
  });

  it('calls onAgentClick when a agent is clicked', () => {
    const onAgentClick = vi.fn();
    const agentTeamStatus = createTeamStatus();

    render(
      <AgentTeamPanel agentTeamStatus={agentTeamStatus} onAgentClick={onAgentClick} />
    );

    fireEvent.click(screen.getByText('Agent Alpha').closest('.cursor-pointer')!);
    expect(onAgentClick).toHaveBeenCalledTimes(1);
    expect(onAgentClick).toHaveBeenCalledWith(agentTeamStatus.agents[0]);
  });

  it('applies custom className', () => {
    const { container } = render(
      <AgentTeamPanel
        agentTeamStatus={createTeamStatus()}
        className="custom-class"
      />
    );
    expect(container.querySelector('.custom-class')).toBeInTheDocument();
  });

  it('renders empty agent list message when no agents', () => {
    render(
      <AgentTeamPanel
        agentTeamStatus={createTeamStatus({ agents: [], totalAgents: 0 })}
      />
    );
    expect(screen.getByText('No agents assigned yet')).toBeInTheDocument();
  });

  it('renders different team statuses', () => {
    const statuses = ['initializing', 'executing', 'aggregating', 'completed', 'failed'] as const;
    const labels = ['Initializing', 'Executing', 'Aggregating', 'Completed', 'Failed'];

    statuses.forEach((status, index) => {
      const { unmount } = render(
        <AgentTeamPanel agentTeamStatus={createTeamStatus({ status })} />
      );
      expect(screen.getByText(labels[index])).toBeInTheDocument();
      unmount();
    });
  });

  it('renders different team modes', () => {
    const modes = ['sequential', 'parallel', 'pipeline', 'hierarchical', 'hybrid'] as const;
    const labels = ['Sequential', 'Parallel', 'Pipeline', 'Hierarchical', 'Hybrid'];

    modes.forEach((mode, index) => {
      const { unmount } = render(
        <AgentTeamPanel agentTeamStatus={createTeamStatus({ mode })} />
      );
      expect(screen.getByText(labels[index])).toBeInTheDocument();
      unmount();
    });
  });
});
