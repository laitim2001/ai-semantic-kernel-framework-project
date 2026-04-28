/**
 * StepProgress - Workflow Step Progress Component
 *
 * Sprint 62: Core Architecture & Adaptive Layout
 * S62-4: WorkflowSidePanel Component
 * Phase 16: Unified Agentic Chat Interface
 *
 * Displays workflow step progress with visual indicators.
 */

import { FC, useMemo } from 'react';
import { Check, Circle, Loader2, X, SkipForward } from 'lucide-react';
import type { StepProgressProps, WorkflowStep, WorkflowStepStatus } from '@/types/unified-chat';
import { cn } from '@/lib/utils';

/**
 * Get status icon and color for a workflow step
 */
const getStepConfig = (status: WorkflowStepStatus) => {
  switch (status) {
    case 'completed':
      return {
        icon: Check,
        color: 'text-green-600',
        bgColor: 'bg-green-100',
        borderColor: 'border-green-600',
      };
    case 'running':
      return {
        icon: Loader2,
        color: 'text-blue-600',
        bgColor: 'bg-blue-100',
        borderColor: 'border-blue-600',
        animate: true,
      };
    case 'failed':
      return {
        icon: X,
        color: 'text-red-600',
        bgColor: 'bg-red-100',
        borderColor: 'border-red-600',
      };
    case 'skipped':
      return {
        icon: SkipForward,
        color: 'text-gray-400',
        bgColor: 'bg-gray-100',
        borderColor: 'border-gray-400',
      };
    case 'pending':
    default:
      return {
        icon: Circle,
        color: 'text-gray-400',
        bgColor: 'bg-gray-50',
        borderColor: 'border-gray-300',
      };
  }
};

/**
 * StepProgress Component
 *
 * Displays:
 * - Overall progress bar with percentage
 * - Step counter (current/total)
 * - List of steps with status icons
 */
export const StepProgress: FC<StepProgressProps> = ({
  steps,
  currentStep,
  totalSteps,
}) => {
  // Calculate progress percentage
  const progress = useMemo(() => {
    if (totalSteps === 0) return 0;
    const completedSteps = steps.filter(
      (s) => s.status === 'completed' || s.status === 'skipped'
    ).length;
    return Math.round((completedSteps / totalSteps) * 100);
  }, [steps, totalSteps]);

  // If no steps, show empty state
  if (steps.length === 0) {
    return (
      <div className="text-sm text-gray-400 text-center py-2">
        No steps defined
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="step-progress">
      {/* Progress Header */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">
          Step {currentStep + 1} of {totalSteps}
        </span>
        <span className="text-sm text-gray-500">{progress}%</span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Step List */}
      <div className="space-y-2">
        {steps.map((step, index) => (
          <StepItem
            key={step.id}
            step={step}
            index={index}
            isCurrent={index === currentStep}
          />
        ))}
      </div>
    </div>
  );
};

/**
 * Individual Step Item
 */
interface StepItemProps {
  step: WorkflowStep;
  index: number;
  isCurrent: boolean;
}

const StepItem: FC<StepItemProps> = ({ step, index, isCurrent }) => {
  const config = getStepConfig(step.status);
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'flex items-center gap-3 p-2 rounded-lg transition-colors',
        isCurrent && 'bg-blue-50',
        step.status === 'failed' && 'bg-red-50'
      )}
      data-testid={`step-item-${index}`}
      data-status={step.status}
    >
      {/* Status Icon */}
      <div
        className={cn(
          'flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center border',
          config.bgColor,
          config.borderColor
        )}
      >
        <Icon
          className={cn(
            'h-3.5 w-3.5',
            config.color,
            config.animate && 'animate-spin'
          )}
        />
      </div>

      {/* Step Info */}
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-gray-700 truncate">
          {step.name}
        </div>
        {step.description && (
          <div className="text-xs text-gray-500 truncate">
            {step.description}
          </div>
        )}
        {step.error && (
          <div className="text-xs text-red-600 truncate" title={step.error}>
            {step.error}
          </div>
        )}
      </div>

      {/* Step Number */}
      <div className="text-xs text-gray-400 flex-shrink-0">
        #{index + 1}
      </div>
    </div>
  );
};

export default StepProgress;
