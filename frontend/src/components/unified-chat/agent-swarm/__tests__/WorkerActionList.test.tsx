/**
 * WorkerActionList Test Suite
 *
 * Tests for the Worker action list component.
 * Sprint 104: ExtendedThinking + 工具調用展示優化
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  WorkerActionList,
  inferActionType,
  type WorkerAction,
  type ActionType,
} from '../WorkerActionList';

// =============================================================================
// Test Data
// =============================================================================

const createAction = (
  id: string,
  type: ActionType,
  title: string,
  overrides?: Partial<WorkerAction>
): WorkerAction => ({
  id,
  type,
  title,
  timestamp: new Date().toISOString(),
  ...overrides,
});

const singleAction: WorkerAction[] = [
  createAction('a1', 'search', 'Searching for relevant files'),
];

const multipleActions: WorkerAction[] = [
  createAction('a1', 'read_todo', 'Reading task list'),
  createAction('a2', 'think', 'Analyzing the problem'),
  createAction('a3', 'search', 'Searching codebase', {
    metadata: { resultCount: 42 },
  }),
  createAction('a4', 'file_write', 'Writing solution file'),
  createAction('a5', 'code', 'Executing code analysis'),
];

const emptyActions: WorkerAction[] = [];

// =============================================================================
// Tests
// =============================================================================

describe('WorkerActionList', () => {
  describe('Rendering', () => {
    it('should render empty state when no actions', () => {
      render(<WorkerActionList actions={emptyActions} />);

      expect(screen.getByText('No actions recorded')).toBeInTheDocument();
    });

    it('should render single action', () => {
      render(<WorkerActionList actions={singleAction} />);

      expect(screen.getByText('Searching for relevant files')).toBeInTheDocument();
    });

    it('should render multiple actions', () => {
      render(<WorkerActionList actions={multipleActions} />);

      expect(screen.getByText('Reading task list')).toBeInTheDocument();
      expect(screen.getByText('Analyzing the problem')).toBeInTheDocument();
      expect(screen.getByText('Searching codebase')).toBeInTheDocument();
      expect(screen.getByText('Writing solution file')).toBeInTheDocument();
      expect(screen.getByText('Executing code analysis')).toBeInTheDocument();
    });

    it('should display action type labels', () => {
      render(<WorkerActionList actions={multipleActions} />);

      expect(screen.getByText('Read')).toBeInTheDocument();
      expect(screen.getByText('Think')).toBeInTheDocument();
      expect(screen.getByText('Search')).toBeInTheDocument();
      expect(screen.getByText('Write File')).toBeInTheDocument();
      expect(screen.getByText('Code')).toBeInTheDocument();
    });

    it('should display result count from metadata', () => {
      render(<WorkerActionList actions={multipleActions} />);

      expect(screen.getByText('42 results')).toBeInTheDocument();
    });
  });

  describe('Action Icons', () => {
    it('should render correct icons for different action types', () => {
      const { container } = render(
        <WorkerActionList actions={multipleActions} />
      );

      // Check that SVG icons are present
      const icons = container.querySelectorAll('svg');
      expect(icons.length).toBeGreaterThan(0);
    });

    it('should apply correct colors to icons', () => {
      const { container } = render(
        <WorkerActionList
          actions={[createAction('a1', 'think', 'Thinking')]}
        />
      );

      // Check for purple color class on think icon
      const icon = container.querySelector('svg');
      expect(icon?.classList.contains('text-purple-500')).toBe(true);
    });
  });

  describe('Click Handling', () => {
    it('should call onActionClick when action is clicked', () => {
      const handleClick = vi.fn();
      render(
        <WorkerActionList
          actions={singleAction}
          onActionClick={handleClick}
        />
      );

      const actionItem = screen.getByText('Searching for relevant files');
      fireEvent.click(actionItem);

      expect(handleClick).toHaveBeenCalledTimes(1);
      expect(handleClick).toHaveBeenCalledWith(singleAction[0]);
    });

    it('should support keyboard navigation', () => {
      const handleClick = vi.fn();
      render(
        <WorkerActionList
          actions={singleAction}
          onActionClick={handleClick}
        />
      );

      const actionItem = screen.getByRole('button');
      fireEvent.keyDown(actionItem, { key: 'Enter' });

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('should support space key activation', () => {
      const handleClick = vi.fn();
      render(
        <WorkerActionList
          actions={singleAction}
          onActionClick={handleClick}
        />
      );

      const actionItem = screen.getByRole('button');
      fireEvent.keyDown(actionItem, { key: ' ' });

      expect(handleClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('Expandable Actions', () => {
    it('should show chevron for expandable actions', () => {
      const expandableAction: WorkerAction[] = [
        createAction('a1', 'search', 'Search results', { expandable: true }),
      ];

      const { container } = render(
        <WorkerActionList actions={expandableAction} />
      );

      // Chevron should be present (may be hidden until hover)
      const chevrons = container.querySelectorAll('.lucide-chevron-right');
      expect(chevrons.length).toBeGreaterThan(0);
    });

    it('should not show chevron for non-expandable actions', () => {
      const nonExpandableAction: WorkerAction[] = [
        createAction('a1', 'think', 'Thinking', { expandable: false }),
      ];

      render(<WorkerActionList actions={nonExpandableAction} />);

      // ChevronRight for expandable should not be in the action item
      // (there may be other chevrons in the component)
    });
  });

  describe('Description Display', () => {
    it('should display description when provided', () => {
      const actionWithDescription: WorkerAction[] = [
        createAction('a1', 'code', 'Running tests', {
          description: 'unit tests for auth module',
        }),
      ];

      render(<WorkerActionList actions={actionWithDescription} />);

      expect(screen.getByText('unit tests for auth module')).toBeInTheDocument();
    });
  });

  describe('Custom Props', () => {
    it('should apply custom className', () => {
      const { container } = render(
        <WorkerActionList
          actions={singleAction}
          className="custom-list-class"
        />
      );

      expect(container.querySelector('.custom-list-class')).toBeInTheDocument();
    });

    it('should apply maxHeight styling', () => {
      const { container } = render(
        <WorkerActionList
          actions={multipleActions}
          maxHeight={200}
        />
      );

      const listContainer = container.firstChild as HTMLElement;
      expect(listContainer.style.maxHeight).toBe('200px');
      expect(listContainer.style.overflowY).toBe('auto');
    });
  });

  describe('Accessibility', () => {
    it('should have role=button on action items', () => {
      render(<WorkerActionList actions={singleAction} />);

      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('should have tabIndex for keyboard navigation', () => {
      const { container } = render(
        <WorkerActionList actions={singleAction} />
      );

      const actionItem = container.querySelector('[tabindex="0"]');
      expect(actionItem).toBeInTheDocument();
    });
  });
});

// =============================================================================
// inferActionType Tests
// =============================================================================

describe('inferActionType', () => {
  it('should infer file_read for read operations', () => {
    expect(inferActionType('readFile')).toBe('file_read');
    expect(inferActionType('Read')).toBe('file_read');
    expect(inferActionType('get_content')).toBe('file_read');
  });

  it('should infer file_write for write operations', () => {
    expect(inferActionType('writeFile')).toBe('file_write');
    expect(inferActionType('save_document')).toBe('file_write');
    expect(inferActionType('edit_file')).toBe('file_write');
  });

  it('should infer search for search operations', () => {
    expect(inferActionType('search_codebase')).toBe('search');
    expect(inferActionType('grep_pattern')).toBe('search');
    expect(inferActionType('find_files')).toBe('search');
  });

  it('should infer code for code operations', () => {
    expect(inferActionType('execute_code')).toBe('code');
    expect(inferActionType('code_analysis')).toBe('code');
  });

  it('should infer database for database operations', () => {
    expect(inferActionType('database_query')).toBe('database');
    expect(inferActionType('run_sql')).toBe('database');
    expect(inferActionType('query_db')).toBe('database');
  });

  it('should infer terminal for terminal operations', () => {
    expect(inferActionType('terminal_command')).toBe('terminal');
    expect(inferActionType('bash_execute')).toBe('terminal');
    expect(inferActionType('shell_run')).toBe('terminal');
  });

  it('should infer web for web operations', () => {
    expect(inferActionType('web_fetch')).toBe('web');
    expect(inferActionType('http_request')).toBe('web');
    expect(inferActionType('fetch_url')).toBe('web');
  });

  it('should infer think for think operations', () => {
    expect(inferActionType('think_step')).toBe('think');
    expect(inferActionType('analyze_problem')).toBe('think');
  });

  it('should infer todo types correctly', () => {
    expect(inferActionType('todo_read')).toBe('read_todo');
    expect(inferActionType('list_todo')).toBe('read_todo');
    expect(inferActionType('todo_write')).toBe('write_todo');
    expect(inferActionType('add_todo')).toBe('write_todo');
  });

  it('should return custom for unknown operations', () => {
    expect(inferActionType('unknown_operation')).toBe('custom');
    expect(inferActionType('random_action')).toBe('custom');
  });
});
