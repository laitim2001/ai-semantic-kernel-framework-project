/**
 * StepProgressEnhanced - Enhanced Workflow Step Progress Component
 *
 * Sprint 69: S69-2 - StepProgress Sub-step Component
 * Phase 17: Agentic Chat Enhancement
 *
 * Claude Code-style hierarchical step progress display with sub-steps,
 * progress percentage, and status icons.
 *
 * Visual Example:
 * ```
 * Step 2/5: Process documents (45%)  [████░░░░░░]
 *   ├─ ✓ Load files
 *   ├─ ◉ Parse content (67%)
 *   ├─ ○ Analyze structure
 *   └─ ○ Generate summary
 * ```
 */

import { FC, useState, useMemo, useCallback } from 'react';
import { Check, Circle, Loader2, AlertCircle, ChevronDown, ChevronRight, Slash } from 'lucide-react';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

export type SubStepStatusType = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';

export interface SubStep {
  id: string;
  name: string;
  status: SubStepStatusType;
  progress?: number;
  message?: string;
  startedAt?: string;
  completedAt?: string;
}

export interface StepProgressEvent {
  stepId: string;
  stepName: string;
  current: number;
  total: number;
  progress: number;
  status: SubStepStatusType;
  substeps: SubStep[];
  metadata?: Record<string, unknown>;
}

export interface StepProgressEnhancedProps {
  step: StepProgressEvent;
  isExpanded?: boolean;
  onToggle?: () => void;
  showSubsteps?: boolean;
}

// =============================================================================
// Helper: Reduced Motion Detection
// =============================================================================

const prefersReducedMotion = (): boolean => {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
};

// =============================================================================
// StatusIcon Component
// =============================================================================

interface StatusIconProps {
  status: SubStepStatusType;
  className?: string;
}

export const StatusIcon: FC<StatusIconProps> = ({ status, className }) => {
  const iconProps = {
    className: cn('w-4 h-4', className),
    'aria-hidden': true,
  };

  switch (status) {
    case 'completed':
      return <Check {...iconProps} className={cn(iconProps.className, 'text-green-500')} />;
    case 'running':
      return <Loader2 {...iconProps} className={cn(iconProps.className, 'text-blue-500 animate-spin')} />;
    case 'failed':
      return <AlertCircle {...iconProps} className={cn(iconProps.className, 'text-red-500')} />;
    case 'skipped':
      return <Slash {...iconProps} className={cn(iconProps.className, 'text-gray-400')} />;
    case 'pending':
    default:
      return <Circle {...iconProps} className={cn(iconProps.className, 'text-gray-400')} />;
  }
};

// =============================================================================
// SubStepItem Component
// =============================================================================

interface SubStepItemProps {
  substep: SubStep;
  isLast?: boolean;
}

export const SubStepItem: FC<SubStepItemProps> = ({ substep, isLast = false }) => {
  const isCompleted = substep.status === 'completed';
  const isRunning = substep.status === 'running';
  const isFailed = substep.status === 'failed';

  return (
    <div
      className={cn(
        'flex items-center gap-2 py-1 text-sm',
        isCompleted && 'text-muted-foreground',
        isFailed && 'text-red-600'
      )}
      role="listitem"
      aria-label={`${substep.name}: ${substep.status}`}
    >
      {/* Tree Line */}
      <span className="text-gray-300 select-none" aria-hidden="true">
        {isLast ? '└─' : '├─'}
      </span>

      {/* Status Icon */}
      <StatusIcon status={substep.status} />

      {/* Name */}
      <span className={cn(
        'flex-1 truncate',
        isCompleted && 'line-through opacity-70'
      )}>
        {substep.name}
      </span>

      {/* Progress (if running and has progress) */}
      {isRunning && substep.progress !== undefined && (
        <span className="text-xs text-blue-500 tabular-nums">
          ({substep.progress}%)
        </span>
      )}

      {/* Message (if present) */}
      {substep.message && (
        <span className="text-xs text-muted-foreground ml-auto truncate max-w-[120px]" title={substep.message}>
          {substep.message}
        </span>
      )}
    </div>
  );
};

