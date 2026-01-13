// =============================================================================
// IPA Platform - DevUI Timeline Node Component
// =============================================================================
// Sprint 88: S88-1 - Timeline Visualization
//
// Individual node in the timeline representing a single event.
//
// Dependencies:
//   - Lucide React (icons)
//   - Tailwind CSS
// =============================================================================

import { FC, useState } from 'react';
import {
  Settings,
  Bot,
  Wrench,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Play,
  Square,
  Zap,
  Clock,
} from 'lucide-react';
import type { TraceEvent } from '@/types/devtools';
import { DurationBadge } from './DurationBar';
import { cn } from '@/lib/utils';

interface TimelineNodeProps {
  /** The event data */
  event: TraceEvent;
  /** Whether this is a start event with a paired end event */
  isPaired?: boolean;
  /** The paired event (if any) */
  pairedEvent?: TraceEvent;
  /** Maximum duration for scaling */
  maxDurationMs: number;
  /** Click handler */
  onClick?: (event: TraceEvent) => void;
  /** Whether this node is selected */
  isSelected?: boolean;
  /** Indent level for nested events */
  indentLevel?: number;
}

/**
 * Get event type configuration (icon, color, label)
 */
function getEventConfig(eventType: string) {
  const type = eventType.toUpperCase();

  // Workflow events
  if (type.includes('WORKFLOW_START')) {
    return { icon: Play, color: 'text-blue-600', bg: 'bg-blue-100', label: 'Workflow Start' };
  }
  if (type.includes('WORKFLOW_END') || type.includes('WORKFLOW_COMPLETE')) {
    return { icon: Square, color: 'text-blue-600', bg: 'bg-blue-100', label: 'Workflow End' };
  }
  if (type.includes('WORKFLOW')) {
    return { icon: Settings, color: 'text-blue-600', bg: 'bg-blue-100', label: 'Workflow' };
  }

  // Executor events
  if (type.includes('EXECUTOR_START')) {
    return { icon: Play, color: 'text-indigo-600', bg: 'bg-indigo-100', label: 'Executor Start' };
  }
  if (type.includes('EXECUTOR_END')) {
    return { icon: Square, color: 'text-indigo-600', bg: 'bg-indigo-100', label: 'Executor End' };
  }
  if (type.includes('EXECUTOR')) {
    return { icon: Zap, color: 'text-indigo-600', bg: 'bg-indigo-100', label: 'Executor' };
  }

  // LLM events
  if (type.includes('LLM_REQUEST')) {
    return { icon: Bot, color: 'text-purple-600', bg: 'bg-purple-100', label: 'LLM Request' };
  }
  if (type.includes('LLM_RESPONSE')) {
    return { icon: Bot, color: 'text-purple-600', bg: 'bg-purple-100', label: 'LLM Response' };
  }
  if (type.includes('LLM')) {
    return { icon: Bot, color: 'text-purple-600', bg: 'bg-purple-100', label: 'LLM' };
  }

  // Tool events
  if (type.includes('TOOL_CALL')) {
    return { icon: Wrench, color: 'text-green-600', bg: 'bg-green-100', label: 'Tool Call' };
  }
  if (type.includes('TOOL_RESULT')) {
    return { icon: Wrench, color: 'text-green-600', bg: 'bg-green-100', label: 'Tool Result' };
  }
  if (type.includes('TOOL')) {
    return { icon: Wrench, color: 'text-green-600', bg: 'bg-green-100', label: 'Tool' };
  }

  // Checkpoint events
  if (type.includes('CHECKPOINT')) {
    return { icon: CheckCircle, color: 'text-yellow-600', bg: 'bg-yellow-100', label: 'Checkpoint' };
  }

  // Error/Warning events
  if (type.includes('ERROR')) {
    return { icon: XCircle, color: 'text-red-600', bg: 'bg-red-100', label: 'Error' };
  }
  if (type.includes('WARNING')) {
    return { icon: AlertTriangle, color: 'text-orange-600', bg: 'bg-orange-100', label: 'Warning' };
  }

  // Default
  return { icon: Clock, color: 'text-gray-600', bg: 'bg-gray-100', label: eventType };
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }) + '.' + date.getMilliseconds().toString().padStart(3, '0');
}

/**
 * Get duration variant based on performance
 */
function getDurationVariant(durationMs?: number): 'success' | 'warning' | 'error' | 'default' {
  if (!durationMs) return 'default';
  if (durationMs < 100) return 'success';
  if (durationMs < 1000) return 'default';
  if (durationMs < 5000) return 'warning';
  return 'error';
}

