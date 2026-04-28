// =============================================================================
// IPA Platform - DevUI Event Detail Component
// =============================================================================
// Sprint 87: S87-3 - DevUI Core Pages
//
// Component for displaying detailed event information with JSON data.
//
// Dependencies:
//   - React
// =============================================================================

import { FC, useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Clock,
  Hash,
  Tag,
  FileJson,
} from 'lucide-react';
import type { TraceEvent } from '@/types/devtools';

interface EventDetailProps {
  event: TraceEvent;
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const formatted = date.toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
  // Add milliseconds manually
  const ms = date.getMilliseconds().toString().padStart(3, '0');
  return `${formatted}.${ms}`;
}

/**
 * JSON viewer component
 */
const JsonViewer: FC<{ data: Record<string, unknown>; label: string }> = ({ data, label }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const isEmpty = Object.keys(data).length === 0;

  if (isEmpty) {
    return (
      <div className="text-sm text-gray-400 italic">No {label.toLowerCase()}</div>
    );
  }

  return (
    <div>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
      >
        {isExpanded ? (
          <ChevronDown className="w-4 h-4" />
        ) : (
          <ChevronRight className="w-4 h-4" />
        )}
        <FileJson className="w-4 h-4" />
        <span>{label}</span>
        <span className="text-gray-400">({Object.keys(data).length} keys)</span>
      </button>
      {isExpanded && (
        <pre className="mt-2 p-3 bg-gray-900 text-gray-100 rounded-lg text-xs overflow-x-auto">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
};

/**
 * Event Detail Component
 * Displays detailed information about a single trace event
 */
export const EventDetail: FC<EventDetailProps> = ({ event }) => {
  return (
    <div className="bg-gray-50 rounded-lg p-4 space-y-4">
      {/* Header info */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <div className="text-xs text-gray-500 mb-1 flex items-center gap-1">
            <Hash className="w-3 h-3" />
            Event ID
          </div>
          <div className="text-sm font-mono text-gray-900">{event.id.slice(0, 12)}...</div>
        </div>
        <div>
          <div className="text-xs text-gray-500 mb-1 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Timestamp
          </div>
          <div className="text-sm text-gray-900">{formatTimestamp(event.timestamp)}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500 mb-1">Duration</div>
          <div className="text-sm text-gray-900">
            {event.duration_ms !== undefined ? `${event.duration_ms}ms` : '-'}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 mb-1">Step Number</div>
          <div className="text-sm text-gray-900">{event.step_number ?? '-'}</div>
        </div>
      </div>

      {/* Parent and Executor info */}
      {(event.parent_event_id || event.executor_id) && (
        <div className="grid grid-cols-2 gap-4">
          {event.parent_event_id && (
            <div>
              <div className="text-xs text-gray-500 mb-1">Parent Event</div>
              <div className="text-sm font-mono text-gray-900">
                {event.parent_event_id.slice(0, 12)}...
              </div>
            </div>
          )}
          {event.executor_id && (
            <div>
              <div className="text-xs text-gray-500 mb-1">Executor ID</div>
              <div className="text-sm font-mono text-gray-900">{event.executor_id}</div>
            </div>
          )}
        </div>
      )}

      {/* Tags */}
      {event.tags.length > 0 && (
        <div>
          <div className="text-xs text-gray-500 mb-2 flex items-center gap-1">
            <Tag className="w-3 h-3" />
            Tags
          </div>
          <div className="flex flex-wrap gap-1">
            {event.tags.map((tag, index) => (
              <span
                key={index}
                className="px-2 py-0.5 bg-gray-200 text-gray-700 rounded text-xs"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Data and Metadata */}
      <div className="space-y-3 pt-2 border-t border-gray-200">
        <JsonViewer data={event.data} label="Event Data" />
        <JsonViewer data={event.metadata} label="Metadata" />
      </div>
    </div>
  );
};

export default EventDetail;
