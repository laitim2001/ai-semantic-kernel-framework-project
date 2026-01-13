// =============================================================================
// IPA Platform - DevUI Event Panel Component
// =============================================================================
// Sprint 88: S88-3 - Event Detail Panels
//
// Factory component that renders appropriate panel based on event type.
//
// Dependencies:
//   - React
//   - LLMEventPanel
//   - ToolEventPanel
//   - Lucide React
// =============================================================================

import { FC, useState } from 'react';
import {
  X,
  Copy,
  Check,
  Clock,
  Tag,
  Hash,
  Settings,
  AlertTriangle,
  Info,
} from 'lucide-react';
import type { TraceEvent } from '@/types/devtools';
import { LLMEventPanel } from './LLMEventPanel';
import { ToolEventPanel } from './ToolEventPanel';
import { DurationBadge } from './DurationBar';
import { cn } from '@/lib/utils';

interface EventPanelProps {
  /** The event to display */
  event: TraceEvent;
  /** Optional paired event */
  pairedEvent?: TraceEvent;
  /** Close handler */
  onClose?: () => void;
  /** Full screen mode */
  fullScreen?: boolean;
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * Get severity configuration
 */
function getSeverityConfig(severity: string) {
  switch (severity) {
    case 'critical':
    case 'error':
      return { color: 'text-red-600', bg: 'bg-red-100', icon: AlertTriangle };
    case 'warning':
      return { color: 'text-yellow-600', bg: 'bg-yellow-100', icon: AlertTriangle };
    case 'info':
      return { color: 'text-blue-600', bg: 'bg-blue-100', icon: Info };
    default:
      return { color: 'text-gray-600', bg: 'bg-gray-100', icon: Info };
  }
}

/**
 * Default Event Panel for generic events
 */
const DefaultEventPanel: FC<{ event: TraceEvent }> = ({ event }) => {
  const severityConfig = getSeverityConfig(event.severity);
  const SeverityIcon = severityConfig.icon;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-gray-100">
          <Settings className="w-5 h-5 text-gray-600" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{event.event_type}</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className={cn(
              'inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded',
              severityConfig.bg,
              severityConfig.color
            )}>
              <SeverityIcon className="w-3 h-3" />
              {event.severity}
            </span>
          </div>
        </div>
      </div>

      {/* Meta info */}
      <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
        {/* Timestamp */}
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-500">Time:</span>
          <span className="text-sm text-gray-900">{formatTimestamp(event.timestamp)}</span>
        </div>

        {/* Duration */}
        {event.duration_ms !== undefined && (
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-500">Duration:</span>
            <DurationBadge durationMs={event.duration_ms} />
          </div>
        )}

        {/* Step number */}
        {event.step_number !== undefined && (
          <div className="flex items-center gap-2">
            <Hash className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-500">Step:</span>
            <span className="text-sm font-mono text-gray-900">{event.step_number}</span>
          </div>
        )}

        {/* Executor ID */}
        {event.executor_id && (
          <div className="flex items-center gap-2 col-span-2">
            <Settings className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-500">Executor:</span>
            <span className="text-sm font-mono text-gray-900 truncate" title={event.executor_id}>
              {event.executor_id}
            </span>
          </div>
        )}
      </div>

      {/* Tags */}
      {event.tags.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <Tag className="w-4 h-4 text-gray-400" />
          {event.tags.map((tag, index) => (
            <span
              key={index}
              className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Event data */}
      {Object.keys(event.data).length > 0 && (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <div className="px-3 py-2 bg-gray-50 border-b border-gray-200">
            <span className="text-sm font-medium text-gray-700">Event Data</span>
          </div>
          <pre className="p-3 text-sm font-mono text-gray-700 overflow-x-auto bg-gray-50/50">
            {JSON.stringify(event.data, null, 2)}
          </pre>
        </div>
      )}

      {/* Metadata */}
      {Object.keys(event.metadata).length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer text-gray-500 hover:text-gray-700">
            View metadata
          </summary>
          <pre className="mt-2 p-3 bg-gray-50 rounded text-xs font-mono overflow-x-auto">
            {JSON.stringify(event.metadata, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
};

/**
 * Event Panel Component
 * Factory that renders appropriate panel based on event type
 */
export const EventPanel: FC<EventPanelProps> = ({
  event,
  pairedEvent,
  onClose,
  fullScreen = false,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopyId = async () => {
    const success = await copyToClipboard(event.id);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Determine which panel to render
  const eventType = event.event_type.toUpperCase();
  const isLLMEvent = eventType.includes('LLM');
  const isToolEvent = eventType.includes('TOOL');

  return (
    <div className={cn(
      'bg-white rounded-lg border border-gray-200 overflow-hidden',
      fullScreen ? 'fixed inset-4 z-50 shadow-2xl' : ''
    )}>
      {/* Panel header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-gray-900">Event Details</h2>
          <button
            onClick={handleCopyId}
            className="flex items-center gap-1 px-2 py-0.5 text-xs text-gray-500 hover:text-gray-700 bg-gray-100 rounded"
            title="Copy event ID"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-green-500" />
                Copied
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                {event.id.slice(0, 8)}...
              </>
            )}
          </button>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-200 rounded"
            title="Close"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        )}
      </div>

      {/* Panel content */}
      <div className={cn(
        'p-4 overflow-auto',
        fullScreen ? 'h-[calc(100%-56px)]' : 'max-h-[600px]'
      )}>
        {isLLMEvent ? (
          <LLMEventPanel event={event} pairedEvent={pairedEvent} />
        ) : isToolEvent ? (
          <ToolEventPanel event={event} pairedEvent={pairedEvent} />
        ) : (
          <DefaultEventPanel event={event} />
        )}
      </div>
    </div>
  );
};

export default EventPanel;
