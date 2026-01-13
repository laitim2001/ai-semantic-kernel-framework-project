// =============================================================================
// IPA Platform - DevUI Event List Component
// =============================================================================
// Sprint 87: S87-3 - DevUI Core Pages
//
// Component for displaying a list of trace events with filtering.
//
// Dependencies:
//   - React
//   - DevTools hooks
// =============================================================================

import { FC, useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Filter,
  Search,
  AlertCircle,
  Info,
  AlertTriangle,
  XCircle,
  Bug,
} from 'lucide-react';
import type { TraceEvent, EventSeverity } from '@/types/devtools';
import { EventDetail } from './EventDetail';
import { cn } from '@/lib/utils';

interface EventListProps {
  events: TraceEvent[];
  isLoading?: boolean;
  onEventSelect?: (event: TraceEvent) => void;
  selectedEventId?: string;
}

/**
 * Severity icon mapping
 */
const severityIcons: Record<EventSeverity, React.ComponentType<{ className?: string }>> = {
  debug: Bug,
  info: Info,
  warning: AlertTriangle,
  error: XCircle,
  critical: AlertCircle,
};

/**
 * Severity colors
 */
const severityStyles: Record<EventSeverity, { bg: string; text: string; icon: string }> = {
  debug: { bg: 'bg-gray-50', text: 'text-gray-600', icon: 'text-gray-400' },
  info: { bg: 'bg-blue-50', text: 'text-blue-700', icon: 'text-blue-500' },
  warning: { bg: 'bg-yellow-50', text: 'text-yellow-700', icon: 'text-yellow-500' },
  error: { bg: 'bg-red-50', text: 'text-red-700', icon: 'text-red-500' },
  critical: { bg: 'bg-red-100', text: 'text-red-800', icon: 'text-red-600' },
};

/**
 * Format timestamp for display
 */
function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  const timeStr = date.toLocaleTimeString('zh-TW', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
  // Add milliseconds manually
  const ms = date.getMilliseconds().toString().padStart(3, '0');
  return `${timeStr}.${ms}`;
}

/**
 * Event row component
 */
const EventRow: FC<{
  event: TraceEvent;
  onSelect?: (event: TraceEvent) => void;
  isSelected?: boolean;
}> = ({ event, onSelect, isSelected }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const styles = severityStyles[event.severity];
  const Icon = severityIcons[event.severity];

  const handleClick = () => {
    if (onSelect) {
      onSelect(event);
    } else {
      setIsExpanded(!isExpanded);
    }
  };

  return (
    <div className="border-b border-gray-200 last:border-b-0">
      {/* Event header */}
      <button
        onClick={handleClick}
        className={cn(
          'w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors',
          isExpanded && 'bg-gray-50',
          isSelected && 'bg-purple-50 ring-1 ring-inset ring-purple-200'
        )}
      >
        {/* Expand/Collapse icon */}
        <div className="text-gray-400">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </div>

        {/* Severity icon */}
        <Icon className={cn('w-4 h-4', styles.icon)} />

        {/* Event type */}
        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium text-gray-900">{event.event_type}</span>
        </div>

        {/* Timestamp */}
        <div className="text-xs text-gray-500 font-mono">{formatTime(event.timestamp)}</div>

        {/* Severity badge */}
        <span
          className={cn(
            'px-2 py-0.5 rounded text-xs font-medium',
            styles.bg,
            styles.text
          )}
        >
          {event.severity}
        </span>

        {/* Duration if available */}
        {event.duration_ms !== undefined && (
          <span className="text-xs text-gray-500 w-16 text-right">
            {event.duration_ms}ms
          </span>
        )}
      </button>

      {/* Event details */}
      {isExpanded && (
        <div className="px-4 pb-4">
          <EventDetail event={event} />
        </div>
      )}
    </div>
  );
};

/**
 * Event List Component
 * Displays a filterable list of trace events
 */
export const EventList: FC<EventListProps> = ({
  events,
  isLoading,
  onEventSelect,
  selectedEventId,
}) => {
  const [severityFilter, setSeverityFilter] = useState<EventSeverity | ''>('');
  const [typeFilter, setTypeFilter] = useState('');

  // Filter events
  const filteredEvents = events.filter((event) => {
    if (severityFilter && event.severity !== severityFilter) return false;
    if (typeFilter && !event.event_type.toLowerCase().includes(typeFilter.toLowerCase())) {
      return false;
    }
    return true;
  });

  if (isLoading) {
    return (
      <div className="p-8 text-center text-gray-500">Loading events...</div>
    );
  }

  return (
    <div>
      {/* Filters */}
      <div className="flex items-center gap-4 px-4 py-3 bg-gray-50 border-b border-gray-200">
        <Filter className="w-4 h-4 text-gray-400" />

        {/* Severity filter */}
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value as EventSeverity | '')}
          className="px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500"
        >
          <option value="">All Severities</option>
          <option value="debug">Debug</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="error">Error</option>
          <option value="critical">Critical</option>
        </select>

        {/* Type filter */}
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Filter by event type..."
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="w-full pl-8 pr-3 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
        </div>

        {/* Results count */}
        <span className="text-sm text-gray-500">
          {filteredEvents.length} of {events.length} events
        </span>
      </div>

      {/* Event list */}
      <div className="divide-y divide-gray-200">
        {filteredEvents.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No events match the current filters.
          </div>
        ) : (
          filteredEvents.map((event) => (
            <EventRow
              key={event.id}
              event={event}
              onSelect={onEventSelect}
              isSelected={event.id === selectedEventId}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default EventList;
