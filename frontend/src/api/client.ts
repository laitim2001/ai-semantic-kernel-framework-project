// =============================================================================
// IPA Platform - API Client
// =============================================================================
// Sprint 5: Frontend UI - HTTP Client
//
// Centralized API client for backend communication.
// Handles authentication, error handling, and response parsing.
//
// Dependencies:
//   - Fetch API
// =============================================================================

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
 * Get authentication token from storage
 */
function getAuthToken(): string | null {
  return localStorage.getItem('auth_token');
}

/**
 * Core fetch wrapper with error handling
 */
async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const token = getAuthToken();

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
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
