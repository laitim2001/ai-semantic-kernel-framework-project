/**
 * ToolCallItem Component Tests
 *
 * Sprint 103: WorkerDetailDrawer
 */

import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ToolCallItem } from '../ToolCallItem';
import type { ToolCallInfo } from '../types';

describe('ToolCallItem', () => {
  const createToolCall = (overrides: Partial<ToolCallInfo> = {}): ToolCallInfo => ({
    toolCallId: 'tc-1',
    toolName: 'test_tool',
    status: 'completed',
    inputArgs: { query: 'test query' },
    outputResult: { result: 'success' },
    durationMs: 1500,
    startedAt: '2026-01-29T10:00:00Z',
    completedAt: '2026-01-29T10:00:01Z',
    ...overrides,
  });

  it('renders tool name', () => {
    render(<ToolCallItem toolCall={createToolCall()} />);
    expect(screen.getByText('test_tool')).toBeInTheDocument();
  });

  it('renders duration', () => {
    render(<ToolCallItem toolCall={createToolCall()} />);
    expect(screen.getByText('1.50s')).toBeInTheDocument();
  });

  it('renders duration in ms for short durations', () => {
    render(<ToolCallItem toolCall={createToolCall({ durationMs: 500 })} />);
    expect(screen.getByText('500ms')).toBeInTheDocument();
  });

  it('expands to show input/output on click', () => {
    render(<ToolCallItem toolCall={createToolCall()} />);

    // Initially collapsed
    expect(screen.queryByText('Input:')).not.toBeInTheDocument();

    // Click to expand
    fireEvent.click(screen.getByText('test_tool'));

    // Should show input and output
    expect(screen.getByText('Input:')).toBeInTheDocument();
    expect(screen.getByText('Output:')).toBeInTheDocument();
  });

  it('shows error when present', () => {
    render(
      <ToolCallItem
        toolCall={createToolCall({
          status: 'failed',
          error: 'Connection timeout',
          outputResult: undefined,
        })}
        defaultExpanded={true}
      />
    );

    expect(screen.getByText('Error:')).toBeInTheDocument();
    expect(screen.getByText('Connection timeout')).toBeInTheDocument();
  });

  it('renders different status icons', () => {
    const statuses = ['pending', 'running', 'completed', 'failed'] as const;

    statuses.forEach((status) => {
      const { container, unmount } = render(
        <ToolCallItem toolCall={createToolCall({ status })} />
      );
      expect(container.firstChild).toBeInTheDocument();
      unmount();
    });
  });

  it('detects MCP tools by name pattern', () => {
    // Tool with colon (MCP pattern)
    const { container: mcpContainer } = render(
      <ToolCallItem toolCall={createToolCall({ toolName: 'azure:query_logs' })} />
    );
    expect(mcpContainer.querySelector('.lucide-cloud')).toBeInTheDocument();

    // Regular tool
    const { container: regularContainer } = render(
      <ToolCallItem toolCall={createToolCall({ toolName: 'regular_tool' })} />
    );
    expect(regularContainer.querySelector('.lucide-terminal')).toBeInTheDocument();
  });

  it('can be expanded by default', () => {
    render(
      <ToolCallItem
        toolCall={createToolCall()}
        defaultExpanded={true}
      />
    );

    // Should be expanded immediately
    expect(screen.getByText('Input:')).toBeInTheDocument();
  });
});
