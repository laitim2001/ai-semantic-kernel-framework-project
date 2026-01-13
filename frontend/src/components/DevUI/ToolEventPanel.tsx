// =============================================================================
// IPA Platform - DevUI Tool Event Panel Component
// =============================================================================
// Sprint 88: S88-3 - Event Detail Panels
//
// Specialized panel for displaying Tool event details.
//
// Dependencies:
//   - Lucide React
//   - Tailwind CSS
// =============================================================================

import { FC, useState } from 'react';
import {
  Wrench,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Clock,
  CheckCircle,
  XCircle,
  ArrowRight,
  Code,
} from 'lucide-react';
import type { TraceEvent } from '@/types/devtools';
import { DurationBadge } from './DurationBar';
import { cn } from '@/lib/utils';

interface ToolEventPanelProps {
  /** The Tool event to display */
  event: TraceEvent;
  /** Optional paired event (call/result pair) */
  pairedEvent?: TraceEvent;
}

interface ToolEventData {
  tool_name?: string;
  name?: string;
  function_name?: string;
  arguments?: Record<string, unknown>;
  parameters?: Record<string, unknown>;
  input?: Record<string, unknown>;
  result?: unknown;
  output?: unknown;
  response?: unknown;
  error?: string;
  success?: boolean;
  status?: string;
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
 * JSON viewer with syntax highlighting
 */
const JsonViewer: FC<{
  data: unknown;
  label: string;
  defaultExpanded?: boolean;
}> = ({ data, label, defaultExpanded = false }) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [copied, setCopied] = useState(false);
  const jsonStr = JSON.stringify(data, null, 2);
  const isLarge = jsonStr.length > 300;

  const handleCopy = async () => {
    const success = await copyToClipboard(jsonStr);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b border-gray-200">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="p-1 hover:bg-gray-200 rounded text-gray-500"
            title="Copy to clipboard"
          >
            {copied ? (
              <Check className="w-4 h-4 text-green-500" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
          {isLarge && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 hover:bg-gray-200 rounded text-gray-500"
            >
              {isExpanded ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-3 bg-gray-50/50 overflow-x-auto">
        <pre className="text-sm font-mono text-gray-700">
          {isExpanded || !isLarge
            ? jsonStr
            : jsonStr.slice(0, 300) + '\n...'}
        </pre>
        {!isExpanded && isLarge && (
          <button
            onClick={() => setIsExpanded(true)}
            className="mt-2 text-xs text-purple-600 hover:text-purple-700"
          >
            Show full data
          </button>
        )}
      </div>
    </div>
  );
};

/**
 * Tool Event Panel Component
 * Displays detailed information about Tool call/result events
 */
export const ToolEventPanel: FC<ToolEventPanelProps> = ({ event, pairedEvent: _pairedEvent }) => {
  const data = event.data as ToolEventData;
  const isCall = event.event_type.toUpperCase().includes('CALL');
  const isResult = event.event_type.toUpperCase().includes('RESULT');

  // Extract tool name
  const toolName = data.tool_name || data.name || data.function_name || 'Unknown Tool';

  // Extract arguments/parameters
  const args = data.arguments || data.parameters || data.input;

  // Extract result
  const result = data.result ?? data.output ?? data.response;

  // Determine success status
  const hasError = !!data.error;
  const isSuccess = data.success !== false && !hasError;
  const statusText = data.status || (hasError ? 'Failed' : isSuccess ? 'Success' : 'Unknown');

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className={cn(
          'flex items-center justify-center w-10 h-10 rounded-lg',
          hasError ? 'bg-red-100' : 'bg-green-100'
        )}>
          <Wrench className={cn('w-5 h-5', hasError ? 'text-red-600' : 'text-green-600')} />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900">
            {isCall ? 'Tool Call' : isResult ? 'Tool Result' : 'Tool Event'}
          </h3>
          <p className="text-sm text-gray-500">{event.event_type}</p>
        </div>

        {/* Status badge */}
        {isResult && (
          <div className={cn(
            'flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium',
            hasError ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
          )}>
            {hasError ? (
              <XCircle className="w-4 h-4" />
            ) : (
              <CheckCircle className="w-4 h-4" />
            )}
            {statusText}
          </div>
        )}
      </div>

      {/* Tool info */}
      <div className="p-4 bg-gray-50 rounded-lg space-y-3">
        {/* Tool name */}
        <div className="flex items-center gap-2">
          <Code className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-500">Tool:</span>
          <span className="text-sm font-mono font-medium text-gray-900">{toolName}</span>
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
            <ArrowRight className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-500">Step:</span>
            <span className="text-sm font-mono text-gray-900">{event.step_number}</span>
          </div>
        )}
      </div>

      {/* Arguments (for TOOL_CALL) */}
      {args && Object.keys(args).length > 0 && (
        <JsonViewer
          data={args}
          label="Arguments / Parameters"
          defaultExpanded={JSON.stringify(args).length < 500}
        />
      )}

      {/* Result (for TOOL_RESULT) */}
      {result !== undefined && (
        <JsonViewer
          data={result}
          label="Result / Output"
          defaultExpanded={JSON.stringify(result).length < 500}
        />
      )}

      {/* Error message */}
      {data.error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <XCircle className="w-4 h-4 text-red-600" />
            <span className="text-sm font-medium text-red-900">Error</span>
          </div>
          <pre className="text-sm font-mono text-red-700 whitespace-pre-wrap">
            {data.error}
          </pre>
        </div>
      )}

      {/* Raw data (collapsed by default) */}
      <details className="text-sm">
        <summary className="cursor-pointer text-gray-500 hover:text-gray-700">
          View raw event data
        </summary>
        <pre className="mt-2 p-3 bg-gray-50 rounded text-xs font-mono overflow-x-auto">
          {JSON.stringify(event.data, null, 2)}
        </pre>
      </details>
    </div>
  );
};

export default ToolEventPanel;
