/**
 * EventLogPanel - AG-UI Event Log Panel
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-4: AG-UI Demo Page
 *
 * Displays real-time AG-UI events in a scrollable log panel.
 * Supports filtering by event type and expanding event details.
 */

import { FC, useState, useMemo, useRef, useEffect } from 'react';
import type { AGUIEventType } from '@/types/ag-ui';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

export interface EventLogEntry {
  id: string;
  type: AGUIEventType;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface EventLogPanelProps {
  /** Event log entries */
  events: EventLogEntry[];
  /** Maximum entries to display */
  maxEntries?: number;
  /** Auto-scroll to bottom on new events */
  autoScroll?: boolean;
  /** Filter by event types */
  filterTypes?: AGUIEventType[];
  /** Callback when event is clicked */
  onEventClick?: (event: EventLogEntry) => void;
  /** Additional CSS classes */
  className?: string;
}

/** Event type styling */
const eventTypeStyles: Partial<Record<AGUIEventType, { badge: 'default' | 'secondary' | 'destructive' | 'outline'; color: string }>> = {
  RUN_STARTED: { badge: 'default', color: 'text-green-600' },
  RUN_FINISHED: { badge: 'default', color: 'text-blue-600' },
  RUN_ERROR: { badge: 'destructive', color: 'text-red-600' },
  TEXT_MESSAGE_START: { badge: 'secondary', color: 'text-gray-600' },
  TEXT_MESSAGE_CONTENT: { badge: 'outline', color: 'text-gray-500' },
  TEXT_MESSAGE_END: { badge: 'secondary', color: 'text-gray-600' },
  TOOL_CALL_START: { badge: 'default', color: 'text-purple-600' },
  TOOL_CALL_ARGS: { badge: 'outline', color: 'text-purple-500' },
  TOOL_CALL_END: { badge: 'default', color: 'text-purple-600' },
  STATE_SNAPSHOT: { badge: 'secondary', color: 'text-orange-600' },
  STATE_DELTA: { badge: 'outline', color: 'text-orange-500' },
  CUSTOM: { badge: 'secondary', color: 'text-teal-600' },
};

/**
 * EventLogPanel Component
 *
 * Real-time event log display with filtering and expandable details.
 */
export const EventLogPanel: FC<EventLogPanelProps> = ({
  events,
  maxEntries = 100,
  autoScroll = true,
  filterTypes,
  onEventClick,
  className = '',
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Filter and limit events
  const displayEvents = useMemo(() => {
    let filtered = [...events];

    if (filterTypes && filterTypes.length > 0) {
      filtered = filtered.filter((e) => filterTypes.includes(e.type));
    }

    return filtered.slice(-maxEntries);
  }, [events, filterTypes, maxEntries]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && !isPaused && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [displayEvents, autoScroll, isPaused]);

  // Format timestamp
  const formatTime = (timestamp: string): string => {
    try {
      const date = new Date(timestamp);
      const timeStr = date.toLocaleTimeString('zh-TW', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
      // Add milliseconds manually
      const ms = date.getMilliseconds().toString().padStart(3, '0');
      return `${timeStr}.${ms}`;
    } catch {
      return timestamp;
    }
  };

  // Get style for event type
  const getEventStyle = (type: AGUIEventType) => {
    return eventTypeStyles[type] || { badge: 'outline' as const, color: 'text-gray-600' };
  };

  return (
    <div
      className={`flex flex-col h-full bg-gray-900 rounded-lg overflow-hidden ${className}`}
      data-testid="event-log-panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-white">Event Log</span>
          <span className="text-xs text-gray-400">({displayEvents.length})</span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={isPaused ? 'default' : 'outline'}
            size="sm"
            onClick={() => setIsPaused(!isPaused)}
            className="text-xs"
            data-testid="pause-log"
          >
            {isPaused ? '▶ Resume' : '⏸ Pause'}
          </Button>
        </div>
      </div>

      {/* Event List */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-2 space-y-1 font-mono text-xs"
        onMouseEnter={() => setIsPaused(true)}
        onMouseLeave={() => setIsPaused(false)}
      >
        {displayEvents.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            No events yet
          </div>
        ) : (
          displayEvents.map((event) => {
            const style = getEventStyle(event.type);
            const isExpanded = expandedId === event.id;

            return (
              <div
                key={event.id}
                className={`
                  rounded px-2 py-1 cursor-pointer transition-colors
                  ${isExpanded ? 'bg-gray-700' : 'hover:bg-gray-800'}
                `}
                onClick={() => {
                  setExpandedId(isExpanded ? null : event.id);
                  onEventClick?.(event);
                }}
                data-testid={`event-${event.id}`}
              >
                {/* Event Header */}
                <div className="flex items-center gap-2">
                  <span className="text-gray-500">{formatTime(event.timestamp)}</span>
                  <Badge variant={style.badge} className={`text-xs ${style.color}`}>
                    {event.type}
                  </Badge>
                  {!isExpanded && event.data && Object.keys(event.data).length > 0 && (
                    <span className="text-gray-500 truncate">
                      {JSON.stringify(event.data).slice(0, 50)}...
                    </span>
                  )}
                </div>

                {/* Expanded Details */}
                {isExpanded && event.data && (
                  <pre className="mt-2 p-2 bg-gray-800 rounded text-gray-300 overflow-x-auto">
                    {JSON.stringify(event.data, null, 2)}
                  </pre>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default EventLogPanel;
