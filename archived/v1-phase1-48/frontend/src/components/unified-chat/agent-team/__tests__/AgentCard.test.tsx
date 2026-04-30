/**
 * AgentCard Component Tests
 *
 * Sprint 102: AgentTeamPanel + AgentCard
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AgentCard } from '../AgentCard';
import type { UIAgentSummary, AgentType, AgentMemberStatus } from '../types';

describe('AgentCard', () => {
  const createWorker = (overrides: Partial<UIAgentSummary> = {}): UIAgentSummary => ({
    agentId: 'agent-1',
    agentName: 'DiagnosticWorker',
    agentType: 'claude_sdk',
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
    agent: createWorker(),
    index: 0,
    isSelected: false,
    onClick: vi.fn(),
  };

  it('renders agent name', () => {
    render(<AgentCard {...defaultProps} />);
    expect(screen.getByText('DiagnosticWorker')).toBeInTheDocument();
  });

  it('renders agent index (1-based, padded)', () => {
    render(<AgentCard {...defaultProps} index={0} />);
    expect(screen.getByText('01')).toBeInTheDocument();
  });

  it('renders agent index correctly for larger numbers', () => {
    render(<AgentCard {...defaultProps} index={9} />);
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('renders progress percentage', () => {
    render(<AgentCard {...defaultProps} />);
    expect(screen.getByText('50%')).toBeInTheDocument();
  });

  it('renders tool calls count', () => {
    render(<AgentCard {...defaultProps} />);
    expect(screen.getByText(/3 tools/)).toBeInTheDocument();
  });

  it('renders singular tool text for 1 tool', () => {
    render(
      <AgentCard
        {...defaultProps}
        agent={createWorker({ toolCallsCount: 1 })}
      />
    );
    expect(screen.getByText(/1 tool/)).toBeInTheDocument();
  });

  it('renders current action when present', () => {
    render(<AgentCard {...defaultProps} />);
    expect(screen.getByText(/Analyzing logs.../)).toBeInTheDocument();
  });

  it('does not render current action when absent', () => {
    render(
      <AgentCard
        {...defaultProps}
        agent={createWorker({ currentAction: undefined })}
      />
    );
    expect(screen.queryByText(/└─/)).not.toBeInTheDocument();
  });

  it('renders agent type badge', () => {
    render(<AgentCard {...defaultProps} />);
    expect(screen.getByText('Claude SDK')).toBeInTheDocument();
  });

  it('renders different agent types', () => {
    const types: AgentType[] = ['claude_sdk', 'maf', 'hybrid', 'research', 'custom'];
    const labels = ['Claude SDK', 'MAF', 'Hybrid', 'Research', 'Custom'];

    types.forEach((agentType, index) => {
      const { unmount } = render(
        <AgentCard
          {...defaultProps}
          agent={createWorker({ agentType })}
        />
      );
      expect(screen.getByText(labels[index])).toBeInTheDocument();
      unmount();
    });
  });

  it('renders role badge', () => {
    render(<AgentCard {...defaultProps} />);
    expect(screen.getByText('diagnostic')).toBeInTheDocument();
  });

  it('calls onClick when card is clicked', () => {
    const onClick = vi.fn();
    render(<AgentCard {...defaultProps} onClick={onClick} />);

    fireEvent.click(screen.getByText('DiagnosticWorker').closest('.cursor-pointer')!);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('calls onClick when View button is clicked', () => {
    const onClick = vi.fn();
    render(<AgentCard {...defaultProps} onClick={onClick} />);

    fireEvent.click(screen.getByText('View'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('applies selected styles when isSelected is true', () => {
    const { container } = render(
      <AgentCard {...defaultProps} isSelected={true} />
    );
    expect(container.querySelector('.ring-2')).toBeInTheDocument();
  });

  it('renders different statuses', () => {
    const statuses: AgentMemberStatus[] = ['pending', 'running', 'paused', 'completed', 'failed'];

    statuses.forEach((status) => {
      const { container, unmount } = render(
        <AgentCard
          {...defaultProps}
          agent={createWorker({ status })}
        />
      );
      expect(container.firstChild).toBeInTheDocument();
      unmount();
    });
  });

  it('clamps progress to valid range', () => {
    render(
      <AgentCard
        {...defaultProps}
        agent={createWorker({ progress: 150 })}
      />
    );
    expect(screen.getByText('100%')).toBeInTheDocument();
  });
});
