/**
 * IntentStatusChip - Inline Intent/Risk/Mode Status Component
 *
 * Sprint 138: Phase 40 - Orchestrator Chat Enhancement
 *
 * Displays intent classification, risk level, and execution mode
 * inline within chat messages. Supports expandable detail view.
 */

import { useState } from 'react';
import {
  Brain,
  Shield,
  Zap,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

export interface IntentStatusChipProps {
  /** Intent classification result */
  intent?: string;
  /** Risk level from assessment */
  riskLevel?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  /** Execution mode selected by router */
  executionMode?: string;
  /** Additional detail text (shown when expanded) */
  detail?: string;
  /** Compact mode for small screens */
  compact?: boolean;
}

// =============================================================================
// Risk Level Configuration
// =============================================================================

const riskConfig: Record<
  string,
  { color: string; bgColor: string; label: string }
> = {
  LOW: {
    color: 'text-green-700',
    bgColor: 'bg-green-50 border-green-200',
    label: '低',
  },
  MEDIUM: {
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-50 border-yellow-200',
    label: '中',
  },
  HIGH: {
    color: 'text-orange-700',
    bgColor: 'bg-orange-50 border-orange-200',
    label: '高',
  },
  CRITICAL: {
    color: 'text-red-700',
    bgColor: 'bg-red-50 border-red-200',
    label: '嚴重',
  },
};

// =============================================================================
// Component
// =============================================================================

export function IntentStatusChip({
  intent,
  riskLevel,
  executionMode,
  detail,
  compact = false,
}: IntentStatusChipProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Don't render if no data
  if (!intent && !riskLevel && !executionMode) return null;

  const risk = riskLevel ? riskConfig[riskLevel] : null;
  const hasDetail = !!detail;

  return (
    <div
      className={cn(
        'inline-flex flex-col rounded-lg border border-gray-200 bg-gray-50 text-xs',
        compact ? 'max-w-fit' : 'w-full'
      )}
    >
      {/* Main chip row */}
      <button
        onClick={hasDetail ? () => setIsExpanded(!isExpanded) : undefined}
        className={cn(
          'inline-flex items-center gap-2 px-3 py-1.5 rounded-lg',
          hasDetail && 'cursor-pointer hover:bg-gray-100 transition-colors',
          !hasDetail && 'cursor-default'
        )}
      >
        {/* Intent */}
        {intent && (
          <span className="inline-flex items-center gap-1 text-gray-700">
            <Brain className="h-3 w-3 text-purple-500" />
            {!compact && <span className="text-gray-400">意圖：</span>}
            <span className="font-medium">{intent}</span>
          </span>
        )}

        {/* Separator */}
        {intent && (riskLevel || executionMode) && (
          <span className="text-gray-300">|</span>
        )}

        {/* Risk Level */}
        {riskLevel && risk && (
          <span className="inline-flex items-center gap-1">
            <Shield className={cn('h-3 w-3', risk.color)} />
            {!compact && <span className="text-gray-400">風險：</span>}
            <Badge
              variant="outline"
              className={cn(
                'text-[10px] px-1.5 py-0 h-4 font-medium border',
                risk.bgColor,
                risk.color
              )}
            >
              {risk.label}
            </Badge>
          </span>
        )}

        {/* Separator */}
        {riskLevel && executionMode && (
          <span className="text-gray-300">|</span>
        )}

        {/* Execution Mode */}
        {executionMode && (
          <span className="inline-flex items-center gap-1 text-gray-700">
            <Zap className="h-3 w-3 text-blue-500" />
            {!compact && <span className="text-gray-400">模式：</span>}
            <span className="font-medium">{executionMode}</span>
          </span>
        )}

        {/* Expand toggle */}
        {hasDetail && (
          <span className="ml-auto text-gray-400">
            {isExpanded ? (
              <ChevronUp className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
          </span>
        )}
      </button>

      {/* Expanded detail */}
      {isExpanded && detail && (
        <div className="px-3 py-2 border-t border-gray-200 text-xs text-gray-600 whitespace-pre-wrap">
          {detail}
        </div>
      )}
    </div>
  );
}

export default IntentStatusChip;
