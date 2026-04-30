/**
 * ConversationLog Component
 *
 * Scrollable timeline showing all agent team events in chronological order.
 * Each event has a colored icon based on type:
 *   thinking=Brain, tool_call=Wrench, message=MessageCircle,
 *   task=CheckCircle, inbox=Inbox, approval=ShieldAlert, system=Info
 *
 * Phase 45: Sprint E — Conversation Log Frontend (Plan Phase 10)
 */

import { FC, useState, useRef, useEffect } from 'react';
import {
  Brain,
  Wrench,
  MessageCircle,
  CheckCircle,
  Inbox,
  ShieldAlert,
  Info,
  ChevronDown,
  ChevronUp,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AgentEvent, AgentEventType } from './types';

// =============================================================================
// Constants
// =============================================================================

interface EventConfig {
  icon: LucideIcon;
  color: string;
  bgColor: string;
  borderColor: string;
  label: string;
}

const EVENT_CONFIG: Record<AgentEventType, EventConfig> = {
  thinking: {
    icon: Brain,
    color: 'text-purple-600 dark:text-purple-400',
    bgColor: 'bg-purple-50 dark:bg-purple-900/20',
    borderColor: 'border-l-purple-400',
    label: 'Thinking',
  },
  tool_call: {
    icon: Wrench,
    color: 'text-orange-600 dark:text-orange-400',
    bgColor: 'bg-orange-50 dark:bg-orange-900/20',
    borderColor: 'border-l-orange-400',
    label: 'Tool Call',
  },
  message: {
    icon: MessageCircle,
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    borderColor: 'border-l-blue-400',
    label: 'Message',
  },
  inbox: {
    icon: Inbox,
    color: 'text-cyan-600 dark:text-cyan-400',
    bgColor: 'bg-cyan-50 dark:bg-cyan-900/20',
    borderColor: 'border-l-cyan-400',
    label: 'Inbox',
  },
  task_completed: {
    icon: CheckCircle,
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-50 dark:bg-green-900/20',
    borderColor: 'border-l-green-400',
    label: 'Task Done',
  },
  approval: {
    icon: ShieldAlert,
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-50 dark:bg-red-900/20',
    borderColor: 'border-l-red-400',
    label: 'Approval',
  },
  system: {
    icon: Info,
    color: 'text-gray-600 dark:text-gray-400',
    bgColor: 'bg-gray-50 dark:bg-gray-900/20',
    borderColor: 'border-l-gray-400',
    label: 'System',
  },
};

// =============================================================================
// Props
// =============================================================================

export interface ConversationLogProps {
  events: AgentEvent[];
  maxHeight?: string;
  className?: string;
}

// =============================================================================
// Helper: format absolute time
// =============================================================================

function formatTime(timestamp: string): string {
  try {
    const d = new Date(timestamp);
    if (isNaN(d.getTime())) return timestamp;
    return d.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return timestamp;
  }
}

// =============================================================================
// Single Event Row
// =============================================================================

const CONTENT_PREVIEW_LIMIT = 80;

const EventRow: FC<{ event: AgentEvent }> = ({ event }) => {
  const config = EVENT_CONFIG[event.type] || EVENT_CONFIG.system;
  const Icon = config.icon;
  const isLong = event.content.length > CONTENT_PREVIEW_LIMIT;
  const [expanded, setExpanded] = useState(false);

  const displayContent = expanded || !isLong
    ? event.content
    : event.content.substring(0, CONTENT_PREVIEW_LIMIT) + '...';

  return (
    <div className={cn(
      'flex items-start gap-2.5 px-2 py-2 rounded-md text-xs border-l-2',
      config.borderColor,
      'hover:bg-muted/50 transition-colors',
    )}>
      {/* Icon */}
      <div className={cn(
        'flex-shrink-0 mt-0.5 p-1 rounded',
        config.bgColor,
      )}>
        <Icon className={cn('h-3.5 w-3.5', config.color)} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Header: agent name + type badge + time */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className={cn('font-semibold text-[11px]', config.color)}>
            {event.agentName}
          </span>
          <span className={cn(
            'text-[9px] px-1.5 py-0.5 rounded-full font-medium',
            config.bgColor, config.color,
          )}>
            {config.label}
          </span>
          <span className="text-muted-foreground ml-auto flex-shrink-0 text-[10px] font-mono">
            {formatTime(event.timestamp)}
          </span>
        </div>

        {/* Content body */}
        <p className="text-foreground/80 mt-1 whitespace-pre-wrap break-words leading-relaxed text-[11px]">
          {displayContent}
        </p>

        {/* Expand/collapse for long content */}
        {isLong && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-1 flex items-center gap-0.5 text-[10px] text-primary hover:underline"
          >
            {expanded ? (
              <><ChevronUp className="h-3 w-3" /> Collapse</>
            ) : (
              <><ChevronDown className="h-3 w-3" /> Show more</>
            )}
          </button>
        )}
      </div>
    </div>
  );
};

// =============================================================================
// Main Component
// =============================================================================

/**
 * ConversationLog - Scrollable timeline of agent team events
 *
 * @param events - Chronological list of AgentEvent objects
 * @param maxHeight - CSS max-height for the scrollable area (default: "400px")
 * @param className - Additional CSS classes
 */
export const ConversationLog: FC<ConversationLogProps> = ({
  events,
  maxHeight = '400px',
  className,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length]);

  if (events.length === 0) {
    return (
      <div className={cn('text-center text-xs text-muted-foreground py-4', className)}>
        No events yet — activity will appear here during team execution
      </div>
    );
  }

  return (
    <div className={cn('space-y-1.5', className)}>
      <div className="flex items-center justify-between px-1">
        <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          Conversation Log
        </h4>
        <span className="text-[10px] text-muted-foreground">
          {events.length} events
        </span>
      </div>
      <div
        ref={scrollRef}
        className="overflow-y-auto space-y-1 scrollbar-thin"
        style={{ maxHeight }}
      >
        {events.map((event) => (
          <EventRow key={event.id} event={event} />
        ))}
      </div>
    </div>
  );
};

export default ConversationLog;
