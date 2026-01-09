/**
 * useFileUpload Hook
 *
 * Sprint 75: File Upload Feature
 * Phase 20: File Attachment Support
 *
 * Custom hook for file upload management with progress tracking.
 */

import { useState, useCallback } from 'react';
import {
  uploadFile,
  FileUploadResponse,
  FileUploadProgress,
  isAllowedFileType,
  getMaxFileSize,
  formatFileSize,
} from '@/api/endpoints/files';

// =============================================================================
// Types
// =============================================================================

export type AttachmentStatus = 'pending' | 'uploading' | 'uploaded' | 'error';

export interface Attachment {
  id: string;
  file: File;
  preview?: string;  // For images
  status: AttachmentStatus;
  progress?: number;
  error?: string;
  serverResponse?: FileUploadResponse;
}

export interface UseFileUploadOptions {
  maxFiles?: number;
  onUploadComplete?: (attachment: Attachment) => void;
  onUploadError?: (attachment: Attachment, error: string) => void;
}

export interface UseFileUploadReturn {
  attachments: Attachment[];
  isUploading: boolean;
  addFiles: (files: File[]) => void;
  removeAttachment: (id: string) => void;
  uploadAll: () => Promise<void>;
  clearAttachments: () => void;
  getUploadedFileIds: () => string[];
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useFileUpload(options: UseFileUploadOptions = {}): UseFileUploadReturn {
  const { maxFiles = 10, onUploadComplete, onUploadError } = options;

  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  /**
   * Generate unique ID for attachment
   */
  const generateId = useCallback(() => {
    return `attachment-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  /**
   * Create image preview URL
   */
  const createPreview = useCallback((file: File): string | undefined => {
    if (file.type.startsWith('image/')) {
      return URL.createObjectURL(file);
    }
    return undefined;
  }, []);

  /**
   * Validate file before adding
   */
  const validateFile = useCallback((file: File): string | null => {
    // Check file type
    if (!isAllowedFileType(file)) {
      return `File type not supported: ${file.type || file.name.split('.').pop()}`;
    }

    // Check file size
    const maxSize = getMaxFileSize(file);
    if (file.size > maxSize) {
      return `File too large. Maximum size: ${formatFileSize(maxSize)}`;
    }

    return null;
  }, []);

  /**
   * Add files to upload queue
   */
  const addFiles = useCallback((files: File[]) => {
    setAttachments((prev) => {
      // Check max files limit
      const availableSlots = maxFiles - prev.length;
      if (availableSlots <= 0) {
        return prev;
      }

      const newAttachments: Attachment[] = [];

      for (const file of files.slice(0, availableSlots)) {
        const error = validateFile(file);
        const attachment: Attachment = {
          id: generateId(),
          file,
          preview: createPreview(file),
          status: error ? 'error' : 'pending',
          error: error || undefined,
        };
        newAttachments.push(attachment);
      }

      return [...prev, ...newAttachments];
    });
  }, [maxFiles, generateId, createPreview, validateFile]);

  /**
   * Remove an attachment by ID
   */
  const removeAttachment = useCallback((id: string) => {
    setAttachments((prev) => {
      const attachment = prev.find((a) => a.id === id);
      if (attachment?.preview) {
        URL.revokeObjectURL(attachment.preview);
      }
      return prev.filter((a) => a.id !== id);
    });
  }, []);

  /**
   * Upload a single attachment
   */
  const uploadSingle = useCallback(async (attachment: Attachment): Promise<Attachment> => {
    // Skip already uploaded or error files
    if (attachment.status === 'uploaded' || attachment.status === 'error') {
      return attachment;
    }

    // Update status to uploading
    setAttachments((prev) =>
      prev.map((a) => (a.id === attachment.id ? { ...a, status: 'uploading' as AttachmentStatus, progress: 0 } : a))
    );

    try {
      const response = await uploadFile(attachment.file, (progress: FileUploadProgress) => {
        setAttachments((prev) =>
          prev.map((a) =>
            a.id === attachment.id ? { ...a, progress: progress.percent } : a
          )
        );
      });

      const updatedAttachment: Attachment = {
        ...attachment,
        status: 'uploaded',
        progress: 100,
        serverResponse: response,
      };

      setAttachments((prev) =>
        prev.map((a) => (a.id === attachment.id ? updatedAttachment : a))
      );

      onUploadComplete?.(updatedAttachment);
      return updatedAttachment;

    } catch (err) {
      const error = err instanceof Error ? err.message : 'Upload failed';
      const updatedAttachment: Attachment = {
        ...attachment,
        status: 'error',
        error,
      };

      setAttachments((prev) =>
        prev.map((a) => (a.id === attachment.id ? updatedAttachment : a))
      );

      onUploadError?.(updatedAttachment, error);
      return updatedAttachment;
    }
  }, [onUploadComplete, onUploadError]);

  /**
   * Upload all pending attachments
   */
  const uploadAll = useCallback(async () => {
    const pendingAttachments = attachments.filter((a) => a.status === 'pending');

    if (pendingAttachments.length === 0) {
      return;
    }

    setIsUploading(true);

    try {
      await Promise.all(pendingAttachments.map(uploadSingle));
    } finally {
      setIsUploading(false);
    }
  }, [attachments, uploadSingle]);

  /**
   * Clear all attachments
   */
  const clearAttachments = useCallback(() => {
    // Revoke all preview URLs
    attachments.forEach((a) => {
      if (a.preview) {
        URL.revokeObjectURL(a.preview);
      }
    });
    setAttachments([]);
  }, [attachments]);

  /**
   * Get IDs of successfully uploaded files
   */
  const getUploadedFileIds = useCallback((): string[] => {
    return attachments
      .filter((a) => a.status === 'uploaded' && a.serverResponse)
      .map((a) => a.serverResponse!.id);
  }, [attachments]);

  return {
    attachments,
    isUploading,
    addFiles,
    removeAttachment,
    uploadAll,
    clearAttachments,
    getUploadedFileIds,
  };
}
