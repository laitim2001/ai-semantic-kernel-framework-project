/**
 * AgentCardList Component Tests
 *
 * Sprint 102: AgentTeamPanel + AgentCard
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AgentCardList } from '../AgentCardList';
import type { UIAgentSummary } from '../types';

describe('AgentCardList', () => {
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

  const agents: UIAgentSummary[] = [
    createAgent('agent-1', 'Agent Alpha'),
    createAgent('agent-2', 'Agent Beta'),
    createAgent('agent-3', 'Agent Gamma'),
  ];

  it('renders empty state when no agents', () => {
    render(<AgentCardList agents={[]} />);
    expect(screen.getByText('No agents assigned yet')).toBeInTheDocument();
    expect(screen.getByText(/Agents will appear when the team starts/)).toBeInTheDocument();
  });

  it('renders all agents', () => {
    render(<AgentCardList agents={agents} />);
    expect(screen.getByText('Agent Alpha')).toBeInTheDocument();
    expect(screen.getByText('Agent Beta')).toBeInTheDocument();
    expect(screen.getByText('Agent Gamma')).toBeInTheDocument();
  });

  it('calls onAgentClick when a agent card is clicked', () => {
    const onAgentClick = vi.fn();
    render(<AgentCardList agents={agents} onAgentClick={onAgentClick} />);

    fireEvent.click(screen.getByText('Agent Alpha').closest('.cursor-pointer')!);
    expect(onAgentClick).toHaveBeenCalledTimes(1);
    expect(onAgentClick).toHaveBeenCalledWith(agents[0]);
  });

  it('passes selected state to correct agent card', () => {
    const { container } = render(
      <AgentCardList agents={agents} selectedAgentId="agent-2" />
    );
    const selectedCards = container.querySelectorAll('.ring-2');
    expect(selectedCards).toHaveLength(1);
  });

  it('renders agents in correct order', () => {
    render(<AgentCardList agents={agents} />);

    const agentNames = screen.getAllByText(/Agent/);
    expect(agentNames[0]).toHaveTextContent('Agent Alpha');
    expect(agentNames[1]).toHaveTextContent('Agent Beta');
    expect(agentNames[2]).toHaveTextContent('Agent Gamma');
  });

  it('renders correct index numbers', () => {
    render(<AgentCardList agents={agents} />);
    expect(screen.getByText('01')).toBeInTheDocument();
    expect(screen.getByText('02')).toBeInTheDocument();
    expect(screen.getByText('03')).toBeInTheDocument();
  });
});
