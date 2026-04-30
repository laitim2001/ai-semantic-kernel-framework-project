// =============================================================================
// IPA Platform - DevUI Timeline Component
// =============================================================================
// Sprint 88: S88-1 - Timeline Visualization
//
// Main timeline component for visualizing execution events.
//
// Dependencies:
//   - React
//   - Lucide React
//   - TimelineNode component
// =============================================================================

import { FC, useState, useMemo, useRef, useEffect } from 'react';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Filter,
  Clock,
  LayoutList,
} from 'lucide-react';
import type { TraceEvent } from '@/types/devtools';
import { TimelineNode } from './TimelineNode';
import { cn } from '@/lib/utils';

interface TimelineProps {
  /** List of events to display */
  events: TraceEvent[];
  /** Currently selected event ID */
  selectedEventId?: string;
  /** Event selection handler */
  onEventSelect?: (event: TraceEvent) => void;
  /** Maximum height of timeline container */
  maxHeight?: string;
  /** Show filters */
  showFilters?: boolean;
  /** Enable zoom controls */
  enableZoom?: boolean;
}

/** Event pair types for matching */
const EVENT_PAIRS: Record<string, string> = {
  'WORKFLOW_START': 'WORKFLOW_END',
  'EXECUTOR_START': 'EXECUTOR_END',
  'LLM_REQUEST': 'LLM_RESPONSE',
  'TOOL_CALL': 'TOOL_RESULT',
};

/**
 * Build event pairs mapping
 */
function buildEventPairs(events: TraceEvent[]): Map<string, TraceEvent> {
  const pairs = new Map<string, TraceEvent>();
  const startEvents: Map<string, TraceEvent> = new Map();

  events.forEach(event => {
    const type = event.event_type.toUpperCase();

    // Check if this is a start event
    for (const [startType, endType] of Object.entries(EVENT_PAIRS)) {
      if (type.includes(startType)) {
        // Store as potential start event using parent_event_id or executor_id as key
        const key = `${startType}-${event.parent_event_id || event.executor_id || ''}`;
        startEvents.set(key, event);
      } else if (type.includes(endType)) {
        // Find matching start event
        const startKey = `${startType}-${event.parent_event_id || event.executor_id || ''}`;
        const startEvent = startEvents.get(startKey);
        if (startEvent) {
          pairs.set(startEvent.id, event);
          startEvents.delete(startKey);
        }
      }
    }
  });

  return pairs;
}

/**
 * Calculate max duration from events
 */
function calculateMaxDuration(events: TraceEvent[], pairs: Map<string, TraceEvent>): number {
  let maxDuration = 0;

  events.forEach(event => {
    // Check paired duration
    const pairedEvent = pairs.get(event.id);
    if (pairedEvent) {
      const duration = new Date(pairedEvent.timestamp).getTime() - new Date(event.timestamp).getTime();
      maxDuration = Math.max(maxDuration, duration);
    }
    // Check individual duration
    if (event.duration_ms) {
      maxDuration = Math.max(maxDuration, event.duration_ms);
    }
  });

  return maxDuration || 1000; // Default to 1s if no duration found
}

/**
 * Build hierarchy from events based on parent_event_id
 */
