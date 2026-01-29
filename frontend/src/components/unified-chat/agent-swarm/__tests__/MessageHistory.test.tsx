/**
 * MessageHistory Component Tests
 *
 * Sprint 103: WorkerDetailDrawer
 */

import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MessageHistory } from '../MessageHistory';
import type { WorkerMessage } from '../types';

describe('MessageHistory', () => {
  const createMessage = (
    role: WorkerMessage['role'],
    content: string,
    overrides: Partial<WorkerMessage> = {}
  ): WorkerMessage => ({
    role,
    content,
    timestamp: '2026-01-29T10:00:00Z',
    ...overrides,
  });

  const sampleMessages: WorkerMessage[] = [
    createMessage('system', 'You are a helpful assistant.'),
    createMessage('user', 'Please help me analyze this data.'),
    createMessage('assistant', 'I will analyze the data now.'),
    createMessage('tool', 'Tool result: Success', { toolCallId: 'tc-1' }),
  ];

  it('renders message count', () => {
    render(<MessageHistory messages={sampleMessages} />);
    expect(screen.getByText('Message History (4)')).toBeInTheDocument();
  });

  it('shows empty state when no messages', () => {
    render(<MessageHistory messages={[]} defaultExpanded={true} />);
    expect(screen.getByText('No messages yet')).toBeInTheDocument();
  });

  it('expands to show messages on click', () => {
    render(<MessageHistory messages={sampleMessages} />);

    // Initially collapsed
    expect(screen.queryByText('You are a helpful assistant.')).not.toBeInTheDocument();

    // Click to expand
    fireEvent.click(screen.getByText('Message History (4)'));

    // Should show messages
    expect(screen.getByText('You are a helpful assistant.')).toBeInTheDocument();
    expect(screen.getByText('Please help me analyze this data.')).toBeInTheDocument();
  });

  it('displays role badges', () => {
    render(<MessageHistory messages={sampleMessages} defaultExpanded={true} />);

    expect(screen.getByText('System')).toBeInTheDocument();
    expect(screen.getByText('User')).toBeInTheDocument();
    expect(screen.getByText('Assistant')).toBeInTheDocument();
    expect(screen.getByText('Tool')).toBeInTheDocument();
  });

  it('displays message counts by role', () => {
    render(<MessageHistory messages={sampleMessages} />);
    expect(screen.getByText('1 assistant')).toBeInTheDocument();
    expect(screen.getByText('1 tool')).toBeInTheDocument();
  });

  it('can be expanded by default', () => {
    render(<MessageHistory messages={sampleMessages} defaultExpanded={true} />);
    expect(screen.getByText('You are a helpful assistant.')).toBeInTheDocument();
  });

  it('truncates long messages', () => {
    const longContent = 'A'.repeat(500);
    render(
      <MessageHistory
        messages={[createMessage('assistant', longContent)]}
        defaultExpanded={true}
        maxPreviewLength={100}
      />
    );

    // Should show truncated content with "..."
    const truncatedText = screen.getByText(/A+\.\.\./);
    expect(truncatedText).toBeInTheDocument();

    // Should have "Show more" button
    expect(screen.getByText('Show more')).toBeInTheDocument();
  });

  it('shows tool call ID for tool messages', () => {
    render(
      <MessageHistory
        messages={[createMessage('tool', 'Tool result', { toolCallId: 'tc-123' })]}
        defaultExpanded={true}
      />
    );

    expect(screen.getByText('tc-123')).toBeInTheDocument();
  });
});
