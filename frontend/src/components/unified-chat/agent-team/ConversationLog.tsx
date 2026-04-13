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

import { FC, useRef, useEffect } from 'react';
import {
  Brain,
  Wrench,
  MessageCircle,
  CheckCircle,
  Inbox,
  ShieldAlert,
  Info,
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
  label: string;
}

const EVENT_CONFIG: Record<AgentEventType, EventConfig> = {
  thinking: {
    icon: Brain,
    color: 'text-purple-500',
    bgColor: 'bg-purple-50 dark:bg-purple-900/20',
    label: 'Thinking',
  },
  tool_call: {
    icon: Wrench,
    color: 'text-orange-500',
    bgColor: 'bg-orange-50 dark:bg-orange-900/20',
    label: 'Tool Call',
  },
  message: {
    icon: MessageCircle,
    color: 'text-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    label: 'Message',
  },
  inbox: {
    icon: Inbox,
    color: 'text-cyan-500',
    bgColor: 'bg-cyan-50 dark:bg-cyan-900/20',
    label: 'Inbox',
  },
  task_completed: {
    icon: CheckCircle,
    color: 'text-green-500',
    bgColor: 'bg-green-50 dark:bg-green-900/20',
    label: 'Task Done',
  },
  approval: {
    icon: ShieldAlert,
    color: 'text-red-500',
    bgColor: 'bg-red-50 dark:bg-red-900/20',
    label: 'Approval',
  },
  system: {
    icon: Info,
    color: 'text-gray-500',
    bgColor: 'bg-gray-50 dark:bg-gray-900/20',
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
// Helper: format relative time
// =============================================================================

function formatRelativeTime(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime();
  if (diff < 1000) return 'now';
  if (diff < 60_000) return `${Math.floor(diff / 1000)}s ago`;
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  return new Date(timestamp).toLocaleTimeString();
}

// =============================================================================
// Single Event Row
// =============================================================================

const EventRow: FC<{ event: AgentEvent }> = ({ event }) => {
  const config = EVENT_CONFIG[event.type] || EVENT_CONFIG.system;
  const Icon = config.icon;

  return (
    <div className={cn(
      'flex items-start gap-2 px-2 py-1.5 rounded-md text-xs',
      'hover:bg-muted/50 transition-colors',
    )}>
      {/* Icon */}
      <div className={cn(
        'flex-shrink-0 mt-0.5 p-1 rounded',
        config.bgColor,
      )}>
        <Icon className={cn('h-3 w-3', config.color)} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="font-medium text-foreground truncate max-w-[120px]">
            {event.agentName}
          </span>
          <span className={cn('text-[10px] px-1 rounded', config.bgColor, config.color)}>
            {config.label}
          </span>
          <span className="text-muted-foreground ml-auto flex-shrink-0 text-[10px]">
            {formatRelativeTime(event.timestamp)}
          </span>
        </div>
        <p className="text-muted-foreground truncate mt-0.5">
          {event.content}
        </p>
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
 * @param maxHeight - CSS max-height for the scrollable area (default: "300px")
 * @param className - Additional CSS classes
 */
export const ConversationLog: FC<ConversationLogProps> = ({
  events,
  maxHeight = '300px',
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
    <div className={cn('space-y-1', className)}>
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
        className="overflow-y-auto space-y-0.5"
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
