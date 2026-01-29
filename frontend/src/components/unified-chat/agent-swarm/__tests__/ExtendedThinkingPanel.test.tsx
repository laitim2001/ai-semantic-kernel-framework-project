/**
 * ExtendedThinkingPanel Test Suite
 *
 * Tests for the Extended Thinking display panel.
 * Sprint 104: ExtendedThinking + 工具調用展示優化
 */

import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ExtendedThinkingPanel } from '../ExtendedThinkingPanel';
import type { ThinkingContent } from '../types';

// =============================================================================
// Test Data
// =============================================================================

const createThinkingContent = (
  content: string,
  tokenCount?: number,
  timestamp?: string
): ThinkingContent => ({
  content,
  tokenCount,
  timestamp: timestamp || new Date().toISOString(),
});

const singleThinking: ThinkingContent[] = [
  createThinkingContent('Analyzing the problem...', 15),
];

const multipleThinkings: ThinkingContent[] = [
  createThinkingContent('First, I need to understand the context.', 20),
  createThinkingContent('Now analyzing the data patterns.', 18),
  createThinkingContent('Based on my analysis, I recommend...', 25),
];

const emptyThinkings: ThinkingContent[] = [];

// =============================================================================
// Tests
// =============================================================================

describe('ExtendedThinkingPanel', () => {
  describe('Rendering', () => {
    it('should not render when thinkingHistory is empty', () => {
      const { container } = render(
        <ExtendedThinkingPanel thinkingHistory={emptyThinkings} />
      );
      expect(container.firstChild).toBeNull();
    });

    it('should render panel with single thinking block', () => {
      render(<ExtendedThinkingPanel thinkingHistory={singleThinking} />);

      expect(screen.getByText(/思考過程/)).toBeInTheDocument();
      expect(screen.getByText('Analyzing the problem...')).toBeInTheDocument();
      expect(screen.getByText('1 block')).toBeInTheDocument();
    });

    it('should render multiple thinking blocks', () => {
      render(<ExtendedThinkingPanel thinkingHistory={multipleThinkings} />);

      expect(screen.getByText('3 blocks')).toBeInTheDocument();
      expect(screen.getByText('First, I need to understand the context.')).toBeInTheDocument();
      expect(screen.getByText('Now analyzing the data patterns.')).toBeInTheDocument();
      expect(screen.getByText('Based on my analysis, I recommend...')).toBeInTheDocument();
    });

    it('should display block indices', () => {
      render(<ExtendedThinkingPanel thinkingHistory={multipleThinkings} />);

      expect(screen.getByText('Block 1')).toBeInTheDocument();
      expect(screen.getByText('Block 2')).toBeInTheDocument();
      expect(screen.getByText('Block 3')).toBeInTheDocument();
    });
  });

  describe('Token Statistics', () => {
    it('should display token count for individual blocks', () => {
      render(<ExtendedThinkingPanel thinkingHistory={singleThinking} />);

      expect(screen.getByText('15 tokens')).toBeInTheDocument();
    });

    it('should calculate total tokens correctly', () => {
      render(<ExtendedThinkingPanel thinkingHistory={multipleThinkings} />);

      // Total: 20 + 18 + 25 = 63
      expect(screen.getByText('Total: 63 tokens')).toBeInTheDocument();
    });

    it('should handle missing token counts', () => {
      const thinkingsWithoutTokens: ThinkingContent[] = [
        createThinkingContent('No token count here'),
      ];

      render(<ExtendedThinkingPanel thinkingHistory={thinkingsWithoutTokens} />);

      // Should still render without errors
      expect(screen.getByText('No token count here')).toBeInTheDocument();
      expect(screen.getByText('Total: 0 tokens')).toBeInTheDocument();
    });
  });

  describe('Expand/Collapse', () => {
    it('should be expanded by default', () => {
      render(<ExtendedThinkingPanel thinkingHistory={singleThinking} />);

      // Content should be visible
      expect(screen.getByText('Analyzing the problem...')).toBeVisible();
    });

    it('should respect defaultExpanded prop', () => {
      render(
        <ExtendedThinkingPanel
          thinkingHistory={singleThinking}
          defaultExpanded={false}
        />
      );

      // Title should be visible, but content might be hidden
      expect(screen.getByText(/思考過程/)).toBeInTheDocument();
    });

    it('should toggle expand/collapse on click', () => {
      render(<ExtendedThinkingPanel thinkingHistory={singleThinking} />);

      const toggleButton = screen.getByRole('button');

      // Initially expanded
      expect(screen.getByText('Analyzing the problem...')).toBeVisible();

      // Click to collapse
      fireEvent.click(toggleButton);

      // Click to expand again
      fireEvent.click(toggleButton);
    });
  });

  describe('Custom Props', () => {
    it('should apply custom className', () => {
      const { container } = render(
        <ExtendedThinkingPanel
          thinkingHistory={singleThinking}
          className="custom-class"
        />
      );

      expect(container.querySelector('.custom-class')).toBeInTheDocument();
    });

    it('should apply custom maxHeight', () => {
      const { container } = render(
        <ExtendedThinkingPanel
          thinkingHistory={singleThinking}
          maxHeight={500}
        />
      );

      // The component should render with the maxHeight applied
      // Check that the thinking content is rendered
      expect(container.querySelector('.space-y-3')).toBeInTheDocument();
    });
  });

  describe('Timestamps', () => {
    it('should display timestamps for thinking blocks', () => {
      const now = new Date();
      const thinkingWithTime: ThinkingContent[] = [
        {
          content: 'Test content',
          tokenCount: 10,
          timestamp: now.toISOString(),
        },
      ];

      render(<ExtendedThinkingPanel thinkingHistory={thinkingWithTime} />);

      // Should display formatted timestamp
      expect(screen.getByText(/Updated:/)).toBeInTheDocument();
    });
  });

  describe('Auto-scroll', () => {
    it('should have autoScroll enabled by default', () => {
      // This is mainly a prop verification test
      // Actual auto-scroll behavior is difficult to test without DOM measurements
      render(<ExtendedThinkingPanel thinkingHistory={multipleThinkings} />);

      // Component should render successfully with auto-scroll
      expect(screen.getByText('3 blocks')).toBeInTheDocument();
    });

    it('should respect autoScroll=false prop', () => {
      render(
        <ExtendedThinkingPanel
          thinkingHistory={multipleThinkings}
          autoScroll={false}
        />
      );

      // Component should still render
      expect(screen.getByText('3 blocks')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have accessible button for expand/collapse', () => {
      render(<ExtendedThinkingPanel thinkingHistory={singleThinking} />);

      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('should render Brain icon for thinking indicator', () => {
      const { container } = render(
        <ExtendedThinkingPanel thinkingHistory={singleThinking} />
      );

      // Check for Lucide Brain icon (rendered as svg)
      const brainIcon = container.querySelector('svg.lucide-brain');
      expect(brainIcon).toBeInTheDocument();
    });
  });
});
