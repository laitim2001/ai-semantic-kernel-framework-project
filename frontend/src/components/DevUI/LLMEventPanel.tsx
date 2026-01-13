// =============================================================================
// IPA Platform - DevUI LLM Event Panel Component
// =============================================================================
// Sprint 88: S88-3 - Event Detail Panels
//
// Specialized panel for displaying LLM event details.
//
// Dependencies:
//   - Lucide React
//   - Tailwind CSS
// =============================================================================

import { FC, useState } from 'react';
import {
  Bot,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  MessageSquare,
  Sparkles,
  Clock,
  Hash,
} from 'lucide-react';
import type { TraceEvent } from '@/types/devtools';
import { DurationBadge } from './DurationBar';

interface LLMEventPanelProps {
  /** The LLM event to display */
  event: TraceEvent;
  /** Optional paired event (request/response pair) */
  pairedEvent?: TraceEvent;
}

interface LLMEventData {
  model?: string;
  prompt?: string;
  messages?: Array<{ role: string; content: string }>;
  response?: string;
  content?: string;
  completion?: string;
  tokens?: {
    prompt?: number;
    completion?: number;
    total?: number;
  };
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
  temperature?: number;
  max_tokens?: number;
  stop_reason?: string;
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
 * Collapsible text section
 */
const CollapsibleText: FC<{
  label: string;
  text: string;
  defaultExpanded?: boolean;
  maxPreviewLength?: number;
}> = ({ label, text, defaultExpanded = false, maxPreviewLength = 200 }) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [copied, setCopied] = useState(false);
  const needsExpand = text.length > maxPreviewLength;

  const handleCopy = async () => {
    const success = await copyToClipboard(text);
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
          {needsExpand && (
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
      <div className="p-3 bg-gray-50/50">
        <pre className="text-sm font-mono text-gray-700 whitespace-pre-wrap break-words">
          {isExpanded || !needsExpand
            ? text
            : text.slice(0, maxPreviewLength) + '...'}
        </pre>
        {!isExpanded && needsExpand && (
          <button
            onClick={() => setIsExpanded(true)}
            className="mt-2 text-xs text-purple-600 hover:text-purple-700"
          >
            Show more ({text.length - maxPreviewLength} more characters)
          </button>
        )}
      </div>
    </div>
  );
};

/**
 * Token usage display
 */
const TokenUsage: FC<{
  prompt?: number;
  completion?: number;
  total?: number;
}> = ({ prompt, completion, total }) => {
  if (!prompt && !completion && !total) return null;

  return (
    <div className="flex items-center gap-4 text-sm">
      {prompt !== undefined && (
        <div className="flex items-center gap-1.5">
          <span className="text-gray-500">Prompt:</span>
          <span className="font-mono text-gray-700">{prompt.toLocaleString()}</span>
        </div>
      )}
      {completion !== undefined && (
        <div className="flex items-center gap-1.5">
          <span className="text-gray-500">Completion:</span>
          <span className="font-mono text-gray-700">{completion.toLocaleString()}</span>
        </div>
      )}
      {total !== undefined && (
        <div className="flex items-center gap-1.5">
          <span className="text-gray-500">Total:</span>
          <span className="font-mono font-medium text-gray-900">{total.toLocaleString()}</span>
        </div>
      )}
    </div>
  );
};

/**
 * LLM Event Panel Component
 * Displays detailed information about LLM request/response events
 */
export const LLMEventPanel: FC<LLMEventPanelProps> = ({ event, pairedEvent: _pairedEvent }) => {
  const data = event.data as LLMEventData;
  const isRequest = event.event_type.toUpperCase().includes('REQUEST');
  const isResponse = event.event_type.toUpperCase().includes('RESPONSE');

  // Extract prompt/response content
  const prompt = data.prompt ||
    (data.messages?.map(m => `[${m.role}]: ${m.content}`).join('\n\n')) ||
    '';
  const response = data.response || data.content || data.completion || '';

  // Extract token usage (handle both naming conventions)
  const tokens = data.tokens || data.usage;
  const tokenInfo = tokens ? {
    prompt: (tokens as { prompt?: number }).prompt ??
            (tokens as { prompt_tokens?: number }).prompt_tokens,
    completion: (tokens as { completion?: number }).completion ??
                (tokens as { completion_tokens?: number }).completion_tokens,
    total: (tokens as { total?: number }).total ??
           (tokens as { total_tokens?: number }).total_tokens,
  } : undefined;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-purple-100">
          <Bot className="w-5 h-5 text-purple-600" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            {isRequest ? 'LLM Request' : isResponse ? 'LLM Response' : 'LLM Event'}
          </h3>
          <p className="text-sm text-gray-500">{event.event_type}</p>
        </div>
      </div>

      {/* Meta information */}
      <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
        {/* Model */}
        {data.model && (
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-500">Model:</span>
            <span className="text-sm font-medium text-gray-900">{data.model}</span>
          </div>
        )}

        {/* Duration */}
        {event.duration_ms !== undefined && (
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-500">Duration:</span>
            <DurationBadge durationMs={event.duration_ms} />
          </div>
        )}

        {/* Temperature */}
        {data.temperature !== undefined && (
          <div className="flex items-center gap-2">
            <Hash className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-500">Temperature:</span>
            <span className="text-sm font-mono text-gray-900">{data.temperature}</span>
          </div>
        )}

        {/* Max tokens */}
        {data.max_tokens !== undefined && (
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-500">Max tokens:</span>
            <span className="text-sm font-mono text-gray-900">{data.max_tokens}</span>
          </div>
        )}
      </div>

      {/* Token usage */}
      {tokenInfo && (
        <div className="p-4 bg-purple-50 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <Hash className="w-4 h-4 text-purple-600" />
            <span className="text-sm font-medium text-purple-900">Token Usage</span>
          </div>
          <TokenUsage
            prompt={tokenInfo.prompt}
            completion={tokenInfo.completion}
            total={tokenInfo.total}
          />
        </div>
      )}

      {/* Prompt content */}
      {prompt && (
        <CollapsibleText
          label="Prompt / Messages"
          text={prompt}
          defaultExpanded={prompt.length < 500}
        />
      )}

      {/* Response content */}
      {response && (
        <CollapsibleText
          label="Response"
          text={response}
          defaultExpanded={response.length < 500}
        />
      )}

      {/* Stop reason */}
      {data.stop_reason && (
        <div className="text-sm text-gray-500">
          Stop reason: <span className="font-mono">{data.stop_reason}</span>
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

export default LLMEventPanel;
