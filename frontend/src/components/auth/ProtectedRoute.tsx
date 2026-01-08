// =============================================================================
// IPA Platform - Protected Route Component
// =============================================================================
// Sprint 71: S71-3 - ProtectedRoute Component
// Phase 18: Authentication System
//
// Route wrapper that requires authentication.
// Redirects unauthenticated users to login page.
//
// Dependencies:
//   - authStore (src/store/authStore)
//   - React Router
// =============================================================================

import { FC, ReactNode, useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { Loader2 } from 'lucide-react';

// =============================================================================
// Types
// =============================================================================

interface ProtectedRouteProps {
  children: ReactNode;
  /** Optional: Required role(s) to access this route */
  requiredRoles?: string[];
}

// =============================================================================
// Component
// =============================================================================

/**
 * ProtectedRoute - Route wrapper for authentication
 *
 * Wraps routes that require authentication. If user is not authenticated,
 * redirects to login page with return URL preserved.
 *
 * @example
 * <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
 *   <Route path="dashboard" element={<DashboardPage />} />
 * </Route>
 *
 * @example With role requirement
 * <ProtectedRoute requiredRoles={['admin', 'operator']}>
 *   <AdminPanel />
 * </ProtectedRoute>
 */
export const ProtectedRoute: FC<ProtectedRouteProps> = ({
  children,
  requiredRoles,
}) => {
  const location = useLocation();
  const { isAuthenticated, user, refreshSession, token } = useAuthStore();
  const [isChecking, setIsChecking] = useState(true);

  // Check session on mount (for page refresh scenarios)
  useEffect(() => {
    const checkSession = async () => {
      // If we have a token but no user data, try to refresh session
      if (token && !user) {
        await refreshSession();
      }
      setIsChecking(false);
    };

    checkSession();
  }, [token, user, refreshSession]);

  // Show loading spinner while checking authentication
  if (isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground">驗證中...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    // Preserve the attempted URL for redirect after login
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role requirements if specified
  if (requiredRoles && requiredRoles.length > 0 && user) {
    const hasRequiredRole = requiredRoles.includes(user.role);

    if (!hasRequiredRole) {
      // User is authenticated but doesn't have required role
      // Redirect to dashboard with access denied message
      return (
        <Navigate
          to="/dashboard"
          state={{ accessDenied: true }}
          replace
        />
      );
    }
  }

  // User is authenticated (and has required role if specified)
  return <>{children}</>;
};

// =============================================================================
// Role-Specific Wrappers (convenience components)
// =============================================================================

/**
 * AdminRoute - Route that requires admin role
 */
export const AdminRoute: FC<{ children: ReactNode }> = ({ children }) => (
  <ProtectedRoute requiredRoles={['admin']}>{children}</ProtectedRoute>
);

/**
 * OperatorRoute - Route that requires operator or admin role
 */
export const OperatorRoute: FC<{ children: ReactNode }> = ({ children }) => (
  <ProtectedRoute requiredRoles={['admin', 'operator']}>{children}</ProtectedRoute>
);

export default ProtectedRoute;
