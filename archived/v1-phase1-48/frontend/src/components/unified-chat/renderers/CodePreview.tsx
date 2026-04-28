/**
 * CodePreview Component
 *
 * Sprint 76: File Download Feature
 * Phase 20: File Attachment Support
 *
 * Displays code files with syntax highlighting.
 */

import { FC, useState, useCallback, useMemo } from 'react';
import { Copy, Check, ChevronDown, ChevronUp, Download, FileCode } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

export interface CodePreviewProps {
  code: string;
  language?: string;
  filename?: string;
  maxLines?: number;
  onDownload?: () => void;
  className?: string;
}

// =============================================================================
// Language Detection
// =============================================================================

const EXTENSION_TO_LANGUAGE: Record<string, string> = {
  '.py': 'python',
  '.js': 'javascript',
  '.jsx': 'javascript',
  '.ts': 'typescript',
  '.tsx': 'typescript',
  '.java': 'java',
  '.cpp': 'cpp',
  '.c': 'c',
  '.h': 'c',
  '.go': 'go',
  '.rs': 'rust',
  '.rb': 'ruby',
  '.php': 'php',
  '.sql': 'sql',
  '.sh': 'bash',
  '.bash': 'bash',
  '.zsh': 'bash',
  '.json': 'json',
  '.xml': 'xml',
  '.html': 'html',
  '.css': 'css',
  '.yaml': 'yaml',
  '.yml': 'yaml',
  '.md': 'markdown',
  '.toml': 'toml',
  '.ini': 'ini',
  '.env': 'dotenv',
};

function detectLanguage(filename?: string): string {
  if (!filename) return 'plaintext';
  const ext = '.' + filename.split('.').pop()?.toLowerCase();
  return EXTENSION_TO_LANGUAGE[ext] || 'plaintext';
}

// =============================================================================
// CodePreview Component
// =============================================================================

export const CodePreview: FC<CodePreviewProps> = ({
  code,
  language,
  filename,
  maxLines = 20,
  onDownload,
  className,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isCopied, setIsCopied] = useState(false);

  const detectedLanguage = language || detectLanguage(filename);

  const lines = useMemo(() => code.split('\n'), [code]);
  const totalLines = lines.length;
  const shouldTruncate = totalLines > maxLines;

  const displayedCode = useMemo(() => {
    if (!shouldTruncate || isExpanded) {
      return code;
    }
    return lines.slice(0, maxLines).join('\n');
  }, [code, lines, maxLines, shouldTruncate, isExpanded]);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  }, [code]);

  const handleToggleExpand = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  return (
    <div
      className={cn(
        'rounded-lg overflow-hidden',
        'border border-gray-200 dark:border-gray-700',
        'bg-gray-50 dark:bg-gray-900',
        className
      )}
    >
      {/* Header */}
      <div
        className={cn(
          'flex items-center justify-between px-3 py-2',
          'bg-gray-100 dark:bg-gray-800',
          'border-b border-gray-200 dark:border-gray-700'
        )}
      >
        <div className="flex items-center gap-2 min-w-0">
          <FileCode className="w-4 h-4 text-gray-500 flex-shrink-0" />
          {filename && (
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">
              {filename}
            </span>
          )}
          <span className="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0">
            {detectedLanguage}
          </span>
          <span className="text-xs text-gray-400 dark:text-gray-500 flex-shrink-0">
            {totalLines} lines
          </span>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleCopy}
            className="h-7 w-7"
            title={isCopied ? 'Copied!' : 'Copy code'}
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

      {/* Code Content */}
      <div className="relative">
        <pre
          className={cn(
            'p-3 overflow-x-auto',
            'text-sm font-mono leading-relaxed',
            'text-gray-800 dark:text-gray-200'
          )}
        >
          <code>{displayedCode}</code>
        </pre>

        {/* Truncation fade effect */}
        {shouldTruncate && !isExpanded && (
          <div
            className={cn(
              'absolute bottom-0 left-0 right-0 h-16',
              'bg-gradient-to-t from-gray-50 dark:from-gray-900 to-transparent',
              'pointer-events-none'
            )}
          />
        )}
      </div>

      {/* Expand/Collapse Button */}
      {shouldTruncate && (
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

export default CodePreview;
