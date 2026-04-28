/**
 * WorkflowSidePanel - Workflow Progress Side Panel
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * S62-4: WorkflowSidePanel Component
 * Sprint 65: S65-4 - UI Polish & Accessibility
 * Phase 16: Unified Agentic Chat Interface
 *
 * Side panel displaying workflow progress, tool tracking, and checkpoints.
 * Only visible when mode is 'workflow'.
 * Enhanced with animations and accessibility features.
 */

import { FC, useState, useCallback, useMemo } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import type { WorkflowSidePanelProps } from '@/types/unified-chat';
import { StepProgress } from './StepProgress';
import { ToolCallTracker } from './ToolCallTracker';
import { CheckpointList } from './CheckpointList';
import { cn } from '@/lib/utils';

// Check for reduced motion preference
const prefersReducedMotion = () => {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
};

/**
 * WorkflowSidePanel Component
 *
 * Displays three main sections:
 * 1. Step Progress - Current workflow step and overall progress
 * 2. Tool Call Tracker - Timeline of tool executions
 * 3. Checkpoint List - Available checkpoints for restore
 *
 * Can be collapsed to save screen space.
 */
export const WorkflowSidePanel: FC<WorkflowSidePanelProps> = ({
  workflowState,
  toolCalls,
  checkpoints,
  onRestoreCheckpoint,
  isCollapsed: controlledCollapsed,
  onToggleCollapse,
}) => {
  // Internal collapsed state (used if not controlled)
  const [internalCollapsed, setInternalCollapsed] = useState(false);

  // Use controlled or internal collapsed state
  const isCollapsed = controlledCollapsed ?? internalCollapsed;

  // Check reduced motion preference
  const reduceMotion = useMemo(() => prefersReducedMotion(), []);

  // Handle toggle
  const handleToggle = useCallback(() => {
    if (onToggleCollapse) {
      onToggleCollapse();
    } else {
      setInternalCollapsed((prev) => !prev);
    }
  }, [onToggleCollapse]);

  // Animation duration based on motion preference
  const transitionDuration = reduceMotion ? 'duration-0' : 'duration-300';

  return (
    <aside
      className={cn(
        'flex flex-col bg-gray-50 border-l transition-all ease-out',
        transitionDuration,
        isCollapsed ? 'w-12' : 'w-80'
      )}
      data-testid="workflow-side-panel"
      data-collapsed={isCollapsed}
      role="complementary"
      aria-label="Workflow progress panel"
      aria-expanded={!isCollapsed}
    >
      {/* Collapse Toggle */}
      <div className="flex items-center justify-between p-2 border-b bg-white">
        {!isCollapsed && (
          <h2 className="text-sm font-semibold text-gray-700 px-2">
            Workflow Progress
          </h2>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={handleToggle}
          title={isCollapsed ? 'Expand panel' : 'Collapse panel'}
        >
          {isCollapsed ? (
            <ChevronLeft className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Panel Content */}
      {!isCollapsed && (
        <div
          className={cn(
            'flex-1 overflow-y-auto',
            !reduceMotion && 'animate-fade-in'
          )}
        >
          {/* Step Progress Section */}
          <section className="p-4 border-b" aria-labelledby="progress-heading">
            <h3
              id="progress-heading"
              className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3"
            >
              Progress
            </h3>
            {workflowState ? (
              <StepProgress
                steps={workflowState.steps}
                currentStep={workflowState.currentStepIndex}
                totalSteps={workflowState.totalSteps}
              />
            ) : (
              <div className="text-sm text-gray-400 text-center py-4" role="status">
                No workflow active
              </div>
            )}
          </section>

          {/* Tool Call Tracker Section */}
          <section className="p-4 border-b" aria-labelledby="tools-heading">
            <h3
              id="tools-heading"
              className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3"
            >
              Tool Calls ({toolCalls.length})
            </h3>
            <ToolCallTracker
              toolCalls={toolCalls}
              maxVisible={5}
              showTimings
            />
          </section>

          {/* Checkpoint List Section */}
          <section className="p-4" aria-labelledby="checkpoints-heading">
            <h3
              id="checkpoints-heading"
              className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3"
            >
              Checkpoints ({checkpoints.length})
            </h3>
            <CheckpointList
              checkpoints={checkpoints}
              onRestore={onRestoreCheckpoint}
              maxVisible={3}
            />
          </section>
        </div>
      )}

      {/* Collapsed State Icons */}
      {isCollapsed && (
        <div className="flex-1 flex flex-col items-center py-4 gap-6">
          <div
            className="text-gray-400 cursor-pointer hover:text-gray-600"
            title="Workflow Progress"
          >
            📊
          </div>
          <div
            className="text-gray-400 cursor-pointer hover:text-gray-600"
            title={`${toolCalls.length} tool calls`}
          >
            🔧
          </div>
          <div
            className="text-gray-400 cursor-pointer hover:text-gray-600"
            title={`${checkpoints.length} checkpoints`}
          >
            📍
          </div>
        </div>
      )}
    </aside>
  );
};

export default WorkflowSidePanel;