/**
 * Timeline Node Component
 * Represents a single event in the timeline
 */
export const TimelineNode: FC<TimelineNodeProps> = ({
  event,
  isPaired = false,
  pairedEvent,
  maxDurationMs,
  onClick,
  isSelected = false,
  indentLevel = 0,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const config = getEventConfig(event.event_type);
  const Icon = config.icon;

  // Calculate paired duration
  const pairDuration = pairedEvent
    ? new Date(pairedEvent.timestamp).getTime() - new Date(event.timestamp).getTime()
    : event.duration_ms;

  const handleClick = () => {
    onClick?.(event);
  };

  const handleToggleExpand = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsExpanded(!isExpanded);
  };

  return (
    <div
      className={cn(
        'relative flex items-start gap-3 py-2 px-3 rounded-lg transition-colors cursor-pointer',
        'hover:bg-gray-50',
        isSelected && 'bg-purple-50 border border-purple-200',
        isPaired && 'border-l-2 border-l-gray-200'
      )}
      style={{ marginLeft: `${indentLevel * 24}px` }}
      onClick={handleClick}
    >
      {/* Timeline connector line */}
      <div className="absolute left-0 top-0 bottom-0 w-px bg-gray-200" style={{ left: '18px' }} />

      {/* Event icon */}
      <div className={cn(
        'relative z-10 flex items-center justify-center w-8 h-8 rounded-full',
        config.bg
      )}>
        <Icon className={cn('w-4 h-4', config.color)} />
      </div>

      {/* Event content */}
      <div className="flex-1 min-w-0">
        {/* Header row */}
        <div className="flex items-center gap-2">
          {/* Expand toggle (if has details) */}
          {Object.keys(event.data).length > 0 && (
            <button
              onClick={handleToggleExpand}
              className="p-0.5 hover:bg-gray-200 rounded"
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 text-gray-500" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-500" />
              )}
            </button>
          )}

          {/* Event type label */}
          <span className={cn('text-sm font-medium', config.color)}>
            {config.label}
          </span>

          {/* Severity badge for non-info levels */}
          {event.severity !== 'info' && event.severity !== 'debug' && (
            <span className={cn(
              'px-1.5 py-0.5 text-xs rounded',
              event.severity === 'error' || event.severity === 'critical'
                ? 'bg-red-100 text-red-700'
                : 'bg-yellow-100 text-yellow-700'
            )}>
              {event.severity}
            </span>
          )}

          {/* Tags */}
          {event.tags.slice(0, 2).map((tag, idx) => (
            <span
              key={idx}
              className="px-1.5 py-0.5 text-xs bg-gray-100 text-gray-600 rounded"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* Details row */}
        <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
          {/* Timestamp */}
          <span className="font-mono">
            {formatTimestamp(event.timestamp)}
          </span>

          {/* Duration */}
          {pairDuration !== undefined && pairDuration > 0 && (
            <DurationBadge
              durationMs={pairDuration}
              variant={getDurationVariant(pairDuration)}
            />
          )}

          {/* Step number */}
          {event.step_number !== undefined && (
            <span>Step {event.step_number}</span>
          )}

          {/* Executor ID */}
          {event.executor_id && (
            <span className="truncate max-w-[120px]" title={event.executor_id}>
              {event.executor_id.slice(0, 8)}...
            </span>
          )}
        </div>

        {/* Expanded data preview */}
        {isExpanded && Object.keys(event.data).length > 0 && (
          <div className="mt-2 p-2 bg-gray-50 rounded text-xs font-mono overflow-x-auto">
            <pre className="text-gray-700 whitespace-pre-wrap">
              {JSON.stringify(event.data, null, 2).slice(0, 500)}
              {JSON.stringify(event.data, null, 2).length > 500 && '...'}
            </pre>
          </div>
        )}
      </div>

      {/* Duration bar (right side) */}
      {pairDuration !== undefined && pairDuration > 0 && (
        <div className="w-24 flex-shrink-0">
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full transition-all duration-300',
                getDurationVariant(pairDuration) === 'error' ? 'bg-red-500' :
                getDurationVariant(pairDuration) === 'warning' ? 'bg-yellow-500' :
                getDurationVariant(pairDuration) === 'success' ? 'bg-green-500' :
                'bg-purple-500'
              )}
              style={{
                width: `${Math.max(5, Math.min(100, (pairDuration / maxDurationMs) * 100))}%`
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default TimelineNode;
