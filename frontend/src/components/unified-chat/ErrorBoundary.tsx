/**
 * ErrorBoundary - Component Error Boundary
 *
 * Sprint 65: Metrics, Checkpoints & Polish
 * S65-3: Error Handling & Recovery
 * Phase 16: Unified Agentic Chat Interface
 *
 * React error boundary for catching and displaying component errors
 * with recovery options.
 */

import { Component, ReactNode, ErrorInfo } from 'react';
import { AlertTriangle, RefreshCw, Bug, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/Button';

// =============================================================================
// Types
// =============================================================================

export interface ErrorBoundaryProps {
  /** Child components to render */
  children: ReactNode;
  /** Fallback component to render on error */
  fallback?: ReactNode;
  /** Callback when an error is caught */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** Whether to show error details (default: true in dev) */
  showDetails?: boolean;
  /** Custom reset handler */
  onReset?: () => void;
  /** Custom error title */
  title?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showStackTrace: boolean;
}

// =============================================================================
// Component
// =============================================================================

/**
 * ErrorBoundary Component
 *
 * Catches JavaScript errors in child component tree and displays
 * a fallback UI with error details and recovery options.
 *
 * @example
 * ```tsx
 * <ErrorBoundary onError={(error) => logError(error)}>
 *   <ChatArea />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showStackTrace: false,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });

    // Log error
    console.error('[ErrorBoundary] Caught error:', error, errorInfo);

    // Call onError callback if provided
    this.props.onError?.(error, errorInfo);
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      showStackTrace: false,
    });

    this.props.onReset?.();
  };

  toggleStackTrace = (): void => {
    this.setState((prev) => ({ showStackTrace: !prev.showStackTrace }));
  };

  render(): ReactNode {
    const { hasError, error, errorInfo, showStackTrace } = this.state;
    const {
      children,
      fallback,
      showDetails = process.env.NODE_ENV === 'development',
      title = 'Something went wrong',
    } = this.props;

    if (hasError) {
      // Custom fallback
      if (fallback) {
        return fallback;
      }

      // Default error UI
      return (
        <div
          className="flex flex-col items-center justify-center min-h-[200px] p-6 bg-red-50 border border-red-200 rounded-lg"
          role="alert"
          aria-live="assertive"
        >
          {/* Error Icon */}
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-100 mb-4">
            <AlertTriangle className="h-6 w-6 text-red-600" />
          </div>

          {/* Error Title */}
          <h2 className="text-lg font-semibold text-red-900 mb-2">{title}</h2>

          {/* Error Message */}
          <p className="text-sm text-red-700 text-center mb-4 max-w-md">
            {error?.message || 'An unexpected error occurred'}
          </p>

          {/* Actions */}
          <div className="flex items-center gap-3 mb-4">
            <Button
              variant="outline"
              onClick={this.handleReset}
              className="border-red-300 hover:bg-red-100"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>

            {showDetails && (
              <Button
                variant="ghost"
                onClick={this.toggleStackTrace}
                className="text-red-700 hover:bg-red-100"
              >
                <Bug className="h-4 w-4 mr-2" />
                {showStackTrace ? 'Hide' : 'Show'} Details
                {showStackTrace ? (
                  <ChevronUp className="h-4 w-4 ml-1" />
                ) : (
                  <ChevronDown className="h-4 w-4 ml-1" />
                )}
              </Button>
            )}
          </div>

          {/* Stack Trace */}
          {showDetails && showStackTrace && (
            <div className="w-full max-w-2xl">
              <div className="bg-white border border-red-200 rounded-lg p-4 overflow-auto max-h-64">
                <div className="text-xs font-mono text-gray-700 whitespace-pre-wrap">
                  {/* Error stack */}
                  {error?.stack && (
                    <div className="mb-4">
                      <div className="font-semibold text-red-700 mb-1">Error Stack:</div>
                      {error.stack}
                    </div>
                  )}

                  {/* Component stack */}
                  {errorInfo?.componentStack && (
                    <div>
                      <div className="font-semibold text-red-700 mb-1">Component Stack:</div>
                      {errorInfo.componentStack}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      );
    }

    return children;
  }
}

// =============================================================================
// Functional Wrapper for Hooks Support
// =============================================================================

/**
 * Wrapper component that provides hook-based error handling
 */
export interface ErrorBoundaryWrapperProps extends Omit<ErrorBoundaryProps, 'onError'> {
  /** Error handler with additional context */
  onError?: (error: Error, errorInfo: ErrorInfo, context?: Record<string, unknown>) => void;
  /** Additional context to pass to error handler */
  context?: Record<string, unknown>;
}

export const ErrorBoundaryWrapper: React.FC<ErrorBoundaryWrapperProps> = ({
  onError,
  context,
  ...props
}) => {
  const handleError = (error: Error, errorInfo: ErrorInfo) => {
    onError?.(error, errorInfo, context);
  };

  return <ErrorBoundary {...props} onError={handleError} />;
};

export default ErrorBoundary;
