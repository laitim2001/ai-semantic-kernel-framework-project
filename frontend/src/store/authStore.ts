/**
 * Auth Store - Authentication State Management
 *
 * Sprint 71: S71-1 - Auth Store (Zustand)
 * Phase 18: Authentication System
 *
 * Provides authentication state management with:
 * - User and token storage
 * - Login/Register/Logout actions
 * - Session persistence via localStorage
 * - Guest data migration on login
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { migrateGuestData, clearGuestUserId } from '@/utils/guestUser';

// =============================================================================
// Types
// =============================================================================

export interface User {
  id: string;
  email: string;
  fullName: string | null;
  role: string;
  isActive: boolean;
  createdAt: string;
  lastLogin: string | null;
}

export interface AuthState {
  // State
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (email: string, password: string) => Promise<boolean>;
  register: (email: string, password: string, fullName?: string) => Promise<boolean>;
  logout: () => void;
  refreshSession: () => Promise<boolean>;
  clearError: () => void;
  setLoading: (loading: boolean) => void;
}

// =============================================================================
// API Helpers
// =============================================================================

const API_BASE = '/api/v1';

async function apiLogin(email: string, password: string): Promise<{
  access_token: string;
  refresh_token?: string;
  expires_in: number;
}> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      username: email,  // OAuth2 uses "username"
      password,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Login failed');
  }

  return response.json();
}

async function apiRegister(
  email: string,
  password: string,
  fullName?: string
): Promise<{ access_token: string }> {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Registration failed');
  }

  return response.json();
}

async function apiGetMe(token: string): Promise<User> {
  const response = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    throw new Error('Failed to get user info');
  }

  const data = await response.json();

  return {
    id: data.id,
    email: data.email,
    fullName: data.full_name,
    role: data.role,
    isActive: data.is_active,
    createdAt: data.created_at,
    lastLogin: data.last_login,
  };
}

async function apiRefreshToken(refreshToken: string): Promise<{
  access_token: string;
  refresh_token: string;
}> {
  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    throw new Error('Token refresh failed');
  }

  return response.json();
}

// =============================================================================
// Store
// =============================================================================

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Login action
      login: async (email: string, password: string): Promise<boolean> => {
        set({ isLoading: true, error: null });

        try {
          // 1. Login and get tokens
          const tokenResponse = await apiLogin(email, password);

          // 2. Get user info
          const user = await apiGetMe(tokenResponse.access_token);

          // 3. Update state
          set({
            token: tokenResponse.access_token,
            refreshToken: tokenResponse.refresh_token || null,
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });

          // 4. Migrate guest data (non-blocking)
          migrateGuestData(tokenResponse.access_token).catch((err) => {
            console.warn('[AuthStore] Guest data migration failed:', err);
          });

          console.log('[AuthStore] Login successful:', user.email);
          return true;
        } catch (error) {
          const message = error instanceof Error ? error.message : 'Login failed';
          set({
            error: message,
            isLoading: false,
            isAuthenticated: false,
          });
          console.error('[AuthStore] Login failed:', message);
          return false;
        }
      },

      // Register action
      register: async (
        email: string,
        password: string,
        fullName?: string
      ): Promise<boolean> => {
        set({ isLoading: true, error: null });

        try {
          // 1. Register and get token
          const tokenResponse = await apiRegister(email, password, fullName);

          // 2. Get user info
          const user = await apiGetMe(tokenResponse.access_token);

          // 3. Update state
          set({
            token: tokenResponse.access_token,
            refreshToken: null,
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });

          // 4. Clear guest ID (new user, no migration needed)
          clearGuestUserId();

          console.log('[AuthStore] Registration successful:', user.email);
          return true;
        } catch (error) {
          const message = error instanceof Error ? error.message : 'Registration failed';
          set({
            error: message,
            isLoading: false,
            isAuthenticated: false,
          });
          console.error('[AuthStore] Registration failed:', message);
          return false;
        }
      },

      // Logout action
      logout: () => {
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
          error: null,
        });

        // Clear guest ID as well (fresh start)
        clearGuestUserId();

        console.log('[AuthStore] Logged out');
      },

      // Refresh session
      refreshSession: async (): Promise<boolean> => {
        const { refreshToken } = get();

        if (!refreshToken) {
          console.log('[AuthStore] No refresh token, cannot refresh session');
          return false;
        }

        try {
          const tokenResponse = await apiRefreshToken(refreshToken);
          const user = await apiGetMe(tokenResponse.access_token);

          set({
            token: tokenResponse.access_token,
            refreshToken: tokenResponse.refresh_token,
            user,
            isAuthenticated: true,
          });

          console.log('[AuthStore] Session refreshed');
          return true;
        } catch (error) {
          console.error('[AuthStore] Session refresh failed:', error);
          // Clear invalid session
          get().logout();
          return false;
        }
      },

      // Clear error
      clearError: () => {
        set({ error: null });
      },

      // Set loading state
      setLoading: (loading: boolean) => {
        set({ isLoading: loading });
      },
    }),
    {
      name: 'ipa-auth-storage',
      // Only persist token and user, not loading/error state
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// =============================================================================
// Selectors
// =============================================================================

export const selectUser = (state: AuthState) => state.user;
export const selectIsAuthenticated = (state: AuthState) => state.isAuthenticated;
export const selectIsLoading = (state: AuthState) => state.isLoading;
export const selectError = (state: AuthState) => state.error;
export const selectToken = (state: AuthState) => state.token;

export default useAuthStore;
