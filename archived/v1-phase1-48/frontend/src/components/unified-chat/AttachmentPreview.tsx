/**
 * AttachmentPreview Component
 *
 * Sprint 75: File Upload Feature
 * Phase 20: File Attachment Support
 *
 * Displays list of selected/uploaded attachments with preview and remove functionality.
 */

import { FC, useMemo } from 'react';
import {
  X,
  FileText,
  Image as ImageIcon,
  FileCode,
  File,
  Loader2,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { formatFileSize } from '@/api/endpoints/files';
import type { Attachment, AttachmentStatus } from '@/hooks/useFileUpload';

// =============================================================================
// Types
// =============================================================================

export interface AttachmentPreviewProps {
  attachments: Attachment[];
  onRemove: (id: string) => void;
  disabled?: boolean;
  className?: string;
}

export interface AttachmentItemProps {
  attachment: Attachment;
  onRemove: (id: string) => void;
  disabled?: boolean;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get file icon based on MIME type
 */
function getFileIcon(file: File): React.ReactNode {
  const mimeType = file.type;

  if (mimeType.startsWith('image/')) {
    return <ImageIcon className="w-5 h-5" />;
  }

  if (
    mimeType.includes('javascript') ||
    mimeType.includes('json') ||
    mimeType.includes('xml') ||
    mimeType.includes('yaml')
  ) {
    return <FileCode className="w-5 h-5" />;
  }

  if (mimeType.startsWith('text/') || mimeType === 'application/pdf') {
    return <FileText className="w-5 h-5" />;
  }

  return <File className="w-5 h-5" />;
}

/**
 * Get status indicator component
 */
function StatusIndicator({ status, progress }: { status: AttachmentStatus; progress?: number }) {
  switch (status) {
    case 'uploading':
      return (
        <div className="flex items-center gap-1 text-blue-600">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-xs">{progress ?? 0}%</span>
        </div>
      );
    case 'uploaded':
      return <CheckCircle className="w-4 h-4 text-green-600" />;
    case 'error':
      return <AlertCircle className="w-4 h-4 text-red-500" />;
    default:
      return null;
  }
}

// =============================================================================
// AttachmentItem Component
// =============================================================================

const AttachmentItem: FC<AttachmentItemProps> = ({ attachment, onRemove, disabled }) => {
  const { id, file, preview, status, progress, error } = attachment;

  const isImage = file.type.startsWith('image/');
  const isUploading = status === 'uploading';
  const hasError = status === 'error';

  return (
    <div
      className={cn(
        'relative flex items-center gap-3 p-2 rounded-lg',
        'bg-gray-50 dark:bg-gray-800',
        'border border-gray-200 dark:border-gray-700',
        hasError && 'border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/20'
      )}
    >
      {/* Preview / Icon */}
      <div
        className={cn(
          'flex-shrink-0 w-12 h-12 rounded-md overflow-hidden',
          'flex items-center justify-center',
          'bg-gray-100 dark:bg-gray-700'
        )}
      >
        {isImage && preview ? (
          <img
            src={preview}
            alt={file.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="text-gray-500 dark:text-gray-400">
            {getFileIcon(file)}
          </div>
        )}
      </div>

      {/* File Info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
          {file.name}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {formatFileSize(file.size)}
          </span>
          <StatusIndicator status={status} progress={progress} />
        </div>
        {error && (
          <p className="text-xs text-red-500 mt-0.5 truncate">
            {error}
          </p>
        )}
      </div>

      {/* Upload Progress Bar */}
      {isUploading && (
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-gray-200 dark:bg-gray-700 rounded-b-lg overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-300"
            style={{ width: `${progress ?? 0}%` }}
          />
        </div>
      )}

      {/* Remove Button */}
      <Button
        type="button"
        variant="ghost"
        size="icon"
        onClick={() => onRemove(id)}
        disabled={disabled || isUploading}
        className={cn(
          'flex-shrink-0 h-8 w-8',
          'text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300',
          'opacity-0 group-hover:opacity-100 transition-opacity',
          // Always show on touch devices
          'sm:opacity-100'
        )}
        title="Remove attachment"
      >
        <X className="w-4 h-4" />
      </Button>
    </div>
  );
};

// =============================================================================
// AttachmentPreview Component
// =============================================================================

export const AttachmentPreview: FC<AttachmentPreviewProps> = ({
  attachments,
  onRemove,
  disabled = false,
  className,
}) => {
  // Summary stats
  const stats = useMemo(() => {
    const total = attachments.length;
    const uploading = attachments.filter((a) => a.status === 'uploading').length;
    const uploaded = attachments.filter((a) => a.status === 'uploaded').length;
    const errors = attachments.filter((a) => a.status === 'error').length;

    return { total, uploading, uploaded, errors };
  }, [attachments]);

  if (attachments.length === 0) {
    return null;
  }

  return (
    <div className={cn('space-y-2', className)}>
      {/* Header with stats */}
      <div className="flex items-center justify-between px-1">
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {stats.total} file{stats.total !== 1 ? 's' : ''}
          {stats.uploading > 0 && ` (${stats.uploading} uploading)`}
          {stats.errors > 0 && (
            <span className="text-red-500 ml-1">
              ({stats.errors} error{stats.errors !== 1 ? 's' : ''})
            </span>
          )}
        </span>

        {/* Clear all button */}
        {!disabled && attachments.length > 1 && (
          <button
            type="button"
            onClick={() => attachments.forEach((a) => onRemove(a.id))}
            className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Attachment list */}
      <div className="space-y-2 group">
        {attachments.map((attachment) => (
          <AttachmentItem
            key={attachment.id}
            attachment={attachment}
            onRemove={onRemove}
            disabled={disabled}
          />
        ))}
      </div>
    </div>
  );
};

// =============================================================================
// Compact Attachment Preview (for inline display in ChatInput)
// =============================================================================

export interface CompactAttachmentPreviewProps {
  attachments: Attachment[];
  onRemove: (id: string) => void;
  disabled?: boolean;
  className?: string;
}

export const CompactAttachmentPreview: FC<CompactAttachmentPreviewProps> = ({
  attachments,
  onRemove,
  disabled = false,
  className,
}) => {
  if (attachments.length === 0) {
    return null;
  }

  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {attachments.map((attachment) => {
        const isImage = attachment.file.type.startsWith('image/');
        const isUploading = attachment.status === 'uploading';
        const hasError = attachment.status === 'error';

        return (
          <div
            key={attachment.id}
            className={cn(
              'relative flex items-center gap-2 px-2 py-1 rounded-md',
              'bg-gray-100 dark:bg-gray-800',
              'border border-gray-200 dark:border-gray-700',
              hasError && 'border-red-300 dark:border-red-700'
            )}
            title={attachment.file.name}
          >
            {/* Thumbnail or icon */}
            <div className="w-6 h-6 flex-shrink-0 rounded overflow-hidden">
              {isImage && attachment.preview ? (
                <img
                  src={attachment.preview}
                  alt={attachment.file.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray-400">
                  {getFileIcon(attachment.file)}
                </div>
              )}
            </div>

            {/* Filename (truncated) */}
            <span className="text-xs text-gray-600 dark:text-gray-300 max-w-[100px] truncate">
              {attachment.file.name}
            </span>

            {/* Status */}
            {isUploading && (
              <Loader2 className="w-3 h-3 animate-spin text-blue-500" />
            )}
            {hasError && (
              <AlertCircle className="w-3 h-3 text-red-500" />
            )}

            {/* Remove button */}
            <button
              type="button"
              onClick={() => onRemove(attachment.id)}
              disabled={disabled || isUploading}
              className={cn(
                'p-0.5 rounded-full',
                'text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300',
                'hover:bg-gray-200 dark:hover:bg-gray-700',
                'disabled:opacity-50'
              )}
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        );
      })}
    </div>
  );
};
