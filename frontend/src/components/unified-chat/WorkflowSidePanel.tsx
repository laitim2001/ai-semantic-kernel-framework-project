/**
 * WorkflowSidePanel - Workflow Progress Side Panel
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * S62-4: WorkflowSidePanel Component
 * Phase 16: Unified Agentic Chat Interface
 *
 * Side panel displaying workflow progress, tool tracking, and checkpoints.
 * Only visible when mode is 'workflow'.
 */

import { FC, useState, useCallback } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import type { WorkflowSidePanelProps } from '@/types/unified-chat';
import { StepProgress } from './StepProgress';
import { ToolCallTracker } from './ToolCallTracker';
import { CheckpointList } from './CheckpointList';
import { cn } from '@/lib/utils';

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

  // Handle toggle
  const handleToggle = useCallback(() => {
    if (onToggleCollapse) {
      onToggleCollapse();
    } else {
      setInternalCollapsed((prev) => !prev);
    }
  }, [onToggleCollapse]);

  return (
    <aside
      className={cn(
        'flex flex-col bg-gray-50 border-l transition-all duration-300',
        isCollapsed ? 'w-12' : 'w-80'
      )}
      data-testid="workflow-side-panel"
      data-collapsed={isCollapsed}
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
        <div className="flex-1 overflow-y-auto">
          {/* Step Progress Section */}
          <div className="p-4 border-b">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
              Progress
            </h3>
            {workflowState ? (
              <StepProgress
                steps={workflowState.steps}
                currentStep={workflowState.currentStepIndex}
                totalSteps={workflowState.totalSteps}
              />
            ) : (
              <div className="text-sm text-gray-400 text-center py-4">
                No workflow active
              </div>
            )}
          </div>

          {/* Tool Call Tracker Section */}
          <div className="p-4 border-b">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
              Tool Calls
            </h3>
            <ToolCallTracker
              toolCalls={toolCalls}
              maxVisible={5}
              showTimings
            />
          </div>

          {/* Checkpoint List Section */}
          <div className="p-4">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
              Checkpoints
            </h3>
            <CheckpointList
              checkpoints={checkpoints}
              onRestore={onRestoreCheckpoint}
              maxVisible={3}
            />
          </div>
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
