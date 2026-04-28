/**
 * Guest User ID Management
 *
 * Sprint 68: S68-5 - Guest User ID Implementation
 * Sprint 69: S69-5 - Guest User ID Finalization
 *
 * Provides guest user identification for per-user sandbox isolation.
 * Guest users get a UUID stored in localStorage that persists across sessions.
 *
 * Phase 17: Guest UUID used for sandbox directory isolation
 * Phase 18: Guest data migrates to authenticated user on login
 */

/** localStorage key for guest user ID */
export const GUEST_USER_KEY = 'ipa_guest_user_id';

/**
 * Get or create a guest user ID.
 *
 * If no guest ID exists, generates a new UUID and stores it in localStorage.
 * The ID format is "guest-{uuid}" to distinguish from authenticated users.
 *
 * @returns Guest user ID string
 *
 * @example
 * const userId = getGuestUserId();
 * // Returns: "guest-a1b2c3d4-e5f6-7890-abcd-ef1234567890"
 */
export function getGuestUserId(): string {
  let userId = localStorage.getItem(GUEST_USER_KEY);

  if (!userId) {
    // Generate new guest UUID
    userId = `guest-${crypto.randomUUID()}`;
    localStorage.setItem(GUEST_USER_KEY, userId);
    console.log('[GuestUser] Created new guest user:', userId);
  }

  return userId;
}

/**
 * Check if the current user is a guest (not authenticated).
 *
 * @returns True if using guest ID
 */
export function isGuestUser(): boolean {
  const userId = localStorage.getItem(GUEST_USER_KEY);
  return userId !== null;
}

/**
 * Clear the guest user ID.
 *
 * Call this after successful authentication to clean up guest state.
 * The actual data migration should be done via the backend API.
 */
export function clearGuestUserId(): void {
  const guestId = localStorage.getItem(GUEST_USER_KEY);
  if (guestId) {
    localStorage.removeItem(GUEST_USER_KEY);
    console.log('[GuestUser] Cleared guest user:', guestId);
  }
}

/**
 * Migrate guest data to authenticated user.
 *
 * Call this on first login when there's an existing guest ID.
 * This calls the backend migration API to transfer:
 * - Sessions
 * - Uploaded files
 * - Sandbox data
 *
 * @param authToken - JWT token for the authenticated user
 * @returns Promise resolving to migration result
 *
 * @example
 * // In login action:
 * await login(email, password);
 * if (hasGuestData()) {
 *   await migrateGuestData(accessToken);
 * }
 */
export async function migrateGuestData(authToken: string): Promise<{
  success: boolean;
  sessionsMigrated?: number;
  directoriesMigrated?: string[];
  error?: string;
}> {
  const guestId = localStorage.getItem(GUEST_USER_KEY);

  if (!guestId) {
    return { success: true, sessionsMigrated: 0, directoriesMigrated: [] };
  }

  try {
    const response = await fetch('/api/v1/auth/migrate-guest', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authToken}`,
      },
      body: JSON.stringify({ guest_id: guestId }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Migration failed: ${response.statusText}`);
    }

    const result = await response.json();

    // Clear guest ID after successful migration
    clearGuestUserId();

    console.log('[GuestUser] Migration complete:', result);
    return {
      success: true,
      sessionsMigrated: result.sessions_migrated,
      directoriesMigrated: result.directories_migrated,
    };
  } catch (error) {
    console.error('[GuestUser] Migration failed:', error);
    // Non-critical failure - guest data remains, user can continue
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Migration failed',
    };
  }
}

/**
 * Check if there's guest data to migrate.
 *
 * @returns True if guest ID exists in localStorage
 */
export function hasGuestData(): boolean {
  return localStorage.getItem(GUEST_USER_KEY) !== null;
}

/**
 * Get headers with guest ID for API requests.
 *
 * Use this when making API requests that need user identification.
 * Phase 18 will add authenticated user header support.
 *
 * @returns Headers object with X-Guest-Id if available
 */
export function getGuestHeaders(): Record<string, string> {
  const guestId = localStorage.getItem(GUEST_USER_KEY);

  if (guestId) {
    return { 'X-Guest-Id': guestId };
  }

  return {};
}

/**
 * Ensure guest user ID exists and return it.
 *
 * This is a convenience function that ensures the ID exists
 * before returning it. Useful for initialization.
 *
 * @returns Guest user ID string
 */
export function ensureGuestUserId(): string {
  return getGuestUserId();
}
