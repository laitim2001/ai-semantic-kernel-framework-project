/**
 * Files API Endpoints
 *
 * Sprint 75: File Upload Feature
 * Phase 20: File Attachment Support
 *
 * API client for file upload and management.
 */

import { API_BASE_URL } from '../client';
import { useAuthStore } from '@/store/authStore';
import { getGuestHeaders } from '@/utils/guestUser';

// =============================================================================
// Types
// =============================================================================

export type FileCategory = 'text' | 'image' | 'pdf';
export type FileStatus = 'pending' | 'uploading' | 'uploaded' | 'error';

export interface FileMetadata {
  id: string;
  user_id: string;
  filename: string;
  size: number;
  mime_type: string;
  category: FileCategory;
  storage_path: string;
  session_id?: string;
  created_at: string;
}

/**
 * Generated file from Claude SDK
 * Sprint 76: File Download Feature
 */
export interface GeneratedFile {
  id: string;
  name: string;
  size: number;
  mimeType: string;
  createdAt: string;
  downloadUrl?: string;
}

export interface FileUploadResponse {
  id: string;
  filename: string;
  size: number;
  mime_type: string;
  category: FileCategory;
  status: FileStatus;
  message: string;
}

export interface FileListResponse {
  files: FileMetadata[];
  total: number;
}

export interface FileUploadProgress {
  loaded: number;
  total: number;
  percent: number;
}

// =============================================================================
// Utilities
// =============================================================================

/**
 * Get auth headers for file upload
 */
function getAuthHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token;
  const guestHeaders = getGuestHeaders();

  const headers: Record<string, string> = {
    ...guestHeaders,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return headers;
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const size = bytes / Math.pow(1024, i);

  return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

/**
 * Get file category from MIME type
 */
export function getFileCategory(mimeType: string): FileCategory {
  if (mimeType.startsWith('image/')) return 'image';
  if (mimeType === 'application/pdf') return 'pdf';
  return 'text';
}

/**
 * Check if file type is allowed
 */
export function isAllowedFileType(file: File): boolean {
  const allowedTypes = [
    // Text
    'text/plain',
    'text/markdown',
    'text/csv',
    'text/html',
    'text/css',
    'text/javascript',
    'application/json',
    'application/xml',
    'application/x-yaml',
    // Images
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/svg+xml',
    // PDF
    'application/pdf',
  ];

  // Also check by extension for code files
  const codeExtensions = ['.py', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.rb', '.php', '.sql', '.sh', '.bat', '.ps1', '.ts'];
  const extension = '.' + file.name.split('.').pop()?.toLowerCase();

  return allowedTypes.includes(file.type) || codeExtensions.includes(extension);
}

/**
 * Get max file size for file type
 */
export function getMaxFileSize(file: File): number {
  const category = getFileCategory(file.type);
  switch (category) {
    case 'image': return 20 * 1024 * 1024; // 20MB
    case 'pdf': return 25 * 1024 * 1024; // 25MB
    default: return 10 * 1024 * 1024; // 10MB
  }
}

// =============================================================================
// API Functions
// =============================================================================

/**
 * Upload a file with progress tracking
 */
export async function uploadFile(
  file: File,
  onProgress?: (progress: FileUploadProgress) => void
): Promise<FileUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    // Track upload progress
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress({
          loaded: event.loaded,
          total: event.total,
          percent: Math.round((event.loaded / event.total) * 100),
        });
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText);
          resolve(response);
        } catch {
          reject(new Error('Failed to parse response'));
        }
      } else if (xhr.status === 401) {
        // Handle unauthorized
        useAuthStore.getState().logout();
        window.location.href = '/login';
        reject(new Error('Unauthorized'));
      } else {
        try {
          const error = JSON.parse(xhr.responseText);
          reject(new Error(error.detail?.message || error.message || 'Upload failed'));
        } catch {
          reject(new Error(`Upload failed: ${xhr.statusText}`));
        }
      }
    });

    xhr.addEventListener('error', () => {
      reject(new Error('Network error during upload'));
    });

    xhr.addEventListener('abort', () => {
      reject(new Error('Upload cancelled'));
    });

    xhr.open('POST', `${API_BASE_URL}/files/upload`);

    // Set auth headers
    const headers = getAuthHeaders();
    Object.entries(headers).forEach(([key, value]) => {
      xhr.setRequestHeader(key, value);
    });

    xhr.send(formData);
  });
}

/**
 * List user files
 */
export async function listFiles(): Promise<FileListResponse> {
  const response = await fetch(`${API_BASE_URL}/files/`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error('Failed to list files');
  }

  return response.json();
}

/**
 * Get file metadata
 */
export async function getFile(fileId: string): Promise<FileMetadata> {
  const response = await fetch(`${API_BASE_URL}/files/${fileId}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error('File not found');
  }

  return response.json();
}

/**
 * Delete a file
 */
export async function deleteFile(fileId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/files/${fileId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });

  if (!response.ok && response.status !== 204) {
    throw new Error('Failed to delete file');
  }
}

/**
 * Get file content URL
 */
export function getFileContentUrl(fileId: string): string {
  return `${API_BASE_URL}/files/${fileId}/content`;
}

/**
 * Get file download URL
 * Sprint 76: File Download Feature
 */
export function getFileDownloadUrl(fileId: string): string {
  return `${API_BASE_URL}/files/${fileId}/download`;
}

/**
 * Download file to local
 * Sprint 76: File Download Feature
 */
export async function downloadFile(fileId: string, filename?: string): Promise<void> {
  const response = await fetch(getFileDownloadUrl(fileId), {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error('Failed to download file');
  }

  // Get filename from Content-Disposition header if not provided
  const contentDisposition = response.headers.get('Content-Disposition');
  let downloadFilename = filename;
  if (!downloadFilename && contentDisposition) {
    const match = contentDisposition.match(/filename="(.+)"/);
    if (match) {
      downloadFilename = match[1];
    }
  }
  downloadFilename = downloadFilename || 'download';

  // Create blob and download
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = downloadFilename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

/**
 * Get file content as text
 * Sprint 76: File Download Feature
 */
export async function getFileContentText(fileId: string): Promise<string> {
  const response = await fetch(getFileContentUrl(fileId), {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error('Failed to get file content');
  }

  return response.text();
}

/**
 * Get file content as blob
 * Sprint 76: File Download Feature
 */
export async function getFileContentBlob(fileId: string): Promise<Blob> {
  const response = await fetch(getFileContentUrl(fileId), {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error('Failed to get file content');
  }

  return response.blob();
}

/**
 * List files with optional session filter
 * Sprint 76: File Download Feature
 */
export async function listFilesWithSession(sessionId?: string): Promise<FileListResponse> {
  const url = sessionId
    ? `${API_BASE_URL}/files/?session_id=${encodeURIComponent(sessionId)}`
    : `${API_BASE_URL}/files/`;

  const response = await fetch(url, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error('Failed to list files');
  }

  return response.json();
}

// =============================================================================
// Export API object
// =============================================================================

export const filesApi = {
  upload: uploadFile,
  list: listFiles,
  listWithSession: listFilesWithSession,
  get: getFile,
  delete: deleteFile,
  download: downloadFile,
  getContentUrl: getFileContentUrl,
  getDownloadUrl: getFileDownloadUrl,
  getContentText: getFileContentText,
  getContentBlob: getFileContentBlob,
};
