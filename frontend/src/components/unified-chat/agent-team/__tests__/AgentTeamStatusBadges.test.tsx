/**
 * AgentTeamStatusBadges Component Tests
 *
 * Sprint 102: AgentTeamPanel + AgentCard
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AgentTeamStatusBadges } from '../AgentTeamStatusBadges';
import type { UIAgentSummary, AgentMemberStatus } from '../types';

describe('AgentTeamStatusBadges', () => {
  const createAgent = (
    id: string,
    name: string,
    status: AgentMemberStatus = 'running'
  ): UIAgentSummary => ({
    agentId: id,
    agentName: name,
    agentType: 'claude_sdk',
    role: 'diagnostic',
    status,
    progress: 50,
    currentAction: 'Processing...',
    toolCallsCount: 2,
    createdAt: '2026-01-29T10:00:00Z',
    startedAt: '2026-01-29T10:01:00Z',
  });

  const agents: UIAgentSummary[] = [
    createAgent('agent-1', 'Agent Alpha', 'completed'),
    createAgent('agent-2', 'Agent Beta', 'running'),
    createAgent('agent-3', 'Agent Gamma', 'pending'),
  ];

  it('renders nothing when no agents', () => {
    const { container } = render(<AgentTeamStatusBadges agents={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders correct number of badges', () => {
    render(<AgentTeamStatusBadges agents={agents} />);
    const badges = screen.getAllByText(/0[1-3]/);
    expect(badges).toHaveLength(3);
  });

  it('renders index numbers (1-based, padded)', () => {
    render(<AgentTeamStatusBadges agents={agents} />);
    expect(screen.getByText('01')).toBeInTheDocument();
    expect(screen.getByText('02')).toBeInTheDocument();
    expect(screen.getByText('03')).toBeInTheDocument();
  });

  it('calls onAgentClick when badge is clicked', () => {
    const onAgentClick = vi.fn();
    render(<AgentTeamStatusBadges agents={agents} onAgentClick={onAgentClick} />);

    fireEvent.click(screen.getByText('01').closest('.cursor-pointer')!);
    expect(onAgentClick).toHaveBeenCalledTimes(1);
    expect(onAgentClick).toHaveBeenCalledWith(agents[0]);
  });

  it('renders badges for different statuses', () => {
    const allStatuses: AgentMemberStatus[] = ['pending', 'running', 'paused', 'completed', 'failed'];
    const workersWithStatuses = allStatuses.map((status, index) =>
      createAgent(`agent-${index}`, `Agent ${index}`, status)
    );

    const { container } = render(<AgentTeamStatusBadges agents={workersWithStatuses} />);
    const badges = container.querySelectorAll('.cursor-pointer');
    expect(badges).toHaveLength(5);
  });

  it('renders agent info in tooltip (basic structure check)', () => {
    // Note: Testing actual tooltip content requires more complex setup
    // This test just verifies the component renders without errors
    const { container } = render(<AgentTeamStatusBadges agents={agents} />);
    expect(container.firstChild).toBeInTheDocument();
  });
});
