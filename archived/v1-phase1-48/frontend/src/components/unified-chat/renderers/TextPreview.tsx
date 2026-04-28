/**
 * TextPreview Component
 *
 * Sprint 76: File Download Feature
 * Phase 20: File Attachment Support
 *
 * Displays text files with basic formatting.
 */

import { FC, useState, useCallback, useMemo } from 'react';
import { Copy, Check, ChevronDown, ChevronUp, Download, FileText, Search } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

export interface TextPreviewProps {
  content: string;
  filename?: string;
  maxLines?: number;
  searchable?: boolean;
  onDownload?: () => void;
  className?: string;
}

// =============================================================================
// TextPreview Component
// =============================================================================

export const TextPreview: FC<TextPreviewProps> = ({
  content,
  filename,
  maxLines = 30,
  searchable = false,
  onDownload,
  className,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  const lines = useMemo(() => content.split('\n'), [content]);
  const totalLines = lines.length;
  const shouldTruncate = totalLines > maxLines;

  // Filter lines based on search query
  const filteredContent = useMemo(() => {
    if (!searchQuery.trim()) {
      if (!shouldTruncate || isExpanded) {
        return content;
      }
      return lines.slice(0, maxLines).join('\n');
    }

    const query = searchQuery.toLowerCase();
    const matchingLines = lines.filter((line) => line.toLowerCase().includes(query));
    return matchingLines.join('\n');
  }, [content, lines, searchQuery, maxLines, shouldTruncate, isExpanded]);

  const matchCount = useMemo(() => {
    if (!searchQuery.trim()) return 0;
    const query = searchQuery.toLowerCase();
    return lines.filter((line) => line.toLowerCase().includes(query)).length;
  }, [lines, searchQuery]);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy content:', err);
    }
  }, [content]);

  const handleToggleExpand = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  const handleToggleSearch = useCallback(() => {
    setIsSearching((prev) => !prev);
    if (isSearching) {
      setSearchQuery('');
    }
  }, [isSearching]);

  // Calculate file stats
  const stats = useMemo(() => {
    const words = content.split(/\s+/).filter(Boolean).length;
    const chars = content.length;
    return { words, chars, lines: totalLines };
  }, [content, totalLines]);

  return (
    <div
      className={cn(
        'rounded-lg overflow-hidden',
        'border border-gray-200 dark:border-gray-700',
        'bg-white dark:bg-gray-900',
        className
      )}
    >
      {/* Header */}
      <div
        className={cn(
          'flex items-center justify-between px-3 py-2',
          'bg-gray-50 dark:bg-gray-800',
          'border-b border-gray-200 dark:border-gray-700'
        )}
      >
        <div className="flex items-center gap-2 min-w-0">
          <FileText className="w-4 h-4 text-gray-500 flex-shrink-0" />
          {filename && (
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">
              {filename}
            </span>
          )}
          <span className="text-xs text-gray-400 dark:text-gray-500 flex-shrink-0">
            {stats.lines} lines • {stats.words} words
          </span>
        </div>

        <div className="flex items-center gap-1">
          {searchable && (
            <Button
              variant={isSearching ? 'secondary' : 'ghost'}
              size="icon"
              onClick={handleToggleSearch}
              className="h-7 w-7"
              title="Search"
            >
              <Search className="w-3.5 h-3.5" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={handleCopy}
            className="h-7 w-7"
            title={isCopied ? 'Copied!' : 'Copy content'}
          >
            {isCopied ? (
              <Check className="w-3.5 h-3.5 text-green-500" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
          </Button>
          {onDownload && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onDownload}
              className="h-7 w-7"
              title="Download file"
            >
              <Download className="w-3.5 h-3.5" />
            </Button>
          )}
        </div>
      </div>

      {/* Search Bar */}
      {isSearching && (
        <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search in file..."
              className={cn(
                'w-full pl-8 pr-3 py-1.5 text-sm',
                'bg-white dark:bg-gray-900',
                'border border-gray-200 dark:border-gray-700 rounded-md',
                'focus:outline-none focus:ring-2 focus:ring-blue-500'
              )}
            />
            {searchQuery && (
              <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-500">
                {matchCount} matches
              </span>
            )}
          </div>
        </div>
      )}

      {/* Content */}
      <div className="relative">
        <pre
          className={cn(
            'p-3 overflow-x-auto',
            'text-sm leading-relaxed whitespace-pre-wrap break-words',
            'text-gray-800 dark:text-gray-200'
          )}
        >
          {filteredContent || (
            <span className="text-gray-400 italic">No matching content</span>
          )}
        </pre>

        {/* Truncation fade effect */}
        {shouldTruncate && !isExpanded && !searchQuery && (
          <div
            className={cn(
              'absolute bottom-0 left-0 right-0 h-16',
              'bg-gradient-to-t from-white dark:from-gray-900 to-transparent',
              'pointer-events-none'
            )}
          />
        )}
      </div>

      {/* Expand/Collapse Button */}
      {shouldTruncate && !searchQuery && (
        <div className="px-3 py-2 border-t border-gray-200 dark:border-gray-700">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleToggleExpand}
            className="w-full justify-center text-xs"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-3.5 h-3.5 mr-1" />
                Show less
              </>
            ) : (
              <>
                <ChevronDown className="w-3.5 h-3.5 mr-1" />
                Show all {totalLines} lines
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  );
};

export default TextPreview;
