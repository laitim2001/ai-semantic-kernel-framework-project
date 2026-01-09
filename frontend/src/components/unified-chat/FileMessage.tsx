/**
 * FileMessage Component
 *
 * Sprint 76: File Download Feature
 * Phase 20: File Attachment Support
 *
 * Displays generated files from Claude SDK in chat messages.
 */

import { FC, useState, useCallback } from 'react';
import {
  FileText,
  Image as ImageIcon,
  FileCode,
  File,
  Download,
  Loader2,
  CheckCircle,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { formatFileSize } from '@/api/endpoints/files';
import type { GeneratedFile } from '@/api/endpoints/files';

// =============================================================================
// Types
// =============================================================================

export type DownloadStatus = 'idle' | 'downloading' | 'success' | 'error';

export interface FileMessageProps {
  file: GeneratedFile;
  onDownload: (fileId: string) => Promise<void>;
  className?: string;
}

export interface FileMessageListProps {
  files: GeneratedFile[];
  onDownload: (fileId: string) => Promise<void>;
  className?: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get file icon based on MIME type
 */
function getFileIcon(mimeType: string): React.ReactNode {
  if (mimeType.startsWith('image/')) {
    return <ImageIcon className="w-5 h-5" />;
  }

  if (
    mimeType.includes('javascript') ||
    mimeType.includes('json') ||
    mimeType.includes('xml') ||
    mimeType.includes('yaml') ||
    mimeType.includes('python') ||
    mimeType.includes('typescript')
  ) {
    return <FileCode className="w-5 h-5" />;
  }

  if (mimeType.startsWith('text/') || mimeType === 'application/pdf') {
    return <FileText className="w-5 h-5" />;
  }

  return <File className="w-5 h-5" />;
}

/**
 * Get file type label
 */
function getFileTypeLabel(mimeType: string): string {
  if (mimeType.startsWith('image/')) return 'Image';
  if (mimeType === 'application/pdf') return 'PDF';
  if (mimeType.includes('javascript')) return 'JavaScript';
  if (mimeType.includes('typescript')) return 'TypeScript';
  if (mimeType.includes('python')) return 'Python';
  if (mimeType.includes('json')) return 'JSON';
  if (mimeType.includes('xml')) return 'XML';
  if (mimeType.includes('yaml')) return 'YAML';
  if (mimeType.startsWith('text/')) return 'Text';
  return 'File';
}

/**
 * Get icon color based on file type
 */
function getIconColor(mimeType: string): string {
  if (mimeType.startsWith('image/')) return 'text-purple-500';
  if (mimeType === 'application/pdf') return 'text-red-500';
  if (mimeType.includes('javascript') || mimeType.includes('typescript')) {
    return 'text-yellow-500';
  }
  if (mimeType.includes('python')) return 'text-blue-500';
  if (mimeType.includes('json')) return 'text-green-500';
  return 'text-gray-500';
}

// =============================================================================
// FileMessage Component
// =============================================================================

export const FileMessage: FC<FileMessageProps> = ({
  file,
  onDownload,
  className,
}) => {
  const [status, setStatus] = useState<DownloadStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  const handleDownload = useCallback(async () => {
    if (status === 'downloading') return;

    setStatus('downloading');
    setError(null);

    try {
      await onDownload(file.id);
      setStatus('success');
      // Reset status after 3 seconds
      setTimeout(() => setStatus('idle'), 3000);
    } catch (err) {
      setStatus('error');
      setError(err instanceof Error ? err.message : 'Download failed');
      // Reset status after 5 seconds
      setTimeout(() => {
        setStatus('idle');
        setError(null);
      }, 5000);
    }
  }, [file.id, onDownload, status]);

  const isDownloading = status === 'downloading';
  const isSuccess = status === 'success';
  const isError = status === 'error';

  return (
    <div
      className={cn(
        'flex items-center gap-3 p-3 rounded-lg',
        'bg-gray-50 dark:bg-gray-800',
        'border border-gray-200 dark:border-gray-700',
        'max-w-md',
        className
      )}
    >
      {/* File Icon */}
      <div
        className={cn(
          'flex-shrink-0 w-10 h-10 rounded-lg',
          'flex items-center justify-center',
          'bg-white dark:bg-gray-700',
          'border border-gray-200 dark:border-gray-600',
          getIconColor(file.mimeType)
        )}
      >
        {getFileIcon(file.mimeType)}
      </div>

      {/* File Info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
          {file.name}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {getFileTypeLabel(file.mimeType)}
          </span>
          <span className="text-xs text-gray-400">•</span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {formatFileSize(file.size)}
          </span>
        </div>
        {error && (
          <p className="text-xs text-red-500 mt-1 truncate">{error}</p>
        )}
      </div>

      {/* Download Button */}
      <Button
        type="button"
        variant={isSuccess ? 'outline' : isError ? 'destructive' : 'secondary'}
        size="sm"
        onClick={handleDownload}
        disabled={isDownloading}
        className={cn(
          'flex-shrink-0',
          isSuccess && 'text-green-600 border-green-600 hover:bg-green-50'
        )}
      >
        {isDownloading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : isSuccess ? (
          <CheckCircle className="w-4 h-4" />
        ) : isError ? (
          <AlertCircle className="w-4 h-4" />
        ) : (
          <Download className="w-4 h-4" />
        )}
        <span className="ml-1.5">
          {isDownloading
            ? 'Downloading...'
            : isSuccess
              ? 'Downloaded'
              : isError
                ? 'Retry'
                : 'Download'}
        </span>
      </Button>
    </div>
  );
};

// =============================================================================
// FileMessageList Component
// =============================================================================

export const FileMessageList: FC<FileMessageListProps> = ({
  files,
  onDownload,
  className,
}) => {
  if (files.length === 0) {
    return null;
  }

  return (
    <div className={cn('space-y-2', className)}>
      {files.length > 1 && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
          {files.length} files generated
        </p>
      )}
      {files.map((file) => (
        <FileMessage key={file.id} file={file} onDownload={onDownload} />
      ))}
    </div>
  );
};

// =============================================================================
// Compact FileMessage (for inline display)
// =============================================================================

export interface CompactFileMessageProps {
  file: GeneratedFile;
  onDownload: (fileId: string) => Promise<void>;
  className?: string;
}

export const CompactFileMessage: FC<CompactFileMessageProps> = ({
  file,
  onDownload,
  className,
}) => {
  const [status, setStatus] = useState<DownloadStatus>('idle');

  const handleDownload = useCallback(async () => {
    if (status === 'downloading') return;

    setStatus('downloading');
    try {
      await onDownload(file.id);
      setStatus('success');
      setTimeout(() => setStatus('idle'), 3000);
    } catch {
      setStatus('error');
      setTimeout(() => setStatus('idle'), 3000);
    }
  }, [file.id, onDownload, status]);

  return (
    <button
      type="button"
      onClick={handleDownload}
      disabled={status === 'downloading'}
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-1 rounded-md',
        'text-sm text-blue-600 dark:text-blue-400',
        'bg-blue-50 dark:bg-blue-900/20',
        'hover:bg-blue-100 dark:hover:bg-blue-900/40',
        'border border-blue-200 dark:border-blue-800',
        'transition-colors',
        'disabled:opacity-50 disabled:cursor-wait',
        className
      )}
      title={`Download ${file.name}`}
    >
      {status === 'downloading' ? (
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
      ) : status === 'success' ? (
        <CheckCircle className="w-3.5 h-3.5 text-green-500" />
      ) : status === 'error' ? (
        <AlertCircle className="w-3.5 h-3.5 text-red-500" />
      ) : (
        <Download className="w-3.5 h-3.5" />
      )}
      <span className="max-w-[120px] truncate">{file.name}</span>
      {file.downloadUrl && (
        <ExternalLink className="w-3 h-3 ml-0.5 opacity-50" />
      )}
    </button>
  );
};

export default FileMessage;
