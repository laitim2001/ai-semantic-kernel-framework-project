/**
 * ExtendedThinkingPanel Component
 *
 * Panel for displaying Claude's Extended Thinking content.
 * Shows thinking blocks with token counts, timestamps, and auto-scroll.
 *
 * Sprint 104: ExtendedThinking + 工具調用展示優化
 */

import { FC, useState, useRef, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ScrollArea } from '@/components/ui/ScrollArea';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/Collapsible';
import { Brain, ChevronDown, ChevronUp, Clock, Hash } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ThinkingContent } from './types';

// =============================================================================
// Types
// =============================================================================

interface ExtendedThinkingPanelProps {
  /** Array of thinking content blocks */
  thinkingHistory: ThinkingContent[];
  /** Maximum height of the scrollable area (px) */
  maxHeight?: number;
  /** Whether the panel is expanded by default */
  defaultExpanded?: boolean;
  /** Whether to auto-scroll to latest content */
  autoScroll?: boolean;
  /** Optional class name */
  className?: string;
}

interface ThinkingBlockProps {
  /** The thinking content */
  thinking: ThinkingContent;
  /** Block index (0-based) */
  index: number;
  /** Whether this is the latest block */
  isLatest: boolean;
}

// =============================================================================
// ThinkingBlock Sub-component
// =============================================================================

/**
 * Single thinking block display
 */
const ThinkingBlock: FC<ThinkingBlockProps> = ({ thinking, index, isLatest }) => {
  return (
    <div
      className={cn(
        'p-3 rounded-lg',
        'bg-purple-50 dark:bg-purple-950/20',
        'border border-purple-100 dark:border-purple-900',
        isLatest && 'ring-2 ring-purple-300 dark:ring-purple-700',
      )}
    >
      {/* Block header */}
      <div className="flex items-center justify-between mb-2">
        <Badge variant="outline" className="text-xs font-normal">
          Block {index + 1}
        </Badge>
        {thinking.tokenCount !== undefined && thinking.tokenCount > 0 && (
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Hash className="h-3 w-3" />
            {thinking.tokenCount} tokens
          </span>
        )}
      </div>

      {/* Thinking content */}
      <div className="text-sm whitespace-pre-wrap leading-relaxed text-gray-700 dark:text-gray-300">
        {thinking.content}
      </div>

      {/* Timestamp */}
      {thinking.timestamp && (
        <div className="mt-2 text-xs text-muted-foreground flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {formatTimestamp(thinking.timestamp)}
        </div>
      )}
    </div>
  );
};

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Format ISO timestamp to locale time string
 */
function formatTimestamp(isoString: string): string {
  try {
    return new Date(isoString).toLocaleTimeString();
  } catch {
    return isoString;
  }
}

// =============================================================================
// ExtendedThinkingPanel Component
// =============================================================================

/**
 * ExtendedThinkingPanel - Display Claude's Extended Thinking content
 *
 * Features:
 * - Collapsible panel with expand/collapse
 * - Auto-scroll to latest thinking content
 * - Token count aggregation
 * - Visual indication for latest block
 *
 * @param thinkingHistory - Array of thinking content blocks
 * @param maxHeight - Maximum height of scrollable area (default: 300)
 * @param defaultExpanded - Whether expanded by default (default: true)
 * @param autoScroll - Whether to auto-scroll to latest (default: true)
 * @param className - Additional CSS classes
 */
export const ExtendedThinkingPanel: FC<ExtendedThinkingPanelProps> = ({
  thinkingHistory,
  maxHeight = 300,
  defaultExpanded = true,
  autoScroll = true,
  className,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Calculate total tokens
  const totalTokens = useMemo(() => {
    return thinkingHistory.reduce(
      (sum, thinking) => sum + (thinking.tokenCount || 0),
      0
    );
  }, [thinkingHistory]);

  // Get latest thinking for timestamp display
  const latestThinking = thinkingHistory[thinkingHistory.length - 1];

  // Auto-scroll to bottom when new content arrives
  useEffect(() => {
    if (autoScroll && scrollRef.current && isExpanded) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [thinkingHistory, autoScroll, isExpanded]);

  // Don't render if no thinking content
  if (thinkingHistory.length === 0) {
    return null;
  }

  return (
    <Card className={cn('overflow-hidden', className)}>
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CardHeader className="pb-2 pt-3 px-4">
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              className="w-full justify-between p-0 h-auto hover:bg-transparent"
            >
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 text-purple-500" />
                <CardTitle className="text-sm font-medium">
                  思考過程 (Extended Thinking)
                </CardTitle>
                <Badge variant="secondary" className="text-xs">
                  {thinkingHistory.length} {thinkingHistory.length === 1 ? 'block' : 'blocks'}
                </Badge>
              </div>
              {isExpanded ? (
                <ChevronUp className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              )}
            </Button>
          </CollapsibleTrigger>
        </CardHeader>

        <CollapsibleContent>
          <CardContent className="pt-0 px-4 pb-3">
            {/* Scrollable thinking blocks */}
            <ScrollArea
              className="pr-3"
              style={{ maxHeight }}
            >
              <div ref={scrollRef} className="space-y-3">
                {thinkingHistory.map((thinking, index) => (
                  <ThinkingBlock
                    key={index}
                    thinking={thinking}
                    index={index}
                    isLatest={index === thinkingHistory.length - 1}
                  />
                ))}
              </div>
            </ScrollArea>

            {/* Statistics footer */}
            <div className="flex items-center justify-between mt-3 pt-3 border-t text-xs text-muted-foreground">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1">
                  <Hash className="h-3 w-3" />
                  <span>Total: {totalTokens} tokens</span>
                </div>
                {latestThinking?.timestamp && (
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    <span>Updated: {formatTimestamp(latestThinking.timestamp)}</span>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
};

export default ExtendedThinkingPanel;
