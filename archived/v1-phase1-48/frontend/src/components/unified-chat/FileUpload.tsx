/**
 * FileUpload Component
 *
 * Sprint 75: File Upload Feature
 * Phase 20: File Attachment Support
 *
 * File upload component with click and drag-and-drop support.
 */

import { FC, useCallback, useRef, useState } from 'react';
import { Upload, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

export interface FileUploadProps {
  onFilesSelected: (files: File[]) => void;
  accept?: string;
  maxSize?: number;
  multiple?: boolean;
  disabled?: boolean;
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

// Accepted file types for the input element
const ACCEPTED_TYPES = [
  // Text files
  '.txt', '.md', '.csv', '.json', '.xml', '.yaml', '.yml',
  '.html', '.css', '.js', '.ts', '.py', '.java', '.cpp', '.c', '.h',
  '.go', '.rs', '.rb', '.php', '.sql', '.sh', '.bat', '.ps1',
  // Images
  '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
  // PDF
  '.pdf',
].join(',');

// =============================================================================
// Component
// =============================================================================

export const FileUpload: FC<FileUploadProps> = ({
  onFilesSelected,
  accept = ACCEPTED_TYPES,
  maxSize,
  multiple = true,
  disabled = false,
  className,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragError, setDragError] = useState<string | null>(null);

  /**
   * Handle file selection from input
   */
  const handleFileChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    if (files.length > 0) {
      onFilesSelected(files);
    }
    // Reset input so the same file can be selected again
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  }, [onFilesSelected]);

  /**
   * Open file picker dialog
   */
  const handleClick = useCallback(() => {
    if (!disabled) {
      inputRef.current?.click();
    }
  }, [disabled]);

  /**
   * Handle keyboard activation
   */
  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if ((event.key === 'Enter' || event.key === ' ') && !disabled) {
      event.preventDefault();
      inputRef.current?.click();
    }
  }, [disabled]);

  /**
   * Handle drag enter
   */
  const handleDragEnter = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
    if (!disabled) {
      setIsDragging(true);
      setDragError(null);
    }
  }, [disabled]);

  /**
   * Handle drag leave
   */
  const handleDragLeave = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
    // Only set isDragging to false if we're leaving the dropzone entirely
    const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
    const x = event.clientX;
    const y = event.clientY;
    if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
      setIsDragging(false);
    }
  }, []);

  /**
   * Handle drag over
   */
  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
  }, []);

  /**
   * Handle drop
   */
  const handleDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);

    if (disabled) return;

    const files = Array.from(event.dataTransfer.files);

    // Validate files
    if (files.length === 0) {
      setDragError('No files detected');
      return;
    }

    if (!multiple && files.length > 1) {
      setDragError('Only one file allowed');
      return;
    }

    // Check file sizes if maxSize is specified
    if (maxSize) {
      const oversized = files.find((f) => f.size > maxSize);
      if (oversized) {
        setDragError(`File "${oversized.name}" is too large`);
        return;
      }
    }

    setDragError(null);
    onFilesSelected(files);
  }, [disabled, multiple, maxSize, onFilesSelected]);

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      className={cn(
        'relative flex flex-col items-center justify-center',
        'p-6 border-2 border-dashed rounded-lg',
        'transition-colors duration-200',
        'cursor-pointer',
        isDragging
          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
          : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500',
        disabled && 'opacity-50 cursor-not-allowed',
        className
      )}
    >
      {/* Hidden file input */}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Icon */}
      <div
        className={cn(
          'p-3 rounded-full mb-3',
          isDragging
            ? 'bg-blue-100 dark:bg-blue-800 text-blue-600 dark:text-blue-300'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400'
        )}
      >
        <Upload className="w-6 h-6" />
      </div>

      {/* Text */}
      <p className="text-sm text-gray-600 dark:text-gray-400 text-center">
        {isDragging ? (
          <span className="text-blue-600 dark:text-blue-400 font-medium">
            Drop files here
          </span>
        ) : (
          <>
            <span className="font-medium text-blue-600 dark:text-blue-400">
              Click to upload
            </span>
            {' or drag and drop'}
          </>
        )}
      </p>

      {/* Supported types */}
      <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
        Text, Images, or PDF (max 25MB)
      </p>

      {/* Error message */}
      {dragError && (
        <div className="absolute bottom-2 left-2 right-2 flex items-center gap-2 text-xs text-red-500">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{dragError}</span>
        </div>
      )}
    </div>
  );
};

// =============================================================================
// Compact Attach Button (for ChatInput)
// =============================================================================

export interface AttachButtonProps {
  onClick: () => void;
  disabled?: boolean;
  hasAttachments?: boolean;
  attachmentCount?: number;
  className?: string;
}

export const AttachButton: FC<AttachButtonProps> = ({
  onClick,
  disabled = false,
  hasAttachments = false,
  attachmentCount = 0,
  className,
}) => {
  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'relative',
        hasAttachments && 'text-blue-600 dark:text-blue-400',
        className
      )}
      title="Attach files"
    >
      <Upload className="w-5 h-5" />

      {/* Badge for attachment count */}
      {hasAttachments && attachmentCount > 0 && (
        <span className="absolute -top-1 -right-1 flex items-center justify-center w-4 h-4 text-[10px] font-medium text-white bg-blue-600 rounded-full">
          {attachmentCount > 9 ? '9+' : attachmentCount}
        </span>
      )}
    </Button>
  );
};

// =============================================================================
// Hidden File Input (for external trigger)
// =============================================================================

export interface HiddenFileInputProps {
  inputRef: React.RefObject<HTMLInputElement>;
  onFilesSelected: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
}

export const HiddenFileInput: FC<HiddenFileInputProps> = ({
  inputRef,
  onFilesSelected,
  accept = ACCEPTED_TYPES,
  multiple = true,
}) => {
  const handleChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    if (files.length > 0) {
      onFilesSelected(files);
    }
    // Reset input
    event.target.value = '';
  }, [onFilesSelected]);

  return (
    <input
      ref={inputRef}
      type="file"
      accept={accept}
      multiple={multiple}
      onChange={handleChange}
      className="hidden"
    />
  );
};