// =============================================================================
// StepProgressEnhanced Component
// =============================================================================

export const StepProgressEnhanced: FC<StepProgressEnhancedProps> = ({
  step,
  isExpanded: controlledExpanded,
  onToggle,
  showSubsteps = true,
}) => {
  const [internalExpanded, setInternalExpanded] = useState(true);
  const reduceMotion = useMemo(() => prefersReducedMotion(), []);

  const isExpanded = controlledExpanded ?? internalExpanded;

  const handleToggle = useCallback(() => {
    if (onToggle) {
      onToggle();
    } else {
      setInternalExpanded((prev) => !prev);
    }
  }, [onToggle]);

  const hasSubsteps = step.substeps && step.substeps.length > 0;

  // Animation config based on reduced motion preference
  const transitionClass = reduceMotion ? '' : 'transition-all duration-300 ease-out';
  const progressTransition = reduceMotion ? '' : 'transition-[width] duration-300';

  return (
    <div
      className="space-y-2"
      data-testid="step-progress-enhanced"
      data-step-id={step.stepId}
      role="article"
      aria-label={`Step ${step.current} of ${step.total}: ${step.stepName}`}
    >
      {/* Main Step Header */}
      <div
        className={cn(
          'flex items-center justify-between p-2 rounded-lg',
          'bg-secondary/50 hover:bg-secondary/70',
          hasSubsteps && showSubsteps ? 'cursor-pointer' : '',
          step.status === 'failed' && 'bg-red-50 hover:bg-red-100'
        )}
        onClick={hasSubsteps && showSubsteps ? handleToggle : undefined}
        role={hasSubsteps && showSubsteps ? 'button' : undefined}
        aria-expanded={hasSubsteps && showSubsteps ? isExpanded : undefined}
        tabIndex={hasSubsteps && showSubsteps ? 0 : undefined}
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === ' ') && hasSubsteps && showSubsteps) {
            e.preventDefault();
            handleToggle();
          }
        }}
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {/* Expand/Collapse Icon */}
          {hasSubsteps && showSubsteps && (
            <span className="flex-shrink-0 text-gray-400" aria-hidden="true">
              {isExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </span>
          )}

          {/* Status Icon */}
          <StatusIcon status={step.status} />

          {/* Step Info */}
          <span className="font-medium truncate">
            Step {step.current}/{step.total}: {step.stepName}
          </span>

          {/* Progress Percentage (if running) */}
          {step.status === 'running' && (
            <span className="text-sm text-muted-foreground tabular-nums">
              ({step.progress}%)
            </span>
          )}
        </div>

        {/* Progress Bar */}
        <div
          className="w-24 h-2 bg-secondary rounded-full overflow-hidden flex-shrink-0 ml-2"
          role="progressbar"
          aria-valuenow={step.progress}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className={cn(
              'h-full rounded-full',
              progressTransition,
              step.status === 'completed' ? 'bg-green-500' :
              step.status === 'failed' ? 'bg-red-500' :
              step.status === 'running' ? 'bg-blue-500' :
              'bg-gray-300'
            )}
            style={{ width: `${step.progress}%` }}
          />
        </div>
      </div>

      {/* Sub-steps (Collapsible) */}
      {hasSubsteps && showSubsteps && (
        <div
          className={cn(
            'ml-6 overflow-hidden',
            transitionClass,
            isExpanded ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'
          )}
          role="list"
          aria-label="Sub-steps"
        >
          <div className="space-y-0.5 py-1">
            {step.substeps.map((substep, index) => (
              <SubStepItem
                key={substep.id}
                substep={substep}
                isLast={index === step.substeps.length - 1}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default StepProgressEnhanced;
