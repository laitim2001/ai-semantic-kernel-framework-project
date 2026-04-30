// =============================================================================
// IPA Platform - API Client
// =============================================================================
// Sprint 5: Frontend UI - HTTP Client
// Sprint 69: S69-5 - Guest User ID header integration
// Sprint 71: S71-4 - Token interceptor with 401 handling (Phase 18)
//
// Centralized API client for backend communication.
// Handles authentication, error handling, and response parsing.
// Supports guest user identification for sandbox isolation.
//
// Dependencies:
//   - Fetch API
//   - guestUser utils (for X-Guest-Id header)
//   - authStore (for token and logout)
// =============================================================================

import { getGuestHeaders } from '@/utils/guestUser';
import { useAuthStore } from '@/store/authStore';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

/**
 * API response wrapper
 */
export interface ApiResponse<T> {
  data: T;
  error?: string;
}

/**
 * API error class for structured error handling
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public details?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Get authentication token from authStore
 * Sprint 71: Updated to read from Zustand persist storage
 */
function getAuthToken(): string | null {
  // Get token from Zustand store (which persists to localStorage)
  const state = useAuthStore.getState();
  return state.token;
}

/**
 * Handle 401 Unauthorized response
 * Sprint 71: Logout user and redirect to login page
 */
function handleUnauthorized(): void {
  const authStore = useAuthStore.getState();
  authStore.logout();

  // Redirect to login page (only if not already on login/signup)
  if (!window.location.pathname.startsWith('/login') &&
      !window.location.pathname.startsWith('/signup')) {
    window.location.href = '/login';
  }
}

/**
 * Core fetch wrapper with error handling
 *
 * Automatically includes:
 * - Authorization header (if auth token exists)
 * - X-Guest-Id header (if guest user, for sandbox isolation)
 */
async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const token = getAuthToken();
  const guestHeaders = getGuestHeaders();

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...guestHeaders,  // S69-5: Include X-Guest-Id for sandbox isolation
    ...options?.headers,
  };

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    // Sprint 71: Handle 401 Unauthorized - logout and redirect
    if (response.status === 401) {
      handleUnauthorized();
      throw new ApiError('Unauthorized', 401);
    }

    let errorMessage = 'API Error';
    let errorDetails: unknown;

    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
      errorDetails = errorData;
    } catch {
      errorMessage = response.statusText;
    }

    throw new ApiError(errorMessage, response.status, errorDetails);
  }

  // Handle empty responses (204 No Content)
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

/**
 * API client methods
 */
export const api = {
  /**
   * GET request
   */
  get: <T>(endpoint: string): Promise<T> => fetchApi<T>(endpoint),

  /**
   * POST request
   */
  post: <T>(endpoint: string, body?: unknown): Promise<T> =>
    fetchApi<T>(endpoint, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }),

  /**
   * PUT request
   */
  put: <T>(endpoint: string, body: unknown): Promise<T> =>
    fetchApi<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),

  /**
   * PATCH request
   */
  patch: <T>(endpoint: string, body: unknown): Promise<T> =>
    fetchApi<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  /**
   * DELETE request
   */
  delete: <T>(endpoint: string): Promise<T> =>
    fetchApi<T>(endpoint, { method: 'DELETE' }),
};

// Export base URL for external use
export { API_BASE_URL };
