/**
 * ImagePreview Component
 *
 * Sprint 76: File Download Feature
 * Phase 20: File Attachment Support
 *
 * Displays image files with preview and zoom functionality.
 */

import { FC, useState, useCallback } from 'react';
import { ZoomIn, ZoomOut, X, Download, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

export interface ImagePreviewProps {
  src: string;
  alt: string;
  filename?: string;
  onDownload?: () => void;
  className?: string;
}

// =============================================================================
// ImagePreview Component
// =============================================================================

export const ImagePreview: FC<ImagePreviewProps> = ({
  src,
  alt,
  filename,
  onDownload,
  className,
}) => {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [scale, setScale] = useState(1);

  const handleLoad = useCallback(() => {
    setIsLoading(false);
  }, []);

  const handleError = useCallback(() => {
    setIsLoading(false);
    setHasError(true);
  }, []);

  const handleZoomIn = useCallback(() => {
    setScale((prev) => Math.min(prev + 0.25, 3));
  }, []);

  const handleZoomOut = useCallback(() => {
    setScale((prev) => Math.max(prev - 0.25, 0.5));
  }, []);

  const handleToggleFullscreen = useCallback(() => {
    setIsFullscreen((prev) => !prev);
    setScale(1);
  }, []);

  const handleOpenInNewTab = useCallback(() => {
    window.open(src, '_blank');
  }, [src]);

  if (hasError) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center p-4 rounded-lg',
          'bg-gray-100 dark:bg-gray-800',
          'border border-gray-200 dark:border-gray-700',
          'text-gray-500 dark:text-gray-400',
          className
        )}
      >
        <p className="text-sm">Failed to load image</p>
        {filename && <p className="text-xs mt-1">{filename}</p>}
        {onDownload && (
          <Button variant="outline" size="sm" onClick={onDownload} className="mt-2">
            <Download className="w-4 h-4 mr-1" />
            Download
          </Button>
        )}
      </div>
    );
  }

  return (
    <>
      {/* Thumbnail Preview */}
      <div
        className={cn(
          'relative group rounded-lg overflow-hidden',
          'bg-gray-100 dark:bg-gray-800',
          'border border-gray-200 dark:border-gray-700',
          className
        )}
      >
        {/* Loading skeleton */}
        {isLoading && (
          <div className="absolute inset-0 animate-pulse bg-gray-200 dark:bg-gray-700" />
        )}

        {/* Image */}
        <img
          src={src}
          alt={alt}
          onLoad={handleLoad}
          onError={handleError}
          className={cn(
            'max-w-full max-h-64 object-contain cursor-pointer',
            'transition-opacity',
            isLoading ? 'opacity-0' : 'opacity-100'
          )}
          onClick={handleToggleFullscreen}
        />

        {/* Hover overlay with actions */}
        <div
          className={cn(
            'absolute inset-0 bg-black/0 group-hover:bg-black/20',
            'transition-colors',
            'flex items-center justify-center gap-2',
            'opacity-0 group-hover:opacity-100'
          )}
        >
          <Button
            variant="secondary"
            size="icon"
            onClick={handleToggleFullscreen}
            className="h-8 w-8"
            title="View fullscreen"
          >
            <ZoomIn className="w-4 h-4" />
          </Button>
          <Button
            variant="secondary"
            size="icon"
            onClick={handleOpenInNewTab}
            className="h-8 w-8"
            title="Open in new tab"
          >
            <ExternalLink className="w-4 h-4" />
          </Button>
          {onDownload && (
            <Button
              variant="secondary"
              size="icon"
              onClick={onDownload}
              className="h-8 w-8"
              title="Download"
            >
              <Download className="w-4 h-4" />
            </Button>
          )}
        </div>

        {/* Filename badge */}
        {filename && (
          <div className="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/50 to-transparent">
            <p className="text-xs text-white truncate">{filename}</p>
          </div>
        )}
      </div>

      {/* Fullscreen Modal */}
      {isFullscreen && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center"
          onClick={handleToggleFullscreen}
        >
          {/* Controls */}
          <div className="absolute top-4 right-4 flex items-center gap-2">
            <Button
              variant="secondary"
              size="icon"
              onClick={(e) => {
                e.stopPropagation();
                handleZoomOut();
              }}
              className="h-10 w-10"
              disabled={scale <= 0.5}
            >
              <ZoomOut className="w-5 h-5" />
            </Button>
            <span className="text-white text-sm px-2">{Math.round(scale * 100)}%</span>
            <Button
              variant="secondary"
              size="icon"
              onClick={(e) => {
                e.stopPropagation();
                handleZoomIn();
              }}
              className="h-10 w-10"
              disabled={scale >= 3}
            >
              <ZoomIn className="w-5 h-5" />
            </Button>
            <Button
              variant="secondary"
              size="icon"
              onClick={handleToggleFullscreen}
              className="h-10 w-10 ml-2"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>

          {/* Image */}
          <img
            src={src}
            alt={alt}
            onClick={(e) => e.stopPropagation()}
            style={{ transform: `scale(${scale})` }}
            className="max-w-[90vw] max-h-[90vh] object-contain transition-transform cursor-move"
          />
        </div>
      )}
    </>
  );
};

export default ImagePreview;
