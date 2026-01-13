// =============================================================================
// IPA Platform - DevUI Tree Node Component
// =============================================================================
// Sprint 88: S88-2 - Event Tree Structure
//
// Individual tree node for displaying hierarchical events.
//
// Dependencies:
//   - Lucide React
//   - Tailwind CSS
// =============================================================================

import { FC, useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Settings,
  Bot,
  Wrench,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Play,
  Square,
  Zap,
  Clock,
  Minus,
} from 'lucide-react';
import type { TraceEvent } from '@/types/devtools';
import { DurationBadge } from './DurationBar';
import { cn } from '@/lib/utils';

export interface EventTreeNode {
  event: TraceEvent;
  children: EventTreeNode[];
  depth: number;
}

interface TreeNodeProps {
  /** Tree node data */
  node: EventTreeNode;
  /** Click handler */
  onClick?: (event: TraceEvent) => void;
  /** Selected event ID */
  selectedEventId?: string;
  /** Initial expanded state */
  defaultExpanded?: boolean;
}

/**
 * Get event icon and color configuration
 */
function getEventIcon(eventType: string): {
  icon: typeof Settings;
  color: string;
  bgColor: string;
} {
  const type = eventType.toUpperCase();

  if (type.includes('WORKFLOW_START')) {
    return { icon: Play, color: 'text-blue-600', bgColor: 'bg-blue-100' };
  }
  if (type.includes('WORKFLOW_END')) {
    return { icon: Square, color: 'text-blue-600', bgColor: 'bg-blue-100' };
  }
  if (type.includes('WORKFLOW')) {
    return { icon: Settings, color: 'text-blue-600', bgColor: 'bg-blue-100' };
  }
  if (type.includes('EXECUTOR_START')) {
    return { icon: Play, color: 'text-indigo-600', bgColor: 'bg-indigo-100' };
  }
  if (type.includes('EXECUTOR_END')) {
    return { icon: Square, color: 'text-indigo-600', bgColor: 'bg-indigo-100' };
  }
  if (type.includes('EXECUTOR')) {
    return { icon: Zap, color: 'text-indigo-600', bgColor: 'bg-indigo-100' };
  }
  if (type.includes('LLM_REQUEST') || type.includes('LLM_RESPONSE')) {
    return { icon: Bot, color: 'text-purple-600', bgColor: 'bg-purple-100' };
  }
  if (type.includes('LLM')) {
    return { icon: Bot, color: 'text-purple-600', bgColor: 'bg-purple-100' };
  }
  if (type.includes('TOOL_CALL') || type.includes('TOOL_RESULT')) {
    return { icon: Wrench, color: 'text-green-600', bgColor: 'bg-green-100' };
  }
  if (type.includes('TOOL')) {
    return { icon: Wrench, color: 'text-green-600', bgColor: 'bg-green-100' };
  }
  if (type.includes('CHECKPOINT')) {
    return { icon: CheckCircle, color: 'text-yellow-600', bgColor: 'bg-yellow-100' };
  }
  if (type.includes('ERROR')) {
    return { icon: XCircle, color: 'text-red-600', bgColor: 'bg-red-100' };
  }
  if (type.includes('WARNING')) {
    return { icon: AlertTriangle, color: 'text-orange-600', bgColor: 'bg-orange-100' };
  }
  return { icon: Clock, color: 'text-gray-600', bgColor: 'bg-gray-100' };
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
 * Tree Node Component
 * Displays a single node in the event tree with expand/collapse functionality
 */
export const TreeNode: FC<TreeNodeProps> = ({
  node,
  onClick,
  selectedEventId,
  defaultExpanded = true,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const { event, children, depth } = node;
  const hasChildren = children.length > 0;
  const isSelected = event.id === selectedEventId;
  const iconConfig = getEventIcon(event.event_type);
  const Icon = iconConfig.icon;

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsExpanded(!isExpanded);
  };

  const handleClick = () => {
    onClick?.(event);
  };

  return (
    <div className="select-none">
      {/* Node content */}
      <div
        className={cn(
          'flex items-center gap-2 py-1.5 px-2 rounded cursor-pointer transition-colors',
          'hover:bg-gray-50',
          isSelected && 'bg-purple-50 ring-1 ring-purple-200'
        )}
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
        onClick={handleClick}
      >
        {/* Tree connector lines */}
        {depth > 0 && (
          <div className="absolute" style={{ left: `${depth * 20 - 12}px` }}>
            <div className="w-4 h-px bg-gray-300" />
          </div>
        )}

        {/* Expand/collapse toggle */}
        {hasChildren ? (
          <button
            onClick={handleToggle}
            className="p-0.5 hover:bg-gray-200 rounded flex-shrink-0"
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-500" />
            )}
          </button>
        ) : (
          <span className="w-5 flex-shrink-0 flex items-center justify-center">
            <Minus className="w-3 h-3 text-gray-300" />
          </span>
        )}

        {/* Event icon */}
        <div className={cn(
          'flex items-center justify-center w-6 h-6 rounded flex-shrink-0',
          iconConfig.bgColor
        )}>
          <Icon className={cn('w-3.5 h-3.5', iconConfig.color)} />
        </div>

        {/* Event type */}
        <span className={cn('text-sm font-medium truncate', iconConfig.color)}>
          {event.event_type}
        </span>

        {/* Timestamp */}
        <span className="text-xs text-gray-400 font-mono ml-auto flex-shrink-0">
          {formatTimestamp(event.timestamp)}
        </span>

        {/* Duration badge */}
        {event.duration_ms !== undefined && event.duration_ms > 0 && (
          <DurationBadge durationMs={event.duration_ms} />
        )}

        {/* Children count */}
        {hasChildren && !isExpanded && (
          <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
            {children.length}
          </span>
        )}
      </div>

      {/* Child nodes (recursive) */}
      {hasChildren && isExpanded && (
        <div className="relative">
          {/* Vertical connector line */}
          <div
            className="absolute w-px bg-gray-200"
            style={{
              left: `${depth * 20 + 18}px`,
              top: 0,
              bottom: '12px',
            }}
          />

          {children.map((child) => (
            <div key={child.event.id} className="relative">
              {/* Horizontal connector line */}
              <div
                className="absolute h-px bg-gray-200"
                style={{
                  left: `${depth * 20 + 18}px`,
                  width: '12px',
                  top: '18px',
                }}
              />
              <TreeNode
                node={child}
                onClick={onClick}
                selectedEventId={selectedEventId}
                defaultExpanded={depth < 2} // Auto-expand first 2 levels
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TreeNode;