function buildEventHierarchy(events: TraceEvent[]): Map<string, number> {
  const levels = new Map<string, number>();
  const parentLevels = new Map<string | undefined, number>();
  parentLevels.set(undefined, 0);

  // Sort by timestamp first
  const sorted = [...events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  sorted.forEach(event => {
    const parentLevel = parentLevels.get(event.parent_event_id) ?? 0;
    const level = event.parent_event_id ? parentLevel + 1 : 0;
    levels.set(event.id, level);
    parentLevels.set(event.id, level);
  });

  return levels;
}

/**
 * Timeline Component
 * Main timeline visualization for execution events
 */
export const Timeline: FC<TimelineProps> = ({
  events,
  selectedEventId,
  onEventSelect,
  maxHeight = '600px',
  showFilters = true,
  enableZoom = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const [filter, setFilter] = useState<string>('');
  const [viewMode, setViewMode] = useState<'timeline' | 'flat'>('timeline');

  // Build event pairs and hierarchy
  const eventPairs = useMemo(() => buildEventPairs(events), [events]);
  const eventLevels = useMemo(() => buildEventHierarchy(events), [events]);
  const maxDuration = useMemo(
    () => calculateMaxDuration(events, eventPairs),
    [events, eventPairs]
  );

  // Sort and filter events
  const displayEvents = useMemo(() => {
    let filtered = [...events];

    // Apply type filter
    if (filter) {
      filtered = filtered.filter(e =>
        e.event_type.toLowerCase().includes(filter.toLowerCase())
      );
    }

    // Sort by timestamp
    filtered.sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    return filtered;
  }, [events, filter]);

  // Calculate total duration
  const totalDuration = useMemo(() => {
    if (events.length === 0) return 0;
    const sorted = [...events].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
    const first = new Date(sorted[0].timestamp).getTime();
    const last = new Date(sorted[sorted.length - 1].timestamp).getTime();
    return last - first;
  }, [events]);

  // Zoom handlers
  const handleZoomIn = () => setZoom(prev => Math.min(prev + 0.25, 2));
  const handleZoomOut = () => setZoom(prev => Math.max(prev - 0.25, 0.5));
  const handleResetZoom = () => setZoom(1);

  // Scroll to selected event
  useEffect(() => {
    if (selectedEventId && containerRef.current) {
      const element = containerRef.current.querySelector(
        `[data-event-id="${selectedEventId}"]`
      );
      element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [selectedEventId]);

  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-gray-500">
        <Clock className="w-12 h-12 mb-2 text-gray-300" />
        <p>No events to display</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-4">
          {/* Event count */}
          <span className="text-sm text-gray-600">
            {displayEvents.length} events
          </span>

          {/* Total duration */}
          <span className="text-sm text-gray-500">
            Total: {totalDuration < 1000
              ? `${totalDuration}ms`
              : `${(totalDuration / 1000).toFixed(2)}s`
            }
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Filter input */}
          {showFilters && (
            <div className="relative">
              <Filter className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Filter events..."
                value={filter}
                onChange={e => setFilter(e.target.value)}
                className="pl-8 pr-3 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500 w-40"
              />
            </div>
          )}

          {/* View mode toggle */}
          <button
            onClick={() => setViewMode(viewMode === 'timeline' ? 'flat' : 'timeline')}
            className={cn(
              'p-1.5 rounded hover:bg-gray-200',
              viewMode === 'flat' && 'bg-gray-200'
            )}
            title={viewMode === 'timeline' ? 'Flat view' : 'Timeline view'}
          >
            <LayoutList className="w-4 h-4 text-gray-600" />
          </button>

          {/* Zoom controls */}
          {enableZoom && (
            <>
              <button
                onClick={handleZoomOut}
                className="p-1.5 rounded hover:bg-gray-200"
                title="Zoom out"
              >
                <ZoomOut className="w-4 h-4 text-gray-600" />
              </button>
              <span className="text-xs text-gray-500 w-12 text-center">
                {Math.round(zoom * 100)}%
              </span>
              <button
                onClick={handleZoomIn}
                className="p-1.5 rounded hover:bg-gray-200"
                title="Zoom in"
              >
                <ZoomIn className="w-4 h-4 text-gray-600" />
              </button>
              <button
                onClick={handleResetZoom}
                className="p-1.5 rounded hover:bg-gray-200"
                title="Reset zoom"
              >
                <Maximize2 className="w-4 h-4 text-gray-600" />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Timeline content */}
      <div
        ref={containerRef}
        className="overflow-auto"
        style={{ maxHeight, transform: `scale(${zoom})`, transformOrigin: 'top left' }}
      >
        <div className="p-4 space-y-1" style={{ width: `${100 / zoom}%` }}>
          {displayEvents.map(event => (
            <div key={event.id} data-event-id={event.id}>
              <TimelineNode
                event={event}
                isPaired={eventPairs.has(event.id)}
                pairedEvent={eventPairs.get(event.id)}
                maxDurationMs={maxDuration}
                onClick={onEventSelect}
                isSelected={event.id === selectedEventId}
                indentLevel={viewMode === 'timeline' ? (eventLevels.get(event.id) || 0) : 0}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Footer with legend */}
      <div className="flex items-center gap-4 px-4 py-2 border-t border-gray-200 bg-gray-50 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-blue-500" />
          Workflow
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-purple-500" />
          LLM
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-green-500" />
          Tool
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-red-500" />
          Error
        </span>
      </div>
    </div>
  );
};

export default Timeline;
