/**
 * FileRenderer Component
 *
 * Sprint 76: File Download Feature
 * Phase 20: File Attachment Support
 *
 * Renders files based on their type with appropriate preview component.
 */

import { FC, useMemo } from 'react';
import { Download, File, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { formatFileSize } from '@/api/endpoints/files';
import type { GeneratedFile } from '@/api/endpoints/files';
import { ImagePreview } from './renderers/ImagePreview';
import { CodePreview } from './renderers/CodePreview';
import { TextPreview } from './renderers/TextPreview';

// =============================================================================
// Types
// =============================================================================

export type FileType = 'image' | 'code' | 'text' | 'pdf' | 'other';

export interface FileRendererProps {
  file: GeneratedFile;
  content?: string;
  preview?: string;  // For image preview (base64 or URL)
  onDownload: (fileId: string) => Promise<void>;
  isLoading?: boolean;
  className?: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Determine file type from MIME type and filename
 */
export function getFileType(mimeType: string, filename?: string): FileType {
  // Image types
  if (mimeType.startsWith('image/')) {
    return 'image';
  }

  // PDF
  if (mimeType === 'application/pdf') {
    return 'pdf';
  }

  // Code types
  const codeExtensions = [
    '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h',
    '.go', '.rs', '.rb', '.php', '.sql', '.sh', '.bash', '.zsh',
    '.json', '.xml', '.html', '.css', '.yaml', '.yml', '.toml', '.ini'
  ];

  if (filename) {
    const ext = '.' + filename.split('.').pop()?.toLowerCase();
    if (codeExtensions.includes(ext)) {
      return 'code';
    }
  }

  if (
    mimeType.includes('javascript') ||
    mimeType.includes('typescript') ||
    mimeType.includes('json') ||
    mimeType.includes('xml') ||
    mimeType.includes('yaml')
  ) {
    return 'code';
  }

  // Text types
  if (mimeType.startsWith('text/')) {
    return 'text';
  }

  return 'other';
}

/**
 * Get file type label
 */
function getFileTypeLabel(type: FileType): string {
  switch (type) {
    case 'image': return 'Image';
    case 'code': return 'Code';
    case 'text': return 'Text';
    case 'pdf': return 'PDF';
    default: return 'File';
  }
}

// =============================================================================
// FileRenderer Component
// =============================================================================

export const FileRenderer: FC<FileRendererProps> = ({
  file,
  content,
  preview,
  onDownload,
  isLoading = false,
  className,
}) => {
  const fileType = useMemo(() => getFileType(file.mimeType, file.name), [file.mimeType, file.name]);

  const handleDownload = async () => {
    await onDownload(file.id);
  };

  // Loading state
  if (isLoading) {
    return (
      <div
        className={cn(
          'flex items-center justify-center p-8 rounded-lg',
          'bg-gray-50 dark:bg-gray-800',
          'border border-gray-200 dark:border-gray-700',
          className
        )}
      >
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        <span className="ml-2 text-sm text-gray-500">Loading preview...</span>
      </div>
    );
  }

  // Image preview
  if (fileType === 'image' && preview) {
    return (
      <ImagePreview
        src={preview}
        alt={file.name}
        filename={file.name}
        onDownload={handleDownload}
        className={className}
      />
    );
  }

  // Code preview
  if (fileType === 'code' && content) {
    return (
      <CodePreview
        code={content}
        filename={file.name}
        onDownload={handleDownload}
        className={className}
      />
    );
  }

  // Text preview
  if (fileType === 'text' && content) {
    return (
      <TextPreview
        content={content}
        filename={file.name}
        searchable={content.length > 1000}
        onDownload={handleDownload}
        className={className}
      />
    );
  }

  // Generic file card (PDF, other, or no content available)
  return (
    <GenericFileCard
      file={file}
      fileType={fileType}
      onDownload={handleDownload}
      className={className}
    />
  );
};

// =============================================================================
// GenericFileCard Component (for unsupported/binary files)
// =============================================================================

interface GenericFileCardProps {
  file: GeneratedFile;
  fileType: FileType;
  onDownload: () => Promise<void>;
  className?: string;
}

const GenericFileCard: FC<GenericFileCardProps> = ({
  file,
  fileType,
  onDownload,
  className,
}) => {
  return (
    <div
      className={cn(
        'flex items-center gap-4 p-4 rounded-lg',
        'bg-gray-50 dark:bg-gray-800',
        'border border-gray-200 dark:border-gray-700',
        className
      )}
    >
      {/* File Icon */}
      <div
        className={cn(
          'flex-shrink-0 w-12 h-12 rounded-lg',
          'flex items-center justify-center',
          'bg-white dark:bg-gray-700',
          'border border-gray-200 dark:border-gray-600',
          'text-gray-500'
        )}
      >
        <File className="w-6 h-6" />
      </div>

      {/* File Info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
          {file.name}
        </p>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {getFileTypeLabel(fileType)}
          </span>
          <span className="text-xs text-gray-400">•</span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {formatFileSize(file.size)}
          </span>
        </div>
        {fileType === 'pdf' && (
          <p className="text-xs text-gray-400 mt-1">
            PDF preview not available. Click to download.
          </p>
        )}
      </div>

      {/* Download Button */}
      <Button
        variant="secondary"
        size="sm"
        onClick={onDownload}
        className="flex-shrink-0"
      >
        <Download className="w-4 h-4 mr-1.5" />
        Download
      </Button>
    </div>
  );
};

export default FileRenderer;
